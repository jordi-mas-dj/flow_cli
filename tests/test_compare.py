import contextlib
import io
import json
import unittest
from unittest.mock import patch

from cli import main
from client import get_workflow
from compare import render_comparison


class CompareTests(unittest.TestCase):
    def test_fetch_definition(self):
        workflow = {"nodes": [{"id": "step", "args": {}}]}
        with patch("client.urlopen", return_value=io.BytesIO(json.dumps({"workflow": workflow}).encode())) as opener:
            self.assertEqual(get_workflow("https://example.com", "token", "flow/name", "prod", 10), workflow)
        self.assertEqual(opener.call_args.args[0].full_url, "https://example.com/skills/flow%2Fname?env=prod")

    def test_prompt_changes_and_added_node(self):
        left = {"nodes": [{"id": "step", "args": {"prompt": "old\ntext"}, "prompt_ref": "V1"}]}
        right = {"nodes": [{"id": "step", "args": {"prompt": "new\ntext"}, "prompt_ref": "V2"}, {"id": "added", "prompt_text": "extra"}]}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            render_comparison(left, right, "a", "b")
        text = output.getvalue()
        for expected in ["-old", "+new", "-V1", "+V2", "+extra", "Workflow definitions", "<absent>"]:
            self.assertIn(expected, text)

    def test_identical_definitions(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            render_comparison({"nodes": []}, {"nodes": []}, "a", "b")
        self.assertIn("No differences.", output.getvalue())

    def test_compare_uses_ag_ui_token_and_env(self):
        with patch.dict("os.environ", {"AG_UI_TOKEN": "ui"}), patch("cli.get_workflow", return_value={"nodes": []}) as fetch, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["compare", "a", "b", "--env", "prod"]), 0)
        self.assertEqual([call.args[2] for call in fetch.call_args_list], ["a", "b"])
        self.assertTrue(all(call.args[1] == "ui" and call.args[3] == "prod" for call in fetch.call_args_list))
