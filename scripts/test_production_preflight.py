"""Pure parsing and temporary-path tests; native collectors always mocked here."""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

import production_preflight as preflight


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name).resolve()
        self.home = self.root / "home"
        self.apps = self.root / "apps"
        self.home.mkdir()
        self.apps.mkdir()
        self.addCleanup(self.temp.cleanup)

    def file(self, relative):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture-secret")
        return path

    def run_fake(self, command):
        if command[0] == "/bin/ps":
            return subprocess.CompletedProcess(command, 0, b"10 1 501 /fixture/bin/node\n20 1 0 /root/private-process\n", b"")
        if command[0] == "/fixture/lsof":
            return subprocess.CompletedProcess(command, 0, b"p10\0n" + str(self.home / ".claude/projects/session-secret").encode() + b"\0\n", b"")
        return subprocess.CompletedProcess(command, 0, b"state = running\npid = 10\nenvironment = fixture-secret\n", b"")

    def collect(self, runner=None):
        with patch.object(preflight.shutil, "which", side_effect=lambda name: "/fixture/" + name):
            return preflight.collect_processes(self.home, runner=runner or self.run_fake, uid=501)

    def build(self, process=None):
        with patch.dict(os.environ, {}, clear=True):
            return preflight.build_preflight(self.home, self.apps, lambda: process or {"complete": True, "running": []})

    def test_real_adapter_arguments_are_read_only_without_cmdline(self):
        commands = []
        def track(command):
            commands.append(command)
            return self.run_fake(command)
        observed = self.collect(track)
        self.assertTrue(observed["complete"])
        self.assertIn("Claude-to-IM", observed["running"])
        self.assertIn("shared_Claude_state_access", observed["running"])
        self.assertTrue(all("args" not in " ".join(command) for command in commands))
        serialized = json.dumps(observed)
        self.assertNotIn("fixture-secret", serialized)
        self.assertNotIn("session-secret", serialized)
        self.assertNotIn("private-process", serialized)

    def test_current_user_only_parser(self):
        records = preflight.parse_ps(b"10 1 501 /fixture/Claude.app/Contents/MacOS/Claude\n20 1 0 /root/secret\n", 501)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["pid"], 10)

    def test_malformed_ps_is_unknown(self):
        def bad(command):
            return subprocess.CompletedProcess(command, 0, b"private-secret-malformed", b"")
        observed = self.collect(bad)
        self.assertFalse(observed["complete"])
        self.assertNotIn("private-secret", str(observed))

    def test_lsof_nul_parser_handles_newline_and_spaces(self):
        records = preflight.parse_lsof(b"p10\0f4\0n/path with spaces/line\nname\0\n")
        self.assertEqual(records, {10: ["/path with spaces/line\nname"]})

    def test_lsof_warning_prevents_complete_claim(self):
        def warning(command):
            if command[0] == "/fixture/lsof":
                return subprocess.CompletedProcess(command, 0, b"p10\0", b"private-warning")
            return self.run_fake(command)
        observed = self.collect(warning)
        self.assertFalse(observed["complete"])
        self.assertNotIn("private-warning", str(observed))

    def test_missing_service_is_negative_not_error(self):
        def missing(command):
            if command[0] == "/fixture/launchctl":
                return subprocess.CompletedProcess(command, 113, b"", b"Could not find service in domain")
            return self.run_fake(command)
        observed = self.collect(missing)
        self.assertTrue(observed["complete"])
        self.assertNotIn("Claude-to-IM", observed["running"])

    def test_unknown_service_state_is_incomplete(self):
        def bad(command):
            if command[0] == "/fixture/launchctl":
                return subprocess.CompletedProcess(command, 0, b"private-secret", b"")
            return self.run_fake(command)
        observed = self.collect(bad)
        self.assertFalse(observed["complete"])
        self.assertNotIn("private-secret", str(observed))

    def test_process_population_change_requires_recheck(self):
        calls = []
        def changing(command):
            if command[0] == "/bin/ps":
                calls.append(1)
                if len(calls) == 2:
                    return subprocess.CompletedProcess(command, 0, b"11 1 501 /fixture/bin/teamo\n", b"")
            return self.run_fake(command)
        observed = self.collect(changing)
        self.assertFalse(observed["complete"])
        self.assertIn("Teamo", observed["running"])

    def test_metadata_scan_does_not_read_contents(self):
        path = self.file(".claude/cache/private-file")
        with patch.object(os, "read", side_effect=AssertionError("content read forbidden")):
            check = preflight.inspect_tree(path.parent, self.home)
        self.assertEqual(check["state"], "checked")
        self.assertEqual(check["estimated_file_bytes"], len("fixture-secret"))
        self.assertNotIn("private-file", str(check))

    def test_symlink_and_hardlink_block_path_check(self):
        path = self.file("outside")
        cache = self.home / ".claude/cache"
        cache.mkdir(parents=True)
        link = cache / "link"
        link.symlink_to(path)
        self.assertEqual(preflight.inspect_tree(cache, self.home)["state"], "unknown")
        link.unlink()
        os.link(path, link)
        self.assertEqual(preflight.inspect_tree(cache, self.home)["state"], "unknown")

    def test_scan_limit_is_unknown(self):
        path = self.file(".claude/cache/item")
        check = preflight.inspect_tree(path.parent, self.home, max_entries=0)
        self.assertEqual(check["reason"], "metadata_scan_limit")

    def test_preflight_has_no_target_writes_or_backups(self):
        path = self.file(".claude/cache/item")
        self.file(".claude/projects/session")
        before = path.read_bytes()
        original_open = os.open
        def readonly(path, flags, *args, **kwargs):
            self.assertEqual(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
            return original_open(path, flags, *args, **kwargs)
        with patch.object(os, "open", side_effect=readonly), \
             patch.object(pathlib.Path, "mkdir", side_effect=AssertionError("mkdir forbidden")), \
             patch.object(pathlib.Path, "unlink", side_effect=AssertionError("unlink forbidden")):
            plan = self.build()
        self.assertFalse(plan["executable"])
        self.assertFalse(plan["backup_plan"]["created"])
        self.assertFalse(plan["backup_plan"]["verified"])
        self.assertTrue(all(not item["selected"] for item in plan["candidates"]))
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.home / "Backups").exists())
        self.assertNotIn("fixture-secret", json.dumps(plan))

    def test_active_protected_integrations_are_blockers_not_removal_targets(self):
        self.file(".claude/cache/item")
        plan = self.build({"complete": True, "running": ["Teamo", "Claude-to-IM"]})
        self.assertIn("relevant_processes_or_shared_state_users_active", plan["blockers"])
        candidates = {item["path"] for item in plan["candidates"]}
        for path in ("~/.teamo", "~/.claude/projects", "~/code/Claude-to-IM-skill"):
            self.assertNotIn(path, candidates)
        self.assertTrue(any(item["path"] == "~/.teamo" for item in plan["protected_items"]))

    def test_backup_parent_symlink_is_blocked_and_never_followed(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.home / "Backups").symlink_to(outside, target_is_directory=True)
        backup = preflight.backup_preflight(self.home, "fixture-id", 10)
        self.assertEqual(backup["state"], "blocked")
        self.assertFalse(list(outside.iterdir()))

    def test_insufficient_space_is_a_blocker(self):
        with patch.object(os, "statvfs", return_value=types.SimpleNamespace(f_bavail=1, f_frsize=1)):
            backup = preflight.backup_preflight(self.home, "fixture-id", 10)
        self.assertEqual(backup["reason"], "insufficient_estimated_space")

    def test_native_timeout_is_redacted(self):
        with patch.object(preflight.subprocess, "run", side_effect=subprocess.TimeoutExpired("fixture-secret", 1)):
            observed = preflight.run_probe(["fake"])
        self.assertEqual(observed.returncode, 999)
        self.assertNotIn(b"fixture-secret", observed.stderr)

    def test_custom_directory_is_not_silently_added(self):
        with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "/private-secret-directory"}):
            plan = preflight.build_preflight(self.home, self.apps, lambda: {"complete": True, "running": []})
        self.assertIn("custom_Claude_config_directory_requires_separate_scope", plan["blockers"])
        self.assertNotIn("private-secret-directory", json.dumps(plan))

    def test_unknown_process_snapshot_blocks(self):
        plan = self.build({"complete": False, "running": []})
        self.assertIn("process_checks_incomplete", plan["blockers"])

    def test_cli_json_is_pure_json_and_cannot_execute(self):
        plan = self.build()
        output = io.StringIO()
        with patch.object(preflight, "build_preflight", return_value=plan), contextlib.redirect_stdout(output):
            preflight.main(["--format", "json"])
        self.assertEqual(json.loads(output.getvalue()), plan)
        self.assertFalse(plan["executable"])

    def test_incomplete_scan_cannot_claim_complete_backup_capacity(self):
        self.file(".claude/cache/item")
        with patch.object(preflight, "inspect_tree", return_value={"state": "unknown", "reason": "metadata_scan_limit"}):
            plan = self.build()
        backup = plan["backup_plan"]
        self.assertFalse(backup["payload_estimate_complete"])
        self.assertIsNone(backup["estimated_payload_bytes"])
        self.assertIsNone(backup["required_space_estimate_bytes"])
        self.assertIn("path_checks_incomplete", plan["blockers"])

    def test_readonly_plan_is_not_accepted_by_fixture_executor(self):
        from cleanup_executor import FixtureWorkspace
        plan = self.build()
        with FixtureWorkspace(lambda: {"complete": True, "running": []}) as workspace:
            receipt = workspace.execute(plan)
            self.assertEqual(receipt["reason"], "unknown_or_tampered_plan")


if __name__ == "__main__":
    unittest.main()
