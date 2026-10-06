# Flow CLI

Manage Agent Studio workflows: list workflows, compare definitions and prompts, and merge prompt text locally.

We are exploring a GitHub-like approach to collaboration: developers copy workflows, work independently on their copies, then integrate their changes into a shared workflow. This tool supports that process by comparing workflows and merging prompt text to help prepare the changes for integration.

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/). To get your token, sign in to [Agent Studio](https://int-dev-dj-agent-platform-ui.vir-dev.onservo.com/), open your browser's developer tools → Network, and look for the access token in the HTTP request headers. Set it below:

```sh
export AG_UI_TOKEN="your-okta-access-token"
uv run cli.py list
uv run cli.py list --search summary --env prod
uv run cli.py compare workflow1 workflow2
uv run cli.py merge source-workflow target-workflow
```

The Agent Studio token expires every few hours. When it expires, get a fresh token from Agent Studio's HTTP request headers and update `AG_UI_TOKEN`.

Settings can also go in `.env`; exported variables take precedence. For comparisons and merges, set `LANGSMITH_API_KEY` to a LangSmith API key with access to the Agent Studio workspace so the CLI can retrieve its prompts.

The default API is dev; override it with `FLOW_BASE_URL` or `--base-url`. Use `--env dev|prod` to select workflow storage, and `list --format json|names` for other output formats.

Merge writes prompt files to `merge/`; resolve any conflict markers manually. It does not publish changes. Existing output files must be moved before rerunning.

For command options, run `uv run cli.py <command> --help`.
