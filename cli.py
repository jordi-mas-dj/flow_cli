"""CLI commands; add future platform operations as subcommands."""

import argparse
import json
import math
import os
import sys

from client import PlatformError, get_workflow, list_workflows
from compare import render_comparison
from langsmith_client import PromptClient, resolve_prompts
from merge import workflow_prompt_names, write_merges


def positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("timeout must be a positive number") from None
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be a positive finite number")
    return timeout


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="flow", description="DJ Agent Platform CLI")
    commands = root.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="List saved workflows")
    comparison = commands.add_parser("compare", help="Compare prompts and definitions of two workflows")
    comparison.add_argument("flow1", help="First workflow name")
    comparison.add_argument("flow2", help="Second workflow name")
    merging = commands.add_parser("merge", help="Merge prompt text into merge/<prompt-name>.txt")
    merging.add_argument("flow1", help="First workflow name")
    merging.add_argument("flow2", help="Second workflow name")
    merging.add_argument("--base", required=True, help="Common base workflow")
    for command in (listing, comparison, merging):
        command.add_argument("--token", default=None, help="Okta access token (UI_TOKEN takes precedence; fallback: FLOW_TOKEN)")
        command.add_argument("--base-url", default=os.environ.get("FLOW_BASE_URL", "https://int-dev-dj-agent-platform-api.vir-dev.onservo.com"), help="Platform API URL (default: FLOW_BASE_URL or deployed dev API)")
        command.add_argument("--env", choices=["dev", "prod"], help="Workflow storage environment (default: platform default)")
        command.add_argument("--timeout", type=positive_timeout, default=30, help="Request timeout in seconds (default: 30)")
    listing.add_argument("--format", choices=["table", "json", "names"], default="table", help="Output format")
    listing.add_argument("--search", default="", help="Filter names and descriptions (case insensitive)")
    return root


def clean(value: object) -> str:
    return " ".join("".join(char for char in str(value) if char.isprintable() or char.isspace()).split())


def render(workflows: list[dict], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(workflows, indent=2, ensure_ascii=False))
    elif output_format == "names":
        for workflow in workflows:
            print("* " + clean(workflow["name"]))
    elif not workflows:
        print("No workflows found.")
    else:
        rows = [["NAME", "DEV", "PROD", "DESCRIPTION"]]
        for workflow in workflows:
            rows.append([
                "* " + clean(workflow["name"]),
                str(workflow.get("dev_version") if workflow.get("dev_version") is not None else "-"),
                str(workflow.get("prod_version") if workflow.get("prod_version") is not None else "-"),
                clean(workflow.get("description", "")),
            ])
        widths = [max(len(row[index]) for row in rows) for index in range(3)]
        for row in rows:
            print("  ".join(row[index].ljust(widths[index]) for index in range(3)) + "  " + row[3])


def main(argv: list[str] | None = None) -> int:
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
    args = parser().parse_args(argv)
    try:
        token = os.environ.get("UI_TOKEN") or (args.token if args.token is not None else os.environ.get("FLOW_TOKEN", ""))
        if args.command == "merge":
            labels = (args.base, args.flow1, args.flow2)
            workflows = [get_workflow(args.base_url, token, name, args.env, args.timeout) for name in labels]
            prompt_client = PromptClient(args.timeout)
            maps = []
            for name, workflow in zip(labels, workflows):
                resolved, unresolved = resolve_prompts(workflow, prompt_client)
                if unresolved:
                    raise PlatformError(f"Cannot merge unresolved prompts in {name}: {', '.join(unresolved)}.")
                maps.append(resolved)
            names = workflow_prompt_names(*workflows)
            conflicts = write_merges(*maps, names, labels)
            return 2 if conflicts else 0
        if args.command == "compare":
            left = get_workflow(args.base_url, token, args.flow1, args.env, args.timeout)
            right = get_workflow(args.base_url, token, args.flow2, args.env, args.timeout)
            prompt_client = PromptClient(args.timeout)
            left_prompts, left_unresolved = resolve_prompts(left, prompt_client)
            right_prompts, right_unresolved = resolve_prompts(right, prompt_client)
            render_comparison(left, right, args.flow1, args.flow2, left_prompts, right_prompts)
            for name, unresolved in ((args.flow1, left_unresolved), (args.flow2, right_unresolved)):
                if unresolved:
                    print(f"Unresolved prompt sources in {name}: {', '.join(unresolved)} (tool versions/internal prompt store).")
            return 0
        workflows = list_workflows(args.base_url, token, args.env, args.timeout)
        query = args.search.casefold()
        workflows = [item for item in workflows if query in item["name"].casefold() or query in str(item.get("description", "")).casefold()]
        render(workflows, args.format)
    except PlatformError as exc:
        print(f"flow: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
