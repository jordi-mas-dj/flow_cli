import contextlib
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from cli import main
from client import PlatformError, list_workflows


class WorkflowTests(unittest.TestCase):
    def test_ag_ui_token_from_environment(self):
        with patch.dict("os.environ", {"AG_UI_TOKEN": "environment-token"}), patch("cli.list_workflows", return_value=[]) as listing, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["list"]), 0)
            self.assertEqual(listing.call_args.args[1], "environment-token")

    def test_legacy_token_variables_are_ignored(self):
        with patch.dict("os.environ", {"AG_UI_TOKEN": "", "UI_TOKEN": "ui-token", "FLOW_TOKEN": "flow-token"}), patch("cli.list_workflows", return_value=[]) as listing, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["list"]), 0)
            self.assertEqual(listing.call_args.args[1], "")

    def test_token_option_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["list", "--token", "argument-token"])
        self.assertEqual(error.exception.code, 2)

    def test_request_and_sorting(self):
        response = io.BytesIO(json.dumps({"skills": [{"name": "z"}, {"name": "Alpha"}]}).encode())
        with patch("client.urlopen", return_value=response) as opener:
            result = list_workflows("https://example.com/api/", "token", "prod", 7)
        self.assertEqual([item["name"] for item in result], ["Alpha", "z"])
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.com/api/skills?env=prod")
        self.assertEqual(request.get_header("Authorization"), "Bearer token")
        self.assertEqual(opener.call_args.kwargs["timeout"], 7)

    def test_auth_error(self):
        error = HTTPError("https://example.com", 403, "Forbidden", {}, None)
        with patch("client.urlopen", side_effect=error):
            with self.assertRaisesRegex(PlatformError, "authorized platform UI"):
                list_workflows("https://example.com", "token", None, 3)

    def test_invalid_response(self):
        for payload in [[], {"skills": {}}, {"skills": [None]}, {"skills": [{"name": 3}]}]:
            with self.subTest(payload=payload):
                with patch("client.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
                    with self.assertRaises(PlatformError):
                        list_workflows("https://example.com", "token", None, 3)

    def test_filter_and_json(self):
        output = io.StringIO()
        items = [{"name": "one", "description": "SUMMARY", "dev_version": 0}, {"name": "two"}]
        with patch("cli.list_workflows", return_value=items), contextlib.redirect_stdout(output):
            self.assertEqual(main(["list", "--search", "summary", "--format", "json"]), 0)
        self.assertEqual(json.loads(output.getvalue()), [items[0]])

    def test_missing_token_returns_error(self):
        output = io.StringIO()
        with patch.dict("os.environ", {"AG_UI_TOKEN": ""}), contextlib.redirect_stderr(output):
            self.assertEqual(main(["list"]), 1)
        self.assertIn("AG_UI_TOKEN", output.getvalue())

    def test_empty_and_zero_version(self):
        output = io.StringIO()
        with patch("cli.list_workflows", return_value=[{"name": "one", "dev_version": 0}]), contextlib.redirect_stdout(output):
            main(["list"])
        self.assertIn("0", output.getvalue())
        for fmt, expected in [("json", "[]\n"), ("names", ""), ("table", "No workflows found.\n")]:
            output = io.StringIO()
            with patch("cli.list_workflows", return_value=[]), contextlib.redirect_stdout(output):
                main(["list", "--format", fmt])
            self.assertEqual(output.getvalue(), expected)


if __name__ == "__main__":
    unittest.main()
