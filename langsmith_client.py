"""Fetch prompt templates without rendering variables or executing models."""

import os

from client import PlatformError


class PromptClient:
    def __init__(self, timeout: float = 30):
        self.timeout = timeout
        self._client = None
        self._cache: dict[str, str] = {}

    def get_prompt(self, identifier: str) -> str:
        if identifier in self._cache:
            return self._cache[identifier]
        if self._client is None:
            key = os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY")
            if not key:
                raise PlatformError("Set LANGSMITH_API_KEY in the environment or .env to retrieve referenced prompts.")
            from langsmith import Client

            self._client = Client(
                api_key=key,
                api_url=os.environ.get("LANGSMITH_ENDPOINT") or os.environ.get("LANGCHAIN_ENDPOINT") or "https://api.smith.langchain.com",
                timeout_ms=int(self.timeout * 1000),
            )
        try:
            template = self._client.pull_prompt(identifier, include_model=False)
            # Includes message roles and unexpanded template variables.
            text = template.pretty_repr(html=False)
        except Exception as exc:
            # SDK exception messages can contain request details; keep credentials out of output.
            raise PlatformError(f"Could not retrieve LangSmith prompt {identifier!r} ({type(exc).__name__}).") from exc
        self._cache[identifier] = text
        return text


def resolve_prompts(workflow: dict, client: PromptClient) -> tuple[dict[str, str], list[str]]:
    resolved = {}
    unresolved = []
    for node in workflow.get("nodes", []):
        args = node.get("args") or {}
        inline = args.get("prompt") if node.get("tool") == "llm_call" else args.get("prompt_text")
        inline = inline or node.get("prompt_text")
        if isinstance(inline, str) and inline.strip():
            resolved[node["id"]] = inline
        elif isinstance(args.get("prompt_id"), str) and args["prompt_id"].strip():
            resolved[node["id"]] = client.get_prompt(args["prompt_id"])
        elif node.get("prompt_ref") or args.get("prompt_store_ref") or any("prompt" in key for key in args):
            unresolved.append(node["id"])
    return resolved, unresolved
