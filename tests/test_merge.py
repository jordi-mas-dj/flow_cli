import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cli import main
from client import PlatformError
from merge import merge_text, workflow_prompt_names, write_merges


class MergeTests(unittest.TestCase):
    def test_independent_edits(self):
        text, conflict = merge_text("one\ntwo\nthree\n", "ONE\ntwo\nthree\n", "one\ntwo\nTHREE\n", ("base", "a", "b"))
        self.assertFalse(conflict)
        self.assertEqual(text, "ONE\ntwo\nTHREE\n")

    def test_conflict_without_final_newlines(self):
        text, conflict = merge_text("base", "left", "right", ("base", "a", "b"))
        self.assertTrue(conflict)
        self.assertIn("<<<<<<< a\nleft\n||||||| base\nbase\n=======\nright\n>>>>>>> b\n", text)

    def test_identical_edits_and_empty_base(self):
        self.assertEqual(merge_text("base", "new", "new", ("base", "a", "b")), ("new", False))
        self.assertEqual(merge_text("", "", "added", ("base", "a", "b")), ("added", False))

    def test_names_and_file_output(self):
        names = workflow_prompt_names({"nodes": [{"id": "step", "args": {"prompt_id": "owner/summary:abc"}}]})
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            output = Path(folder) / "merge"
            conflicts = write_merges({"step": "base"}, {"step": "new"}, {"step": "base"}, names, ("base", "a", "b"), output)
            self.assertFalse(conflicts)
            self.assertEqual((output / "owner_summary.txt").read_text(), "new")
            with self.assertRaises(PlatformError):
                write_merges({}, {"step": "other"}, {}, names, ("base", "a", "b"), output)
            self.assertEqual((output / "owner_summary.txt").read_text(), "new")

    def test_collision_prevents_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "merge"
            with self.assertRaises(PlatformError):
                write_merges({}, {"a": "a", "b": "b"}, {}, {"a": "same", "b": "same"}, ("base", "a", "b"), output)
            self.assertFalse(output.exists())

    def test_workflow_merge_cli(self):
        workflows = [
            {"nodes": [{"id": "step", "tool": "llm_call", "args": {"prompt": text}}]}
            for text in ["original", "left", "right"]
        ]
        with patch("cli.get_workflow", side_effect=workflows), patch("cli.write_merges", return_value=True) as writer:
            self.assertEqual(main(["merge", "a", "b", "--base", "original"]), 2)
        self.assertEqual(writer.call_args.args[:3], ({"step": "original"}, {"step": "left"}, {"step": "right"}))
