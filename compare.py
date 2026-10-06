"""Readable diffs of saved workflow prompts and definitions."""

import difflib
import json


def prompts(workflow: dict) -> dict[str, dict]:
    result = {}
    for node in workflow.get("nodes", []):
        args = node.get("args") or {}
        fields = {key: node[key] for key in ("prompt_text", "prompt_ref") if node.get(key) is not None}
        for key, value in args.items():
            if "prompt" in key.lower():
                fields["args." + key] = value
        if fields:
            result[node["id"]] = fields
    return result


def lines(value: object) -> list[str]:
    text = value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
    return text.splitlines(keepends=True)


def diff(left: object, right: object, left_label: str, right_label: str) -> None:
    for line in difflib.unified_diff(lines(left), lines(right), fromfile=left_label, tofile=right_label):
        print(line, end="" if line.endswith("\n") else "\n")


def render_comparison(left: dict, right: dict, left_name: str, right_name: str,
                      left_prompts: dict[str, str] | None = None,
                      right_prompts: dict[str, str] | None = None) -> None:
    print(f"Comparing {left_name} -> {right_name} (- left, + right)")
    print("\nPrompts (matched by node ID)")
    a, b = prompts(left), prompts(right)
    changed = False
    missing = object()
    for node_id in sorted(a.keys() | b.keys()):
        for field in sorted(a.get(node_id, {}).keys() | b.get(node_id, {}).keys()):
            before = a.get(node_id, {}).get(field, missing)
            after = b.get(node_id, {}).get(field, missing)
            if before == after:
                continue
            changed = True
            print(f"\nNode {node_id}: {field}")
            diff("<absent>" if before is missing else before, "<absent>" if after is missing else after,
                 f"{left_name}/{node_id}/{field}", f"{right_name}/{node_id}/{field}")
    if not changed:
        print("No differences in saved prompt fields.")
    if left_prompts is not None and right_prompts is not None:
        print("\nResolved prompt text (inline and LangSmith)")
        prompt_changes = False
        for node_id in sorted(left_prompts.keys() | right_prompts.keys()):
            before = left_prompts.get(node_id, missing)
            after = right_prompts.get(node_id, missing)
            if before == after:
                continue
            prompt_changes = True
            print(f"\nNode {node_id}")
            diff("<unavailable>" if before is missing else before, "<unavailable>" if after is missing else after,
                 f"{left_name}/{node_id}/prompt", f"{right_name}/{node_id}/prompt")
        if not prompt_changes:
            print("No differences in retrieved prompt text." if left_prompts or right_prompts else "No prompt text could be resolved.")
        print("Tool-default and internal-store prompt bodies are not retrieved from LangSmith.")
    print("\nWorkflow definitions")
    if left == right:
        print("No differences.")
    else:
        diff(left, right, left_name + "/workflow.json", right_name + "/workflow.json")
