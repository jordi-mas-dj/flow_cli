# Flow CLI

Manage Agent Studio workflows: list workflows, compare definitions and prompts, and merge prompt text locally.

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/). To get your token, sign in to [Agent Studio](https://int-dev-dj-agent-platform-ui.vir-dev.onservo.com/), open your browser's developer tools → Network, and look for the access token in the HTTP request headers. Set it below:

```sh
export FLOW_TOKEN="your-okta-access-token"
uv run cli.py list
uv run cli.py list --search summary --env prod
uv run cli.py compare workflow1 workflow2
uv run cli.py merge source-workflow target-workflow
```

Settings can also go in `.env`. `UI_TOKEN` takes precedence over `--token` and `FLOW_TOKEN`. Set `LANGSMITH_API_KEY` to resolve LangSmith prompts for comparisons and merges.

The default API is dev; override it with `FLOW_BASE_URL` or `--base-url`. Use `--env dev|prod` to select workflow storage, and `list --format json|names` for other output formats.

Merge writes prompt files to `merge/`; resolve any conflict markers manually. It does not publish changes. Existing output files must be moved before rerunning.

For command options, run `uv run cli.py <command> --help`.
