"""Fixture-only execution tests. All process observations are fake."""
import copy
import os
import pathlib
import stat
import unittest
from unittest.mock import patch

from cleanup_executor import FixtureWorkspace, Stop, evaluate_process_snapshot
from cleanup_manifest import build_manifest


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.workspace = FixtureWorkspace(lambda: {"complete": True, "running": []})
        self.addCleanup(self.workspace.__exit__, None, None, None)
        self.home = self.workspace.home

    def file(self, relative, content=b"fixture-secret-content"):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def manifest(self):
        return build_manifest(self.home, self.workspace.applications)

    def plan(self, *paths):
        manifest = self.manifest()
        by_path = {row["path"]: row["id"] for row in manifest["items"]}
        ids = [by_path[path] for path in paths]
        return self.workspace.prepare(manifest, ids)

    def test_file_removed_only_after_verified_backup(self):
        path = self.file(".claude/stats-cache.json")
        plan = self.plan("~/.claude/stats-cache.json")
        self.assertTrue(path.exists())
        receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["status"], "complete")
        self.assertTrue(receipt["backup_verified"])
        self.assertFalse(path.exists())
        backup = pathlib.Path(receipt["backup_directory"])
        self.assertEqual((backup / plan["items"][0]["id"]).read_bytes(), b"fixture-secret-content")
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o700)
        self.assertNotIn("fixture-secret-content", str(receipt))

    def test_directory_and_empty_children_backup(self):
        self.file(".claude/cache/sub/file")
        (self.home / ".claude/cache/empty").mkdir()
        receipt = self.workspace.execute(self.plan("~/.claude/cache"))
        self.assertEqual(receipt["status"], "complete")
        backup = pathlib.Path(receipt["backup_directory"]) / receipt["items"][0]["id"]
        self.assertTrue((backup / "empty").is_dir())
        self.assertEqual((backup / "sub/file").read_bytes(), b"fixture-secret-content")

    def test_protected_and_review_items_rejected_despite_forgery(self):
        for relative in (".claude/projects", ".claude/settings.json", ".claude/.credentials.json", ".teamo"):
            path = self.file(relative)
            doc = self.manifest()
            item = next(row for row in doc["items"] if row["path"] == "~/" + relative)
            item.update(policy="candidate", disposition="candidate")
            with self.assertRaises(Stop):
                self.workspace.prepare(doc, [item["id"]])
            self.assertEqual(path.read_bytes(), b"fixture-secret-content")

    def test_unknown_duplicate_and_empty_ids_rejected(self):
        self.file(".claude/cache/item")
        doc = self.manifest()
        item_id = next(row["id"] for row in doc["items"] if row["path"] == "~/.claude/cache")
        for ids in ([], ["unknown"], [item_id, item_id]):
            with self.assertRaises(Stop):
                self.workspace.prepare(doc, ids)

    def test_inventory_changed_before_prepare(self):
        path = self.file(".claude/stats-cache.json", b"before")
        doc = self.manifest()
        item_id = next(row["id"] for row in doc["items"] if row["path"] == "~/.claude/stats-cache.json")
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(Stop, "path_state_changed"):
            self.workspace.prepare(doc, [item_id])

    def test_same_size_content_change_after_prepare(self):
        path = self.file(".claude/stats-cache.json", b"AAAA")
        plan = self.plan("~/.claude/stats-cache.json")
        stamp = path.stat()
        path.write_bytes(b"BBBB")
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["reason"], "path_state_changed")
        self.assertEqual(path.read_bytes(), b"BBBB")

    def test_new_directory_child_after_prepare(self):
        path = self.file(".claude/cache/first")
        plan = self.plan("~/.claude/cache")
        self.file(".claude/cache/new")
        self.assertEqual(self.workspace.execute(plan)["status"], "stopped")
        self.assertTrue(path.exists())

    def test_symlink_parent_after_prepare_does_not_touch_outside(self):
        self.file(".claude/stats-cache.json")
        plan = self.plan("~/.claude/stats-cache.json")
        original = self.home / ".claude"
        original.rename(self.home / "old-claude")
        outside = self.workspace.root / "outside"
        outside.mkdir()
        foreign = outside / "stats-cache.json"
        foreign.write_bytes(b"outside")
        original.symlink_to(outside, target_is_directory=True)
        receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["status"], "stopped")
        self.assertEqual(foreign.read_bytes(), b"outside")

    def test_nested_symlink_and_hardlink_rejected(self):
        cache = self.home / ".claude/cache"
        cache.mkdir(parents=True)
        outside = self.file("outside")
        link = cache / "link"
        link.symlink_to(outside)
        with self.assertRaises(OSError):
            self.plan("~/.claude/cache")
        link.unlink()
        os.link(outside, link)
        with self.assertRaisesRegex(Stop, "hardlink_not_supported"):
            self.plan("~/.claude/cache")
        self.assertTrue(outside.exists())

    def test_missing_process_observation_blocks_preparation(self):
        self.file(".claude/cache/item")
        self.workspace.process_probe = lambda: {"complete": False, "running": []}
        with self.assertRaisesRegex(Stop, "process_state_unknown"):
            self.plan("~/.claude/cache")

    def test_teamo_or_bridge_running_blocks_without_killing(self):
        self.file(".claude/cache/item")
        for process in ("Claude", "teamo", "com.claude-to-im.bridge"):
            self.workspace.process_probe = lambda: {"complete": True, "running": [process]}
            with self.assertRaisesRegex(Stop, "relevant_process_running"):
                self.plan("~/.claude/cache")

    def test_process_restarts_before_execution(self):
        path = self.file(".claude/cache/item")
        plan = self.plan("~/.claude/cache")
        self.workspace.process_probe = lambda: {"complete": True, "running": ["teamo"]}
        receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["reason"], "relevant_process_running")
        self.assertTrue(path.exists())

    def test_backup_corruption_prevents_all_deletions(self):
        first = self.file(".claude/stats-cache.json")
        second = self.file(".claude/cache/item")
        plan = self.plan("~/.claude/stats-cache.json", "~/.claude/cache")
        original = self.workspace._copy_backup
        def corrupt(path, destination):
            result = original(path, destination)
            if destination.is_file():
                destination.write_bytes(b"corrupt")
            return result
        with patch.object(self.workspace, "_copy_backup", side_effect=corrupt), \
             patch.object(self.workspace, "_delete_staged") as delete:
            receipt = self.workspace.execute(plan)
            delete.assert_not_called()
        self.assertEqual(receipt["reason"], "backup_verification_failed")
        self.assertFalse(receipt["backup_verified"])
        self.assertTrue(first.exists() and second.exists())

    def test_backup_write_failure_prevents_all_deletions(self):
        path = self.file(".claude/cache/item")
        plan = self.plan("~/.claude/cache")
        with patch.object(self.workspace, "_copy_backup", side_effect=OSError("fixture-secret")):
            receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["reason"], "OSError")
        self.assertNotIn("fixture-secret", str(receipt))
        self.assertTrue(path.exists())

    def test_changed_during_backup_stops(self):
        path = self.file(".claude/stats-cache.json")
        plan = self.plan("~/.claude/stats-cache.json")
        original = self.workspace._copy_backup
        def change(path, destination):
            result = original(path, destination)
            path.write_bytes(b"new")
            return result
        with patch.object(self.workspace, "_copy_backup", side_effect=change):
            receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["reason"], "changed_during_backup")
        self.assertEqual(path.read_bytes(), b"new")

    def test_failure_stops_remaining_items(self):
        first = self.file(".claude/stats-cache.json")
        second = self.file(".claude/cache/item")
        plan = self.plan("~/.claude/stats-cache.json", "~/.claude/cache")
        with patch.object(self.workspace, "_delete_staged", side_effect=OSError("fixture-secret")) as delete:
            receipt = self.workspace.execute(plan)
        self.assertEqual(delete.call_count, 1)
        self.assertEqual(receipt["items"][0]["state"], "removal_failed_may_be_partial")
        self.assertEqual(receipt["items"][1]["state"], "not_executed")
        self.assertTrue(receipt["backup_verified"])
        self.assertTrue(second.exists())
        self.assertTrue(pathlib.Path(receipt["staged_recovery"]).exists())

    def test_process_restart_stops_after_first_removal(self):
        self.file(".claude/stats-cache.json")
        second = self.file(".claude/cache/item")
        plan = self.plan("~/.claude/stats-cache.json", "~/.claude/cache")
        original = self.workspace._delete_staged
        def restart(path):
            original(path)
            self.workspace.process_probe = lambda: {"complete": True, "running": ["teamo"]}
        with patch.object(self.workspace, "_delete_staged", side_effect=restart):
            receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["items"][0]["state"], "removed")
        self.assertEqual(receipt["items"][1]["state"], "failed_before_removal")
        self.assertTrue(second.exists())

    def test_tampered_plan_and_replay_rejected(self):
        path = self.file(".claude/cache/item")
        plan = self.plan("~/.claude/cache")
        altered = copy.deepcopy(plan)
        altered["items"][0]["action"] = "remove_shared_history"
        self.assertEqual(self.workspace.execute(altered)["reason"], "unknown_or_tampered_plan")
        self.assertEqual(self.workspace.execute(plan)["reason"], "unknown_or_tampered_plan")
        self.assertTrue(path.exists())

    def test_backup_parent_symlink_rejected(self):
        path = self.file(".claude/cache/item")
        plan = self.plan("~/.claude/cache")
        self.workspace.backups.rmdir()
        outside = self.workspace.root / "outside"
        outside.mkdir()
        self.workspace.backups.symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.workspace.execute(plan)["status"], "stopped")
        self.assertTrue(path.exists())
        self.assertFalse(list(outside.iterdir()))

    def test_shared_assets_unchanged_after_success(self):
        protected = [self.file(name) for name in (".claude/projects/session", ".claude/skills/tool",
                      ".teamo/settings.json", "code/Claude-to-IM-skill/file", ".claude.json")]
        before = {path: path.read_bytes() for path in protected}
        self.file(".claude/cache/item")
        receipt = self.workspace.execute(self.plan("~/.claude/cache"))
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(before, {path: path.read_bytes() for path in protected})

    def test_arbitrary_real_root_is_not_an_api_option(self):
        with self.assertRaises(TypeError):
            FixtureWorkspace(root="/Users/kevin")

    def test_parent_replaced_with_original_file_moved_is_rejected(self):
        path = self.file(".claude/stats-cache.json")
        plan = self.plan("~/.claude/stats-cache.json")
        parent = path.parent
        parent.rename(self.home / "old-parent")
        parent.mkdir()
        (self.home / "old-parent" / path.name).rename(path)
        receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["reason"], "path_state_changed")
        self.assertTrue(path.exists())

    def test_corruption_between_removals_stops_next_item(self):
        self.file(".claude/stats-cache.json")
        second = self.file(".claude/cache/item")
        plan = self.plan("~/.claude/stats-cache.json", "~/.claude/cache")
        original = self.workspace._delete_staged
        def corrupt_next(path):
            original(path)
            backup = path.parent.parent / plan["items"][1]["id"] / "item"
            backup.write_bytes(b"corrupt")
        with patch.object(self.workspace, "_delete_staged", side_effect=corrupt_next):
            receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["reason"], "backup_verification_failed")
        self.assertFalse(receipt["backup_verified"])
        self.assertEqual(receipt["items"][0]["state"], "removed")
        self.assertTrue(second.exists())

    def test_recreated_original_not_overwritten_on_staged_failure(self):
        path = self.file(".claude/stats-cache.json")
        plan = self.plan("~/.claude/stats-cache.json")
        def fail_after_recreation(staged):
            path.write_bytes(b"new-original")
            raise OSError("fixture-secret")
        with patch.object(self.workspace, "_delete_staged", side_effect=fail_after_recreation):
            receipt = self.workspace.execute(plan)
        self.assertEqual(path.read_bytes(), b"new-original")
        self.assertEqual(pathlib.Path(receipt["staged_recovery"]).read_bytes(), b"fixture-secret-content")

    def test_deleted_target_stops_before_backup(self):
        path = self.file(".claude/stats-cache.json")
        plan = self.plan("~/.claude/stats-cache.json")
        path.unlink()
        receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["status"], "stopped")
        self.assertNotIn("backup_directory", receipt)

    def test_legacy_inventory_requires_regeneration(self):
        self.file(".claude/cache/item")
        doc = self.manifest()
        doc["schema_version"] = 1
        item_id = next(row["id"] for row in doc["items"] if row["path"] == "~/.claude/cache")
        with self.assertRaisesRegex(Stop, "fresh_claude_manifest_required"):
            self.workspace.prepare(doc, [item_id])

    def test_process_classifier_preserves_shared_runtime_identity(self):
        observed = evaluate_process_snapshot([
            {"pid": 1, "executable": "/fixture/bin/teamo"},
            {"pid": 2, "executable": "/fixture/bin/claude", "parent": "teamo"},
            {"pid": 3, "executable": "/fixture/bin/node", "label": "com.claude-to-im.bridge"},
        ], complete=True)
        self.assertEqual(observed, {"complete": True, "running": ["Claude", "Claude-to-IM", "Teamo"]})

    def test_unknown_or_malformed_process_snapshot_blocks(self):
        for records in (None, [{"pid": 1}], [{"pid": 1, "executable": "claude"}] * 2):
            self.assertFalse(evaluate_process_snapshot(records, complete=True)["complete"])
        self.assertFalse(evaluate_process_snapshot([])["complete"])

    def test_mutated_workspace_home_cannot_inspect_external_path(self):
        self.file(".claude/cache/item")
        doc = self.manifest()
        item_id = next(row["id"] for row in doc["items"] if row["path"] == "~/.claude/cache")
        self.workspace.home = self.workspace.root.parent / "not-our-home"
        with patch("cleanup_executor.metadata", side_effect=AssertionError("outside inspection forbidden")) as inspect:
            with self.assertRaises(ValueError):
                self.workspace.prepare(doc, [item_id])
            inspect.assert_not_called()

    def test_process_restart_after_staging_preserves_data(self):
        path = self.file(".claude/stats-cache.json")
        plan = self.plan("~/.claude/stats-cache.json")
        self.workspace.process_probe = lambda: {"complete": True, "running": [] if path.exists() else ["Claude"]}
        with patch.object(self.workspace, "_delete_staged") as delete:
            receipt = self.workspace.execute(plan)
            delete.assert_not_called()
        self.assertEqual(receipt["reason"], "relevant_process_running")
        self.assertEqual(receipt["items"][0]["state"], "staged_preserved")
        self.assertEqual(pathlib.Path(receipt["staged_recovery"]).read_bytes(), b"fixture-secret-content")

    def test_partial_delete_is_reported_and_backup_survives(self):
        self.file(".claude/cache/first")
        self.file(".claude/cache/second")
        plan = self.plan("~/.claude/cache")
        def partial(path):
            (path / "first").unlink()
            raise OSError("fixture-secret")
        with patch.object(self.workspace, "_delete_staged", side_effect=partial):
            receipt = self.workspace.execute(plan)
        self.assertEqual(receipt["items"][0]["state"], "removal_failed_may_be_partial")
        backup = pathlib.Path(receipt["backup_directory"]) / plan["items"][0]["id"]
        self.assertTrue((backup / "first").exists() and (backup / "second").exists())

    def test_second_backup_failure_keeps_all_sources(self):
        first = self.file(".claude/stats-cache.json")
        second = self.file(".claude/cache/item")
        plan = self.plan("~/.claude/stats-cache.json", "~/.claude/cache")
        original = self.workspace._copy_backup
        calls = []
        def fail_second(path, destination):
            calls.append(path)
            if len(calls) == 2:
                raise OSError("fixture-secret")
            return original(path, destination)
        with patch.object(self.workspace, "_copy_backup", side_effect=fail_second), \
             patch.object(self.workspace, "_delete_staged") as delete:
            receipt = self.workspace.execute(plan)
            delete.assert_not_called()
        self.assertEqual(receipt["status"], "stopped")
        self.assertTrue(first.exists() and second.exists())


if __name__ == "__main__":
    unittest.main()
