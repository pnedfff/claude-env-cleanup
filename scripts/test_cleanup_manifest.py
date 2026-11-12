"""Cleanup inventory regression tests using disposable fixture paths only."""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import audit_claude_env as cli
import cleanup_manifest as manifest


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.temp.name) / "home"
        self.apps = pathlib.Path(self.temp.name) / "apps"
        self.home.mkdir()
        self.apps.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def file(self, relative, content="fixture-secret"):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def build(self, scope="claude"):
        return manifest.build_manifest(self.home, self.apps, scope)

    def items(self, document):
        return {item["path"]: item for item in document["items"]}

    def test_candidate_includes_impact_and_never_selects(self):
        self.file(".claude/stats-cache.json")
        doc = self.build()
        item = self.items(doc)["~/.claude/stats-cache.json"]
        self.assertEqual(item["disposition"], "candidate")
        self.assertTrue(item["impact"])
        self.assertFalse(doc["executable"])
        self.assertTrue(all(not row["selected"] for row in doc["items"]))
        self.assertNotIn("fixture-secret", json.dumps(doc))

    def test_shared_history_and_root_cannot_be_candidates(self):
        self.file(".claude/projects/session.jsonl")
        self.file(".claude/history.jsonl")
        rows = self.items(self.build())
        for path in ("~/.claude", "~/.claude/projects", "~/.claude/sessions",
                     "~/.claude/history.jsonl", "~/.claude.json", "~/.claude/skills"):
            self.assertEqual(rows[path]["disposition"], "protected")
            self.assertEqual(rows[path]["proposed_action"], "preserve")
            self.assertTrue(rows[path]["protection_reason"])

    def test_integration_data_is_never_inspected(self):
        self.file(".teamo/settings.json")
        self.file("code/Claude-to-IM-skill/session.json")
        original = manifest.metadata
        touched = []
        def track(path, anchor):
            touched.append(path)
            return original(path, anchor)
        with patch.object(manifest, "metadata", side_effect=track):
            rows = self.items(self.build())
        for path in ("~/.teamo", "~/.claude-to-im", "~/code/Claude-to-IM-skill",
                     "~/Library/LaunchAgents/com.claude-to-im.bridge.plist"):
            self.assertEqual(rows[path]["observation"]["state"], "not_checked")
            self.assertEqual(rows[path]["disposition"], "protected")
        self.assertFalse(any(".teamo" in str(p) or "Claude-to-IM" in str(p) for p in touched))

    def test_default_scope_excludes_other_tool_configs(self):
        self.file(".codex/config.toml")
        rows = self.items(self.build())
        self.assertNotIn("~/.codex/config.toml", rows)
        self.assertNotIn("~/.cc-switch/settings.json", rows)
        self.assertNotIn("~/.gemini/settings.json", rows)

    def test_explicit_all_adds_review_only_configs(self):
        self.file(".codex/config.toml")
        rows = self.items(self.build("all"))
        item = rows["~/.codex/config.toml"]
        self.assertEqual(item["disposition"], "review")
        self.assertTrue(item["protection_reason"])
        self.assertFalse(item["selected"])
        self.assertEqual(rows["~/.teamo"]["observation"]["state"], "not_checked")

    def test_missing_is_not_candidate(self):
        row = self.items(self.build())["~/.claude/cache"]
        self.assertEqual(row["disposition"], "not_found")

    def test_symlinked_parent_is_blocked(self):
        outside = pathlib.Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "cache").write_text("fixture-secret")
        (self.home / ".claude").symlink_to(outside, target_is_directory=True)
        doc = self.build()
        row = self.items(doc)["~/.claude/cache"]
        self.assertEqual(row["observation"]["state"], "blocked_symlink")
        self.assertEqual(row["disposition"], "review")
        self.assertEqual(doc["completeness"], "incomplete")
        self.assertEqual((outside / "cache").read_text(), "fixture-secret")

    def test_file_symlink_is_review_only(self):
        secret = self.file("fixture-target")
        (self.home / ".claude").mkdir()
        (self.home / ".claude" / "stats-cache.json").symlink_to(secret)
        row = self.items(self.build())["~/.claude/stats-cache.json"]
        self.assertEqual(row["disposition"], "review")
        self.assertIsNone(row["observation"]["file_bytes"])

    def test_permission_error_is_incomplete_without_private_message(self):
        with patch.object(pathlib.Path, "lstat", side_effect=PermissionError("fixture-secret")):
            doc = self.build()
        self.assertEqual(doc["completeness"], "incomplete")
        self.assertNotIn("fixture-secret", json.dumps(doc))

    def test_ids_unique_and_stable(self):
        first = self.build()
        second = self.build()
        self.assertEqual([r["id"] for r in first["items"]], [r["id"] for r in second["items"]])
        self.assertEqual(len({r["id"] for r in first["items"]}), len(first["items"]))

    def test_cli_json_is_pure_json_and_never_runs_commands(self):
        doc = self.build()
        output = io.StringIO()
        with patch.object(cli, "build_manifest", return_value=doc), \
             patch.object(cli, "run_command", side_effect=AssertionError("commands forbidden")), \
             contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(["--format", "json"]), 0)
        self.assertEqual(json.loads(output.getvalue()), doc)

    def test_default_detailed_config_audit_does_not_read_other_tools(self):
        claude = self.file(".claude/settings.json", '{}')
        codex = self.file(".codex/config.toml")
        output = io.StringIO()
        with patch.object(cli, "HOME", self.home), patch.object(cli, "FILES", [claude, codex]), \
             patch.object(cli, "scan_json_file") as json_scan, patch.object(cli, "scan_text_file") as text_scan, \
             contextlib.redirect_stdout(output):
            cli.scan_files()
        json_scan.assert_called_once_with(claude)
        text_scan.assert_not_called()

    def test_inventory_is_read_only_even_for_protected_content(self):
        paths = [self.file(".claude/projects/session.jsonl"), self.file(".claude/.credentials.json"),
                 self.file(".claude/settings.json"), self.file(".teamo/settings.json")]
        before = {p: p.read_bytes() for p in paths}
        # Inventory must not read file contents, even for configuration candidates.
        with patch.object(pathlib.Path, "read_text", side_effect=AssertionError("content read forbidden")), \
             patch.object(pathlib.Path, "read_bytes", side_effect=AssertionError("content read forbidden")):
            self.build()
        self.assertEqual(before, {p: p.read_bytes() for p in paths})

    def test_detailed_default_does_not_call_cross_tool_checks(self):
        output = io.StringIO()
        def fixture(*args):
            pass
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(cli, "build_manifest", return_value=self.build()))
            for name in ("scan_files", "scan_env", "scan_privacy_controls", "scan_official_install",
                         "scan_browser_bridge", "scan_launch_agents"):
                stack.enter_context(patch.object(cli, name, fixture))
            blocked = []
            for name in ("scan_coding_agent_configs", "scan_port", "scan_cc_switch_artifacts",
                         "scan_locale_font_signals", "scan_teamo_preservation"):
                blocked.append(stack.enter_context(patch.object(cli, name, side_effect=AssertionError("out of scope"))))
            stack.enter_context(contextlib.redirect_stdout(output))
            self.assertEqual(cli.main(["--audit"]), 0)
            for check in blocked:
                check.assert_not_called()

    def test_json_diagnostics_combination_rejected_before_inspection(self):
        with patch.object(cli, "build_manifest") as build, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main(["--format", "json", "--audit"])
        build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
