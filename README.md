# Flow CLI

Manage Agent Studio workflows: list workflows, compare definitions and prompts, and merge prompt text locally.

We are exploring a GitHub-like approach to collaboration: developers copy workflows, work independently on their copies, then integrate their changes into a shared workflow. This tool supports that process by comparing workflows and merging prompt text to help prepare the changes for integration.

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

## Credential settings

To get your token, sign in to [Agent Studio](https://int-dev-dj-agent-platform-ui.vir-dev.onservo.com/), open your browser's developer tools → Network, and look for the access token in the HTTP request headers. Set it below:

```sh
export AG_UI_TOKEN="your-okta-access-token"
export LANGSMITH_API_KEY="your-langsmith-api-key"
```

When the Agent Studio token expires, get a fresh token from Agent Studio's HTTP request headers and update `AG_UI_TOKEN`.

Settings can also go in `.env` beside `cli.py`; exported variables take precedence. To retrieve referenced prompts during comparisons and merges, set `LANGSMITH_API_KEY` to a LangSmith API key with access to the Agent Studio workspace. Optionally set `LANGSMITH_ENDPOINT`; inline prompts do not require LangSmith credentials.

The default API is `https://int-dev-dj-agent-platform-api.vir-dev.onservo.com`; override it with `FLOW_BASE_URL` or `--base-url`. Use `--env dev|prod` to select workflow storage.

## How the tool works

The CLI retrieves workflow definitions from Agent Studio using `AG_UI_TOKEN` and referenced prompt text from LangSmith using `LANGSMITH_API_KEY`. Inline prompts are read directly from workflow definitions.

Run from the repository directory; uv installs dependencies automatically:

```sh
uv run cli.py list
uv run cli.py list --search summary --format names
uv run cli.py compare version1 master
uv run cli.py merge version1 master
```

`list` shows names, dev/prod versions, and descriptions. Names are prefixed with `*` in table and names output. Use `--format json` for the full listing data.

`compare` shows differences in saved prompt fields, resolved prompt text, and full workflow definitions. Nodes match by ID. `-` indicates the first workflow and `+` the second. LangSmith references preserve pinned versions; unversioned references retrieve the current prompt.

`merge version1 master` writes prompt text to `merge/<prompt-name>.txt` in the current directory. It uses the target prompt name without its commit suffix, falling back to the node ID for inline prompts. Unsafe filename characters become `_`; filename collisions are errors.

No common base is required. Identical prompts and prompts present on only one side are carried through. Differing prompts get `<<<<<<< version1`, `=======`, and `>>>>>>> master` markers for manual resolution. This prepares local text files; it does not merge workflow definitions or publish changes. Existing output files must be moved before rerunning.

Tool-default prompts, tool-version references such as `V7`, and internal prompt-store references cannot be retrieved through LangSmith. Comparison reports unresolved references; merge stops if it encounters one. Failed LangSmith retrievals also stop the operation.

Exit codes: `0` for success, `1` for errors, and `2` when merge files contain conflicts.

For command options, run `uv run cli.py <command> --help`.

## Tests

```sh
uv run python -m unittest discover -s tests
```
