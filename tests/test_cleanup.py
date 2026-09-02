from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cleanup", ROOT / "cleanup.py")
assert SPEC and SPEC.loader
cleanup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleanup)


class CleanupSafetyTests(unittest.TestCase):
    def test_default_targets_do_not_include_browser_site_data_or_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            targets = [str(path) for path in cleanup.deep_targets(home, home / "Applications")]
        joined = "\n".join(targets)
        self.assertNotIn("/Cookies", joined)
        self.assertNotIn("/Local Storage", joined)
        self.assertNotIn("/IndexedDB", joined)
        self.assertNotIn("/.claude/projects", joined)
        self.assertNotIn("/.claude/skills", joined)

    def test_dry_run_never_moves_or_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cache = home / "Library" / "Caches" / "com.anthropic.claudefordesktop"
            cache.mkdir(parents=True)
            marker = cache / "keep.txt"
            marker.write_text("still here")

            with mock.patch.object(cleanup.shutil, "move") as move:
                result = cleanup.clean(home, deep=False, dry_run=True)

            self.assertEqual(result, 0)
            move.assert_not_called()
            self.assertTrue(marker.exists())
            self.assertFalse((home / "Backups").exists())

    def test_cancel_at_first_confirmation_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cache = home / "Library" / "Caches" / "com.anthropic.claudefordesktop"
            cache.mkdir(parents=True)
            marker = cache / "keep.txt"
            marker.write_text("still here")

            with mock.patch("builtins.input", return_value="n"), mock.patch.object(cleanup.shutil, "move") as move:
                result = cleanup.clean(home, deep=False)

            self.assertEqual(result, 0)
            move.assert_not_called()
            self.assertTrue(marker.exists())

    def test_confirmed_cleanup_moves_to_home_backup_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cache = home / "Library" / "Caches" / "com.anthropic.claudefordesktop"
            cache.mkdir(parents=True)
            (cache / "cache.txt").write_text("data")

            answers = iter(["y", "确认安全清理"])
            with mock.patch("builtins.input", side_effect=lambda _prompt: next(answers)):
                result = cleanup.clean(home, deep=False)

            self.assertEqual(result, 0)
            self.assertFalse(cache.exists())
            backups = list((home / "Backups" / "claude-env-cleanup").glob("safe-*"))
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / "manifest.json").exists())
            self.assertTrue((backups[0] / "HOME" / "Library" / "Caches" / "com.anthropic.claudefordesktop" / "cache.txt").exists())

    def test_cancel_at_second_confirmation_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cache = home / "Library" / "Caches" / "com.anthropic.claudefordesktop"
            cache.mkdir(parents=True)
            marker = cache / "keep.txt"
            marker.write_text("still here")

            answers = iter(["y", "不确认"])
            with mock.patch("builtins.input", side_effect=lambda _prompt: next(answers)), mock.patch.object(cleanup.shutil, "move") as move:
                result = cleanup.clean(home, deep=False)

            self.assertEqual(result, 0)
            move.assert_not_called()
            self.assertTrue(marker.exists())
            self.assertFalse((home / "Backups").exists())


if __name__ == "__main__":
    unittest.main()
