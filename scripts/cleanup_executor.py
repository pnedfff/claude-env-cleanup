"""Fixture-only cleanup transactions. No live-user CLI or arbitrary-root entrypoint."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import pathlib
import shutil
import stat
import tempfile
import time
import uuid
from contextlib import contextmanager

from cleanup_manifest import definitions, metadata


class Stop(Exception):
    """Only fixed, secret-free reason codes should be passed here."""


def signature(info):
    # Rename changes ctime; inode, contents, mode and mtime must still match.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid,
            info.st_size, info.st_mtime_ns, info.st_nlink)


def evaluate_process_snapshot(records, *, complete=False):
    """Classify an explicitly complete snapshot without logging process arguments."""
    if complete is not True or not isinstance(records, list):
        return {"complete": False, "running": []}
    running = set()
    seen = set()
    for record in records:
        if (not isinstance(record, dict) or type(record.get("pid")) is not int
                or record["pid"] <= 0 or record["pid"] in seen
                or not isinstance(record.get("executable"), str) or not record["executable"]):
            return {"complete": False, "running": []}
        seen.add(record["pid"])
        executable = record["executable"]
        name = pathlib.PurePath(executable).name.lower()
        if name in {"claude", "claude-code"} or "/Claude.app/Contents/" in executable:
            running.add("Claude")
        if name in {"teamo", "teamo-code"} or "/.teamo/" in executable:
            running.add("Teamo")
        if "Claude-to-IM-skill" in executable or record.get("label") == "com.claude-to-im.bridge":
            running.add("Claude-to-IM")
    return {"complete": True, "running": sorted(running)}


class FixtureWorkspace:
    """Owns an internally created TemporaryDirectory; callers cannot choose a live root."""
    def __init__(self, process_probe=None):
        self._temp = tempfile.TemporaryDirectory(prefix="claude-cleanup-fixture-")
        self.root = pathlib.Path(self._temp.name).resolve()
        self.home = self.root / "home"
        self.applications = self.root / "applications"
        self.backups = self.root / "backups"
        for path in (self.home, self.applications, self.backups):
            path.mkdir(mode=0o700)
        self._identity = signature(self.root.lstat())[:2]
        self._plans = {}
        self.process_probe = process_probe or (lambda: {"complete": False, "running": []})

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._temp.cleanup()

    def _root_fd(self):
        if signature(self.root.lstat())[:2] != self._identity:
            raise Stop("workspace_replaced")
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        if signature(os.fstat(fd))[:2] != self._identity:
            os.close(fd)
            raise Stop("workspace_replaced")
        return fd

    @contextmanager
    def _parent(self, path):
        relative = path.relative_to(self.root)
        if not relative.parts or any(p in {".", ".."} for p in relative.parts):
            raise Stop("invalid_path")
        fd = self._root_fd()
        try:
            for name in relative.parts[:-1]:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
                if os.fstat(fd).st_uid != os.getuid():
                    raise Stop("foreign_owner")
            yield fd, relative.name
        finally:
            os.close(fd)

    @contextmanager
    def _lock(self):
        root = self._root_fd()
        try:
            fd = os.open("execution.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=root)
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_nlink != 1:
                    raise Stop("invalid_lock")
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield
            finally:
                os.close(fd)
        finally:
            os.close(root)

    def _process_guard(self):
        result = self.process_probe()
        if not isinstance(result, dict) or result.get("complete") is not True or not isinstance(result.get("running"), list):
            raise Stop("process_state_unknown")
        # Includes Teamo/shared-state users and the bridge; never kill any process.
        if result["running"]:
            raise Stop("relevant_process_running")

    def _walk(self, parent, name, output_parent=None, output_name=None, budget=None, prefix="."):
        budget = budget or {"count": 0, "bytes": 0, "start": time.monotonic()}
        budget["count"] += 1
        if budget["count"] > 10000 or time.monotonic() - budget["start"] > 15:
            raise Stop("snapshot_limit")
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(fd)
            if before.st_uid != os.getuid():
                raise Stop("foreign_owner")
            if stat.S_ISDIR(before.st_mode):
                record = {"relative": prefix, "kind": "directory", "identity": signature(before)}
                records = [record]
                out = None
                if output_parent is not None:
                    os.mkdir(output_name, 0o700, dir_fd=output_parent)
                    out = os.open(output_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=output_parent)
                try:
                    for child in sorted(os.listdir(fd)):
                        if child in {".", ".."}:
                            raise Stop("invalid_child")
                        records.extend(self._walk(fd, child, out, child, budget, prefix + "/" + child))
                    if out is not None:
                        os.fsync(out)
                finally:
                    if out is not None:
                        os.close(out)
            elif stat.S_ISREG(before.st_mode):
                if before.st_nlink != 1:
                    raise Stop("hardlink_not_supported")
                digest = hashlib.sha256()
                size = 0
                out = None
                if output_parent is not None:
                    out = os.open(output_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                  0o600, dir_fd=output_parent)
                try:
                    while block := os.read(fd, 1024 * 1024):
                        size += len(block)
                        budget["bytes"] += len(block)
                        if budget["bytes"] > 256 * 1024 * 1024 or time.monotonic() - budget["start"] > 15:
                            raise Stop("snapshot_limit")
                        digest.update(block)
                        if out is not None:
                            remaining = memoryview(block)
                            while remaining:
                                written = os.write(out, remaining)
                                if written <= 0:
                                    raise Stop("backup_write_failed")
                                remaining = remaining[written:]
                    if out is not None:
                        os.fsync(out)
                finally:
                    if out is not None:
                        os.close(out)
                records = [{"relative": prefix, "kind": "file", "identity": signature(before),
                            "bytes": size, "sha256": digest.hexdigest()}]
            else:
                raise Stop("special_file_not_supported")
            if signature(os.fstat(fd)) != signature(before):
                raise Stop("changed_during_snapshot")
            return records
        finally:
            os.close(fd)

    def _parent_identity(self, path):
        with self._parent(path) as (fd, _):
            info = os.fstat(fd)
            return (info.st_dev, info.st_ino, info.st_mode, info.st_uid)

    def _snapshot(self, path):
        with self._parent(path) as (fd, name):
            return self._walk(fd, name)

    @staticmethod
    def _contents(records):
        return [{k: v for k, v in record.items() if k != "identity"} for record in records]

    def _targets(self, manifest, ids):
        if manifest.get("schema_version") != 2 or manifest.get("scope") != "claude":
            raise Stop("fresh_claude_manifest_required")
        if not ids or len(ids) != len(set(ids)):
            raise Stop("invalid_selection")
        known = {hashlib.sha256(row[2].encode()).hexdigest()[:16]: row
                 for row in definitions(self.home, self.applications, "claude")}
        items = manifest.get("items")
        if not isinstance(items, list) or len({item["id"] for item in items}) != len(items):
            raise Stop("invalid_manifest")
        supplied = {item["id"]: item for item in items}
        targets = []
        for item_id in ids:
            if item_id not in known or item_id not in supplied:
                raise Stop("unknown_item_id")
            path, anchor, display, category, _, policy, _, _, external = known[item_id]
            item = supplied[item_id]
            if policy != "candidate" or category != "cache" or external:
                raise Stop("protected_or_review_only")
            # Do not even inspect a caller-mutated workspace path outside our fixture.
            path.relative_to(self.root)
            if item.get("path") != display or item.get("policy") != policy or item.get("disposition") != "candidate":
                raise Stop("manifest_tampered_or_not_candidate")
            current = metadata(path, anchor)
            if current.get("state") != "present" or current != item.get("observation"):
                raise Stop("path_state_changed")
            targets.append((item_id, path))
        return targets

    def prepare(self, manifest, ids):
        """Return a reviewable, one-use plan; do not create backups or remove targets."""
        with self._lock():
            self._process_guard()
            targets = self._targets(manifest, ids)
            parents = {item_id: self._parent_identity(path) for item_id, path in targets}
            snapshots = {item_id: self._snapshot(path) for item_id, path in targets}
            # Reject a replacement between metadata review and content snapshot.
            self._targets(manifest, ids)
            self._process_guard()
            plan = {"plan_id": uuid.uuid4().hex, "mode": "fixture_only", "requires_review": True,
                    "items": [{"id": item_id, "path": "~/" + str(path.relative_to(self.home)),
                               "action": "backup_then_remove_cache",
                               "entries": len(snapshots[item_id]),
                               "bytes": sum(r.get("bytes", 0) for r in snapshots[item_id])}
                              for item_id, path in targets]}
            self._plans[plan["plan_id"]] = (copy.deepcopy(plan), targets, snapshots, parents)
            return plan

    def _copy_backup(self, path, destination):
        with self._parent(path) as (src, name), self._parent(destination) as (dst, output):
            return self._walk(src, name, dst, output)

    def _delete_staged(self, path):
        with self._parent(path) as (parent, name):
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if stat.S_ISREG(info.st_mode):
                os.unlink(name, dir_fd=parent)
            elif stat.S_ISDIR(info.st_mode) and shutil.rmtree.avoids_symlink_attacks:
                shutil.rmtree(name, dir_fd=parent)
            else:
                raise Stop("safe_removal_unavailable")

    def execute(self, plan):
        """Execute only a registered fixture plan; stop on the first error."""
        receipt = {"mode": "fixture_only", "status": "stopped", "items": [], "backup_verified": False}
        staged = None
        source = None
        current_index = None
        deleting = False
        try:
            with self._lock():
                saved = self._plans.pop(plan.get("plan_id"), None)
                if saved is None or plan != saved[0]:
                    raise Stop("unknown_or_tampered_plan")
                _, targets, snapshots, parents = saved
                receipt["items"] = [{"id": item_id, "state": "not_executed"} for item_id, _ in targets]
                self._process_guard()
                for item_id, path in targets:
                    if self._parent_identity(path) != parents[item_id] or self._snapshot(path) != snapshots[item_id]:
                        raise Stop("path_state_changed")
                transaction = self.backups / uuid.uuid4().hex
                # Validate parent without following any link before mutation.
                with self._parent(transaction) as (fd, name):
                    os.mkdir(name, 0o700, dir_fd=fd)
                stage_dir = transaction / "staged"
                with self._parent(stage_dir) as (fd, name):
                    os.mkdir(name, 0o700, dir_fd=fd)
                receipt["backup_directory"] = str(transaction)
                # All selected backups must verify before the first removal.
                for item_id, path in targets:
                    self._process_guard()
                    destination = transaction / item_id
                    copied = self._copy_backup(path, destination)
                    if (self._parent_identity(path) != parents[item_id] or copied != snapshots[item_id]
                            or self._snapshot(path) != snapshots[item_id]):
                        raise Stop("changed_during_backup")
                    if self._contents(self._snapshot(destination)) != self._contents(snapshots[item_id]):
                        raise Stop("backup_verification_failed")
                backup_manifest = {"items": [{"id": item_id, "original": str(path.relative_to(self.home)),
                                               "snapshot": snapshots[item_id]} for item_id, path in targets]}
                encoded = json.dumps(backup_manifest, sort_keys=True).encode()
                with self._parent(transaction / "backup-manifest.json") as (fd, name):
                    out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
                    with os.fdopen(out, "wb") as handle:
                        handle.write(encoded)
                        handle.flush()
                        os.fsync(handle.fileno())
                # Read back the manifest as well as every payload immediately before execution.
                with self._parent(transaction / "backup-manifest.json") as (fd, name):
                    check = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                    with os.fdopen(check, "rb") as handle:
                        if handle.read() != encoded:
                            raise Stop("backup_manifest_verification_failed")
                    os.fsync(fd)
                for item_id, _ in targets:
                    if self._contents(self._snapshot(transaction / item_id)) != self._contents(snapshots[item_id]):
                        raise Stop("backup_verification_failed")
                receipt["backup_verified"] = True
                for index, (item_id, path) in enumerate(targets):
                    current_index = index
                    self._process_guard()
                    if self._contents(self._snapshot(transaction / item_id)) != self._contents(snapshots[item_id]):
                        raise Stop("backup_verification_failed")
                    if self._parent_identity(path) != parents[item_id] or self._snapshot(path) != snapshots[item_id]:
                        raise Stop("path_state_changed")
                    staged = stage_dir / item_id
                    source = path
                    with self._parent(path) as (src, name), self._parent(staged) as (dst, output):
                        os.rename(name, output, src_dir_fd=src, dst_dir_fd=dst)
                    # Verify what was actually moved, not a possibly recreated original path.
                    if self._snapshot(staged) != snapshots[item_id]:
                        raise Stop("staged_state_changed")
                    self._process_guard()
                    deleting = True
                    self._delete_staged(staged)
                    deleting = False
                    staged = None
                    source = None
                    receipt["items"][index]["state"] = "removed"
                receipt["status"] = "complete"
        except Exception as exc:
            receipt["reason"] = str(exc) if isinstance(exc, Stop) else type(exc).__name__
            if receipt["reason"] in {"backup_verification_failed", "backup_manifest_verification_failed"}:
                receipt["backup_verified"] = False
            # Keep staged data for explicit recovery; never overwrite a recreated source.
            if current_index is not None:
                receipt["items"][current_index]["state"] = (
                    "removal_failed_may_be_partial" if deleting else
                    "staged_preserved" if staged is not None else "failed_before_removal")
            if staged is not None and source is not None:
                receipt["staged_recovery"] = str(staged)
                receipt["recovery_state"] = "manual_review_required"
        return receipt


if __name__ == "__main__":
    raise SystemExit("Live cleanup is disabled. Run test_cleanup_executor.py with temporary fixtures only.")
