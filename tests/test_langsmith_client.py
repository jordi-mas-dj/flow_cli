import contextlib
import io
import os
import unittest
from unittest.mock import Mock, patch

from client import PlatformError
from compare import render_comparison
from langsmith_client import PromptClient, resolve_prompts


class PromptTests(unittest.TestCase):
    def test_fetch_pinned_prompt_and_cache(self):
        from langchain_core.prompts import ChatPromptTemplate

        client = PromptClient()
        client._client = Mock()
        client._client.pull_prompt.return_value = ChatPromptTemplate.from_messages([
            ("system", "Be precise"), ("human", "Summarize {topic}")])
        text = client.get_prompt("summary:abc123")
        self.assertIn("System Message", text)
        self.assertIn("Human Message", text)
        self.assertIn("{topic}", text)
        self.assertEqual(client.get_prompt("summary:abc123"), text)
        client._client.pull_prompt.assert_called_once_with("summary:abc123", include_model=False)

    def test_resolve_references_inline_and_tool_versions(self):
        client = Mock()
        client.get_prompt.return_value = "remote prompt"
        workflow = {"nodes": [
            {"id": "remote", "tool": "llm_call", "args": {"prompt_id": "summary:abc"}},
            {"id": "inline", "tool": "llm_call", "args": {"prompt": "inline {text}"}},
            {"id": "version", "prompt_ref": "V7", "args": {}},
            {"id": "store", "args": {"prompt_store_ref": "abcdef"}},
        ]}
        resolved, unresolved = resolve_prompts(workflow, client)
        self.assertEqual(resolved, {"remote": "remote prompt", "inline": "inline {text}"})
        self.assertEqual(unresolved, ["version", "store"])
        client.get_prompt.assert_called_once_with("summary:abc")

    def test_missing_key_and_redacted_failure(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(PlatformError, "LANGSMITH_API_KEY"):
                PromptClient().get_prompt("summary")
        client = PromptClient()
        client._client = Mock()
        client._client.pull_prompt.side_effect = ValueError("secret-key")
        with self.assertRaises(PlatformError) as error:
            client.get_prompt("summary")
        self.assertNotIn("secret-key", str(error.exception))

    def test_resolved_prompt_diff(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            render_comparison({"nodes": []}, {"nodes": []}, "a", "b", {"step": "old"}, {"step": "new"})
        self.assertIn("Resolved prompt text", output.getvalue())
        self.assertIn("-old", output.getvalue())
        self.assertIn("+new", output.getvalue())
