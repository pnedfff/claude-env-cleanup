"""Trash-move tests. Home and Trash are temporary directories; process observations are fake."""
import errno
import io
import os
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

import trash_cleanup
from trash_cleanup import Stop, TrashCleaner

QUIET = {"complete": True, "running": []}
CACHE = "~/Library/Caches/claude-cli-nodejs"
STATS = "~/.claude/stats-cache.json"


class TrashCleanupTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="claude-trash-fixture-")
        self.addCleanup(temp.cleanup)
        root = pathlib.Path(temp.name).resolve()
        self.home, self.apps, self.trash = root / "home", root / "applications", root / "home" / ".Trash"
        for path in (self.home, self.apps, self.trash):
            path.mkdir(mode=0o700)
        self.probe = dict(QUIET)
        self.cleaner = TrashCleaner(self.home, self.apps, self.trash, lambda: self.probe)
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def file(self, relative, content=b"fixture"):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def seed(self):
        self.file("Library/Caches/claude-cli-nodejs/a/b.log", b"12345")
        self.file(".claude/stats-cache.json", b"{}")
        self.file(".claude/projects/session.jsonl", b"keep")
        self.file(".claude/settings.json", b"keep")

    def ids(self, plan):
        return {item["path"]: item["id"] for item in plan["items"]}

    def moved(self):
        self.seed()
        plan = self.cleaner.plan()
        receipt = self.cleaner.run(plan["confirm_code"])
        self.assertEqual(receipt["status"], "complete", receipt)
        return receipt

    def test_plan_lists_only_present_cache_candidates_and_changes_nothing(self):
        self.seed()
        plan = self.cleaner.plan()
        self.assertEqual(set(self.ids(plan)), {CACHE, STATS})
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["total_bytes"], 7)
        self.assertEqual(list(self.trash.iterdir()), [])

    def test_run_moves_to_batch_and_leaves_protected_data(self):
        receipt = self.moved()
        batch = self.trash / receipt["batch"]
        self.assertFalse((self.home / "Library/Caches/claude-cli-nodejs").exists())
        self.assertFalse((self.home / ".claude/stats-cache.json").exists())
        self.assertEqual((self.home / ".claude/projects/session.jsonl").read_bytes(), b"keep")
        self.assertEqual((self.home / ".claude/settings.json").read_bytes(), b"keep")
        by_path = {item["path"]: item for item in receipt["items"]}
        self.assertEqual((batch / by_path[CACHE]["id"] / "a/b.log").read_bytes(), b"12345")
        self.assertEqual({item["state"] for item in receipt["items"]}, {"moved"})
        self.assertTrue((batch / "receipt.json").is_file())

    def test_restore_puts_everything_back(self):
        receipt = self.moved()
        result = self.cleaner.restore(receipt["batch"])
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual((self.home / "Library/Caches/claude-cli-nodejs/a/b.log").read_bytes(), b"12345")
        self.assertEqual((self.home / ".claude/stats-cache.json").read_bytes(), b"{}")
        again = self.cleaner.restore(receipt["batch"])
        self.assertEqual({item["state"] for item in again["items"]}, {"not_in_trash_batch"})

    def test_restore_never_overwrites_recreated_source(self):
        receipt = self.moved()
        self.file("Library/Caches/claude-cli-nodejs/new.log", b"new")
        self.file(".claude/stats-cache.json", b"new")
        result = self.cleaner.restore(receipt["batch"])
        self.assertEqual(result["status"], "partial")
        self.assertEqual({item["state"] for item in result["items"]}, {"source_recreated_not_overwritten"})
        self.assertEqual((self.home / ".claude/stats-cache.json").read_bytes(), b"new")
        self.assertEqual((self.home / "Library/Caches/claude-cli-nodejs/new.log").read_bytes(), b"new")
        self.assertEqual(len(list((self.trash / receipt["batch"]).iterdir())), 3)

    def test_restore_refuses_changed_trashed_copy(self):
        receipt = self.moved()
        item = next(i for i in receipt["items"] if i["path"] == CACHE)
        (self.trash / receipt["batch"] / item["id"] / "a/b.log").write_bytes(b"tampered-longer")
        result = self.cleaner.restore(receipt["batch"])
        states = {i["path"]: i["state"] for i in result["items"]}
        self.assertEqual(states[CACHE], "trashed_copy_changed_review_required")
        self.assertFalse((self.home / "Library/Caches/claude-cli-nodejs").exists())

    def test_restore_rejects_bad_batch_names(self):
        for name in ("../x", "ClaudeCleanup-1", "", None, "/tmp/x"):
            self.assertEqual(self.cleaner.restore(name)["reason"], "invalid_batch_name")
        self.assertEqual(self.cleaner.restore("ClaudeCleanup-20260101T000000Z-0123456789ab")["reason"], "batch_not_found")

    def test_wrong_or_stale_code_moves_nothing(self):
        self.seed()
        plan = self.cleaner.plan()
        self.assertEqual(self.cleaner.run("0" * 12)["reason"], "confirm_code_mismatch_review_plan_again")
        self.file("Library/Caches/claude-cli-nodejs/a/later.log", b"later")
        stale = self.cleaner.run(plan["confirm_code"])
        self.assertEqual(stale["reason"], "confirm_code_mismatch_review_plan_again")
        self.assertTrue((self.home / ".claude/stats-cache.json").exists())
        self.assertEqual(list(self.trash.iterdir()), [])

    def test_selection_is_bound_to_code(self):
        self.seed()
        full = self.cleaner.plan()
        one = self.cleaner.plan([self.ids(full)[STATS]])
        self.assertNotEqual(full["confirm_code"], one["confirm_code"])
        self.assertEqual(self.cleaner.run(one["confirm_code"])["reason"], "confirm_code_mismatch_review_plan_again")
        receipt = self.cleaner.run(one["confirm_code"], [self.ids(full)[STATS]])
        self.assertEqual(receipt["status"], "complete")
        self.assertTrue((self.home / "Library/Caches/claude-cli-nodejs").exists())

    def test_protected_review_and_unknown_ids_are_rejected(self):
        self.seed()
        from cleanup_manifest import build_manifest
        manifest = build_manifest(self.home, self.apps)
        by_path = {row["path"]: row["id"] for row in manifest["items"]}
        for target in (by_path["~/.claude/projects"], by_path["~/.claude/settings.json"],
                       by_path["~/.claude"], by_path["~/.teamo"], "f" * 16, "../../etc"):
            with self.assertRaises(Stop):
                self.cleaner.plan([target])
            self.assertEqual(self.cleaner.run("x", [target])["reason"], "unknown_or_protected_item_id")
        with self.assertRaises(Stop):
            self.cleaner.plan([])

    def test_process_running_or_unknown_blocks(self):
        self.seed()
        code = self.cleaner.plan()["confirm_code"]
        for probe, reason in (({"complete": True, "running": ["Claude"]}, "relevant_process_running"),
                              ({"complete": False, "running": []}, "process_state_unknown"),
                              (None, "process_state_unknown")):
            self.probe = probe
            self.assertIn(reason, self.cleaner.plan()["blockers"])
            self.assertEqual(self.cleaner.run(code)["reason"], reason)
        self.assertEqual(list(self.trash.iterdir()), [])

    def test_incomplete_samples_are_retried_but_never_accepted(self):
        self.seed()
        samples = iter([{"complete": False, "running": []}, None, QUIET] * 50)
        self.cleaner.process_probe = lambda: next(samples)
        plan = self.cleaner.plan()
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(self.cleaner.run(plan["confirm_code"])["status"], "complete")
        calls = {"n": 0}

        def never_complete():
            calls["n"] += 1
            return {"complete": False, "running": []}
        self.cleaner.process_probe = never_complete
        self.assertIn("process_state_unknown", self.cleaner.plan()["blockers"])
        self.assertEqual(calls["n"], self.cleaner.probe_attempts)
        # An incomplete sample that already shows Claude blocks at once, without retrying.
        calls["n"] = 0

        def incomplete_but_running():
            calls["n"] += 1
            return {"complete": False, "running": ["Claude"]}
        self.cleaner.process_probe = incomplete_but_running
        self.assertIn("relevant_process_running", self.cleaner.plan()["blockers"])
        self.assertEqual(calls["n"], 1)

    def test_stop_reason_is_written_to_the_batch_receipt(self):
        import json
        self.seed()
        code = self.cleaner.plan()["confirm_code"]
        calls = {"n": 0}

        def probe():
            calls["n"] += 1
            return QUIET if calls["n"] <= 2 else {"complete": True, "running": ["Claude"]}
        self.cleaner.process_probe = probe
        receipt = self.cleaner.run(code)
        saved = json.loads((self.trash / receipt["batch"] / "receipt.json").read_text())
        self.assertEqual(saved["reason"], "relevant_process_running")
        self.assertEqual(saved["status"], "stopped")

    def test_process_appearing_mid_run_stops_before_next_item(self):
        self.seed()
        code = self.cleaner.plan()["confirm_code"]
        calls = {"n": 0}

        def probe():
            calls["n"] += 1
            return QUIET if calls["n"] <= 2 else {"complete": True, "running": ["Claude"]}
        self.cleaner.process_probe = probe
        receipt = self.cleaner.run(code)
        self.assertEqual(receipt["reason"], "relevant_process_running")
        self.assertEqual([i["state"] for i in receipt["items"]], ["moved", "not_moved"])

    def test_symlinked_target_or_parent_is_never_moved(self):
        outside = self.home.parent / "outside"
        (outside / "claude-cli-nodejs").mkdir(parents=True)
        (outside / "claude-cli-nodejs/x").write_bytes(b"x")
        (self.home / "Library/Caches").mkdir(parents=True)
        (self.home / "Library/Caches/claude-cli-nodejs").symlink_to(outside / "claude-cli-nodejs")
        (self.home / "Library/Logs").symlink_to(outside)
        (outside / "Claude").mkdir()
        plan = self.cleaner.plan()
        self.assertEqual(plan["items"], [])
        self.assertIn("nothing_to_move", plan["blockers"])
        self.assertEqual({i["reason"] for i in plan["skipped"]}, {"blocked_symlink"})
        self.assertEqual(self.cleaner.run(plan["confirm_code"])["reason"], "nothing_to_move")
        self.assertTrue((outside / "claude-cli-nodejs/x").exists())

    def test_scan_limit_skips_item_instead_of_moving_unreviewed(self):
        self.seed()
        for index in range(6):
            self.file(f"Library/Logs/Claude/{index}.log")
        cleaner = TrashCleaner(self.home, self.apps, self.trash, lambda: QUIET, scan_entries=4)
        plan = cleaner.plan()
        self.assertEqual({i["path"]: i["reason"] for i in plan["skipped"]},
                         {"~/Library/Logs/Claude": "metadata_scan_limit"})
        receipt = cleaner.run(plan["confirm_code"])
        self.assertEqual(receipt["status"], "complete")
        self.assertTrue((self.home / "Library/Logs/Claude/0.log").exists())

    def test_cross_volume_fails_without_copy_fallback(self):
        self.seed()
        code = self.cleaner.plan()["confirm_code"]
        real_rename = os.rename

        def rename(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
            if src_dir_fd != dst_dir_fd:  # the item move; receipt writes stay inside the batch
                raise OSError(errno.EXDEV, "x")
            return real_rename(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
        with patch.object(trash_cleanup.os, "rename", side_effect=rename):
            receipt = self.cleaner.run(code)
        self.assertEqual(receipt["reason"], "cross_volume_not_supported")
        self.assertEqual({i["state"] for i in receipt["items"]}, {"not_moved"})
        self.assertTrue((self.home / "Library/Caches/claude-cli-nodejs/a/b.log").exists())
        self.assertTrue((self.home / ".claude/stats-cache.json").exists())

    def test_trash_missing_symlinked_or_custom_config_dir_blocks(self):
        self.seed()
        os.environ["CLAUDE_CONFIG_DIR"] = "/private/value"
        self.assertIn("custom_claude_config_dir_out_of_scope", self.cleaner.plan()["blockers"])
        del os.environ["CLAUDE_CONFIG_DIR"]
        self.trash.rmdir()
        self.assertIn("trash_not_found", self.cleaner.plan()["blockers"])
        real = self.home.parent / "elsewhere"
        real.mkdir()
        self.trash.symlink_to(real)
        plan = self.cleaner.plan()
        self.assertIn("trash_not_a_private_directory", plan["blockers"])
        self.assertEqual(self.cleaner.run(plan["confirm_code"])["reason"], "trash_not_a_private_directory")
        self.assertEqual(list(real.iterdir()), [])

    def test_cli_has_no_path_or_root_option_and_requires_confirm(self):
        for argv in (["run", "--confirm", "x", "--home", "/tmp"], ["plan", "--trash", "/tmp"],
                     ["plan", "/tmp/anything"], ["run"], ["restore"], []):
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                trash_cleanup.main(argv)

    def test_cli_output_uses_display_paths_only(self):
        self.seed()
        out = io.StringIO()
        with patch.object(trash_cleanup, "TrashCleaner", lambda: self.cleaner), redirect_stdout(out):
            self.assertEqual(trash_cleanup.main(["plan"]), 0)
            code = self.cleaner.plan()["confirm_code"]
            self.assertEqual(trash_cleanup.main(["run", "--confirm", code]), 0)
        self.assertIn("restore --batch ClaudeCleanup-", out.getvalue())
        self.assertNotIn(str(self.home), out.getvalue())


if __name__ == "__main__":
    unittest.main()
