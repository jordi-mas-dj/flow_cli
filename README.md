# Flow CLI

A command-line tool for DJ Agent Platform workflows.

## Run

Requires Python 3.10+. Run with uv (installs dependencies automatically):

```sh
export FLOW_BASE_URL="https://int-dev-dj-agent-platform-api.vir-dev.onservo.com"
export FLOW_TOKEN="your-okta-access-token"
uv run cli.py list
```

Or install the `flow` command with `uv tool install .` and run:

```sh
flow list
flow list --token "your-okta-access-token"
flow list --env prod
flow list --search summary
flow list --format json
flow list --format names
flow list --base-url https://your-platform-api --timeout 10
```

The command calls the platform's `GET /skills` endpoint. It lists workflow
names, numeric dev/prod artifact versions, and descriptions, sorted by name.
JSON output preserves all fields from each returned skill. Empty JSON output
is `[]`; names output is empty. Errors go to stderr and return exit code 1.

`FLOW_TOKEN` must be an Okta access token from a client authorized for the
platform UI. This endpoint does not accept ordinary B2B/B2C API tokens.
Token precedence: `UI_TOKEN`, then `--token`, then `FLOW_TOKEN`.
When `UI_TOKEN` is nonempty, it is sent as the Bearer token even if `--token` is provided.
Tokens are not stored by the CLI.
`--env` selects workflow storage; `--base-url` selects the API deployment.
Without `--env`, the server uses its default (currently dev).

The platform checkout is not required at runtime. Saved workflows may live
in S3, so listing uses the API rather than scanning the checkout.

## Development

Compare the latest saved versions of two workflows:

```sh
uv run cli.py compare flow1 flow2
flow compare flow1 flow2 --env prod
```

The command fetches `GET /skills/{name}` for each workflow. It shows per-node
diffs of saved prompt text, references, and prompt arguments, then a diff of
the complete JSON definitions. Nodes match by ID; renamed nodes appear as
removed/added. JSON object keys are sorted; array order is preserved.
`-` marks the first workflow and `+` the second. The CLI also retrieves
`args.prompt_id` references from LangSmith and compares their full templates,
including message roles and unexpanded variables. Pinned versions are preserved;
unversioned IDs use the current LangSmith version. Each reference is fetched once
per comparison. Inline text is compared directly without a LangSmith request.

LangSmith settings are read from `.env` beside `cli.py`, or exported variables
(exported variables take precedence). Configure `LANGSMITH_API_KEY` and optionally
`LANGSMITH_ENDPOINT`. Legacy `LANGCHAIN_API_KEY`/`LANGCHAIN_ENDPOINT` are supported.
Tool version references such as `V7`, tool-default prompts, and internal
`prompt_store_ref` values cannot be resolved through LangSmith.
Retrieval failures return an error rather than reporting prompts as identical.
This command does not execute workflows. Exit code is 0
for a successful comparison (including differences), or 1 for an API error.

## Tests

Merge prompt text using a common base workflow:

```sh
uv run cli.py merge flow1 flow2 --base original_workflow
```

This uses the Python `merge3` library. It retrieves prompts as `compare` does,
matches them by node ID, and writes only text files under `merge/` in the current
directory. It does not merge workflow JSON or publish changes to LangSmith.
Each filename uses the target prompt name without its commit suffix, falling
back to the node ID for inline prompts. Unsafe filename characters become `_`.
Duplicate filenames and unresolved prompt references are errors. Existing
output files are preserved; move them aside before rerunning.

Independent edits merge automatically; overlapping edits get `<<<<<<<`, `|||||||` (base),
`=======`, and `>>>>>>>` markers for manual resolution. Exit codes: 0 for a
clean merge, 2 for conflicts written to files, 1 for errors.

## Validation

```sh
uv run python -m unittest discover -s tests -v
```

Commands live in `cli.py`; platform read operations live in
`client.py`.
