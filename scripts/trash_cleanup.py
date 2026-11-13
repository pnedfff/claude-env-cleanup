"""Live cleanup for fixed Claude cache/log candidates only: move to a Trash batch, never delete.

No path or root flag exists on the CLI. Targets are rebuilt from fixed item IDs.
"""
from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import hmac
import json
import os
import pathlib
import re
import stat
from datetime import datetime, timezone

from cleanup_manifest import build_manifest, definitions
from production_preflight import collect_processes, inspect_tree

BATCH_NAME = re.compile(r"^ClaudeCleanup-\d{8}T\d{6}Z-[0-9a-f]{12}$")
ITEM_ID = re.compile(r"^[0-9a-f]{16}$")
RECEIPT = "receipt.json"


class Stop(Exception):
    """Only fixed, secret-free reason codes should be passed here."""


def open_dir(path):
    """Open a directory component by component from the OS root, refusing symlinks."""
    path = pathlib.Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise Stop("invalid_path")
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in path.parts[1:]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def write_receipt(batch_fd, receipt):
    payload = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True).encode()
    out = os.open(RECEIPT + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600, dir_fd=batch_fd)
    with os.fdopen(out, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(RECEIPT + ".tmp", RECEIPT, src_dir_fd=batch_fd, dst_dir_fd=batch_fd)


def read_receipt(batch_fd):
    fd = os.open(RECEIPT, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=batch_fd)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 1024 * 1024:
            raise Stop("invalid_receipt")
        receipt = json.loads(handle.read())
    if (not isinstance(receipt, dict) or receipt.get("mode") != "trash_move"
            or not isinstance(receipt.get("items"), list)):
        raise Stop("invalid_receipt")
    return receipt


class TrashCleaner:
    """Tests may inject home/trash roots; the CLI always uses the current user's real ones."""

    def __init__(self, home=None, applications=None, trash=None, process_probe=None, scan_entries=10000,
                 probe_attempts=12):
        self.home = pathlib.Path.home() if home is None else pathlib.Path(home)
        self.applications = pathlib.Path("/Applications") if applications is None else pathlib.Path(applications)
        self.trash = self.home / ".Trash" if trash is None else pathlib.Path(trash)
        self.process_probe = process_probe or (lambda: collect_processes(self.home))
        self.scan_entries = scan_entries
        self.probe_attempts = probe_attempts

    def _fixed(self):
        """ID -> fixed target. Only cache/log candidates under home ever qualify."""
        fixed = {}
        for path, anchor, display, category, _, policy, _, _, external in definitions(
                self.home, self.applications, "claude"):
            if policy == "candidate" and category == "cache" and not external and anchor == self.home:
                fixed[hashlib.sha256(display.encode()).hexdigest()[:16]] = (path, display)
        return fixed

    def _inspect(self, path, anchor):
        return inspect_tree(path, anchor, max_entries=self.scan_entries)

    def _process_blocker(self):
        # A busy Mac changes its process list between the two ps samples, which marks the
        # sample incomplete. Re-sample a bounded number of times; only a complete sample
        # with nothing running passes, and any sample that shows a relevant process blocks.
        for _ in range(self.probe_attempts):
            result = self.process_probe()
            if not isinstance(result, dict) or not isinstance(result.get("running"), list):
                continue
            # Claude, Teamo, the IM bridge and shared-state users all block. Nothing is ever killed.
            if result["running"]:
                return "relevant_process_running", sorted(str(name) for name in result["running"])
            if result.get("complete") is True:
                return None, []
        return "process_state_unknown", []

    def _guard(self):
        reason, _ = self._process_blocker()
        if reason:
            raise Stop(reason)

    def _trash_blocker(self, items):
        try:
            info = self.trash.lstat()
        except FileNotFoundError:
            return "trash_not_found"
        except OSError:
            # macOS denies ~/.Trash to terminals without Full Disk Access.
            return "trash_unavailable_check_full_disk_access"
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            return "trash_not_a_private_directory"
        if not os.access(self.trash, os.R_OK | os.W_OK | os.X_OK):
            return "trash_unavailable_check_full_disk_access"
        # A move is a same-volume rename. There is no copy-and-delete fallback.
        if any(item["parent"]["dev"] != info.st_dev for item in items):
            return "cross_volume_not_supported"
        return None

    def plan(self, ids=None):
        """Read-only. Returns reviewable items plus a code bound to their current state."""
        fixed = self._fixed()
        if ids is not None and (not ids or len(set(ids)) != len(ids) or any(i not in fixed for i in ids)):
            raise Stop("unknown_or_protected_item_id")
        observed = {item["id"]: item["observation"]["state"]
                    for item in build_manifest(self.home, self.applications, "claude")["items"]}
        items, skipped = [], []
        for item_id, (path, display) in fixed.items():
            if ids is not None and item_id not in ids:
                continue
            if observed[item_id] != "present":
                if observed[item_id] != "not_found" or ids is not None:
                    skipped.append({"id": item_id, "path": display, "reason": observed[item_id]})
                continue
            check = self._inspect(path, self.home)
            if check["state"] != "checked":
                # Scan limits are not raised: an unreviewed tree is left where it is.
                skipped.append({"id": item_id, "path": display, "reason": check.get("reason", "unknown")})
                continue
            items.append({"id": item_id, "path": display, "entries": check["entries"],
                          "bytes": check["estimated_file_bytes"], "digest": check["metadata_digest"],
                          "parent": check["parent_identity"]})
        blockers = []
        reason, running = self._process_blocker()
        if reason:
            blockers.append(reason)
        if os.environ.get("CLAUDE_CONFIG_DIR"):
            blockers.append("custom_claude_config_dir_out_of_scope")
        if not items:
            blockers.append("nothing_to_move")
        trash_reason = self._trash_blocker(items)
        if trash_reason:
            blockers.append(trash_reason)
        bound = [[i["id"], i["path"], i["digest"], i["parent"]] for i in items]
        code = hashlib.sha256(json.dumps(bound, sort_keys=True).encode()).hexdigest()[:12]
        return {"mode": "trash_move", "action": "move_to_trash_batch_no_delete", "items": items,
                "skipped": skipped, "blockers": blockers, "running": running, "confirm_code": code,
                "total_bytes": sum(i["bytes"] for i in items)}

    def run(self, confirm_code, ids=None):
        """Re-plan, require the code from the reviewed plan, then move item by item."""
        receipt = {"mode": "trash_move", "status": "stopped", "batch": None, "items": []}
        try:
            plan = self.plan(ids)
            receipt["items"] = [{"id": i["id"], "path": i["path"], "entries": i["entries"], "bytes": i["bytes"],
                                 "digest": i["digest"], "state": "not_moved"} for i in plan["items"]]
            receipt["skipped"] = plan["skipped"]
            if plan["blockers"]:
                raise Stop(plan["blockers"][0])
            # A changed tree yields a different code, so stale consent cannot be replayed.
            if not isinstance(confirm_code, str) or not hmac.compare_digest(confirm_code, plan["confirm_code"]):
                raise Stop("confirm_code_mismatch_review_plan_again")
            parents = {i["id"]: i["parent"] for i in plan["items"]}
            fixed = self._fixed()
            trash_fd = open_dir(self.trash)
            try:
                try:
                    fcntl.flock(trash_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise Stop("another_cleanup_running")
                batch = "ClaudeCleanup-%s-%s" % (
                    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), plan["confirm_code"])
                os.mkdir(batch, 0o700, dir_fd=trash_fd)
                batch_fd = os.open(batch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=trash_fd)
                receipt["batch"] = batch
                try:
                    write_receipt(batch_fd, receipt)
                    for entry in receipt["items"]:
                        self._guard()
                        path = fixed[entry["id"]][0]
                        check = self._inspect(path, self.home)
                        if (check.get("metadata_digest") != entry["digest"]
                                or check.get("parent_identity") != parents[entry["id"]]):
                            raise Stop("path_state_changed")
                        parent_fd = open_dir(path.parent)
                        try:
                            info = os.fstat(parent_fd)
                            if {"dev": info.st_dev, "ino": info.st_ino, "uid": info.st_uid} != parents[entry["id"]]:
                                raise Stop("path_state_changed")
                            try:
                                os.rename(path.name, entry["id"], src_dir_fd=parent_fd, dst_dir_fd=batch_fd)
                            except OSError as exc:
                                raise Stop("cross_volume_not_supported" if exc.errno == errno.EXDEV else "move_failed")
                        finally:
                            os.close(parent_fd)
                        entry["state"] = "moved"
                        write_receipt(batch_fd, receipt)
                        # Verify what actually arrived, not a possibly recreated original path.
                        moved = self._inspect(self.trash / batch / entry["id"], self.trash)
                        if moved.get("metadata_digest") != entry["digest"]:
                            entry["state"] = "moved_but_differs_review_required"
                            raise Stop("moved_object_differs")
                    receipt["status"] = "complete"
                except Stop as exc:
                    receipt["reason"] = str(exc)
                    raise
                except Exception as exc:
                    receipt["reason"] = type(exc).__name__
                    raise
                finally:
                    try:
                        write_receipt(batch_fd, receipt)
                    finally:
                        os.close(batch_fd)
            finally:
                os.close(trash_fd)
        except Stop as exc:
            receipt["reason"] = str(exc)
        except Exception as exc:
            receipt["reason"] = type(exc).__name__
        return receipt

    def restore(self, batch):
        """Move items of one batch back. A recreated original is never overwritten."""
        result = {"mode": "trash_restore", "status": "stopped", "batch": batch, "items": []}
        try:
            if not isinstance(batch, str) or not BATCH_NAME.match(batch):
                raise Stop("invalid_batch_name")
            self._guard()
            fixed = self._fixed()
            trash_fd = open_dir(self.trash)
            try:
                try:
                    fcntl.flock(trash_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    batch_fd = os.open(batch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=trash_fd)
                except FileNotFoundError:
                    raise Stop("batch_not_found")
                except OSError:
                    raise Stop("batch_unavailable_or_cleanup_running")
                try:
                    receipt = read_receipt(batch_fd)
                    for entry in receipt["items"]:
                        item_id = entry.get("id") if isinstance(entry, dict) else None
                        if not isinstance(item_id, str) or not ITEM_ID.match(item_id) or item_id not in fixed:
                            result["items"].append({"id": None, "state": "unknown_item_skipped"})
                            continue
                        outcome = {"id": item_id, "path": fixed[item_id][1]}
                        result["items"].append(outcome)
                        if entry.get("state") != "moved":
                            outcome["state"] = "not_in_trash_batch"
                            continue
                        outcome["state"] = self._restore_one(batch, batch_fd, item_id, fixed[item_id][0], entry)
                        if outcome["state"] == "restored":
                            entry["state"] = "restored"
                            write_receipt(batch_fd, receipt)
                    states = {item["state"] for item in result["items"]}
                    result["status"] = "complete" if states <= {"restored", "not_in_trash_batch"} else "partial"
                finally:
                    os.close(batch_fd)
            finally:
                os.close(trash_fd)
        except Stop as exc:
            result["reason"] = str(exc)
        except Exception as exc:
            result["reason"] = type(exc).__name__
        return result

    def _restore_one(self, batch, batch_fd, item_id, path, entry):
        # The destination comes from the fixed table, never from the receipt text.
        try:
            path.lstat()
            return "source_recreated_not_overwritten"
        except FileNotFoundError:
            pass
        except OSError:
            return "source_state_unknown"
        if self._inspect(self.trash / batch / item_id, self.trash).get("metadata_digest") != entry.get("digest"):
            return "trashed_copy_changed_review_required"
        try:
            parent_fd = open_dir(path.parent)
        except (OSError, Stop):
            return "original_parent_missing_or_unsafe"
        try:
            info = os.stat(item_id, dir_fd=batch_fd, follow_symlinks=False)
            if stat.S_ISREG(info.st_mode):
                # link() fails if the name exists, so a file recreated meanwhile survives.
                os.link(item_id, path.name, src_dir_fd=batch_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
                os.unlink(item_id, dir_fd=batch_fd)
            else:
                # rename() of a directory fails on a non-empty recreated directory.
                os.rename(item_id, path.name, src_dir_fd=batch_fd, dst_dir_fd=parent_fd)
        except FileExistsError:
            return "source_recreated_not_overwritten"
        except OSError as exc:
            return ("source_recreated_not_overwritten" if exc.errno == errno.ENOTEMPTY
                    else "cross_volume_not_supported" if exc.errno == errno.EXDEV else "restore_failed")
        finally:
            os.close(parent_fd)
        return "restored"


def render_plan(plan):
    lines = ["# Claude 缓存与日志：移入废纸篓计划", "",
             "动作：移入 `~/.Trash/ClaudeCleanup-<时间>-<确认码>/`，不删除，不清空废纸篓。", ""]
    lines += ["| 项目 ID | 路径 | 条目数 | 字节 |", "|---|---|---:|---:|"]
    lines += [f"| {i['id']} | {i['path']} | {i['entries']} | {i['bytes']} |" for i in plan["items"]]
    lines += ["", f"合计：{len(plan['items'])} 项，{plan['total_bytes']} 字节。"]
    if plan["skipped"]:
        lines += ["", "不会处理（留在原处）："]
        lines += [f"- {i['path']}：{i['reason']}" for i in plan["skipped"]]
    if plan["blockers"]:
        lines += ["", "阻塞，当前不能执行：" + "、".join(plan["blockers"])]
        if plan["running"]:
            lines += ["相关进程或共享数据使用者：" + "、".join(plan["running"]) + "。请自行退出后重新生成计划；本工具不会终止任何进程。"]
    else:
        lines += ["", "审阅无误后执行：", "",
                  f"    python3 trash_cleanup.py run --confirm {plan['confirm_code']}", "",
                  "目录内容一旦变化，确认码随之失效，须重新审阅。"]
    return "\n".join(lines) + "\n"


def render_receipt(receipt):
    lines = [f"状态：{receipt['status']}" + (f"；原因：{receipt['reason']}" if receipt.get("reason") else "")]
    if receipt.get("batch"):
        lines.append(f"批次：~/.Trash/{receipt['batch']}")
    lines += [f"- {i.get('path') or i.get('id')}：{i['state']}" for i in receipt["items"]]
    if receipt.get("mode") == "trash_move" and any(i["state"] == "moved" for i in receipt["items"]):
        lines += ["", "撤回（清空废纸篓之前有效；原路径已被重新创建的项不会覆盖）：",
                  f"    python3 trash_cleanup.py restore --batch {receipt['batch']}"]
    return "\n".join(lines) + "\n"


def parse_ids(value):
    return [part for part in value.split(",") if part] if value else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan_parser = commands.add_parser("plan", help="只读：列出可移入废纸篓的缓存/日志项和确认码")
    plan_parser.add_argument("--ids", help="逗号分隔的项目 ID；省略表示全部可处理项")
    plan_parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    run_parser = commands.add_parser("run", help="按已审阅的确认码移入废纸篓批次")
    run_parser.add_argument("--confirm", required=True, help="plan 输出的确认码")
    run_parser.add_argument("--ids", help="须与生成确认码时的选择一致")
    restore_parser = commands.add_parser("restore", help="把一个批次移回原位置")
    restore_parser.add_argument("--batch", required=True, help="回执中的批次名")
    args = parser.parse_args(argv)
    cleaner = TrashCleaner()
    try:
        if args.command == "plan":
            plan = cleaner.plan(parse_ids(args.ids))
            print(json.dumps(plan, ensure_ascii=False, indent=2) if args.format == "json" else render_plan(plan))
            return 2 if plan["blockers"] else 0
        result = cleaner.run(args.confirm, parse_ids(args.ids)) if args.command == "run" else cleaner.restore(args.batch)
    except Stop as exc:
        print(f"状态：stopped；原因：{exc}")
        return 2
    print(render_receipt(result))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
