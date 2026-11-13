"""Production read-only process/path preflight. No backup, kill or delete capability."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import time
import uuid
from datetime import datetime, timezone

from cleanup_manifest import build_manifest, definitions
from cleanup_executor import evaluate_process_snapshot, signature


def run_probe(command):
    """Never emit raw output: process utilities can expose private file paths."""
    try:
        result = subprocess.run(command, capture_output=True, timeout=15, check=False)
        if len(result.stdout) + len(result.stderr) > 16 * 1024 * 1024:
            return subprocess.CompletedProcess(command, 999, b"", b"output_limit")
        return result
    except Exception as exc:
        return subprocess.CompletedProcess(command, 999, b"", type(exc).__name__.encode())


def parse_ps(payload, uid):
    records = []
    seen = set()
    for line in payload.decode("utf-8", errors="strict").splitlines():
        if not line.strip():
            continue
        parts = line.strip().split(None, 3)
        if len(parts) != 4 or not all(part.isdecimal() for part in parts[:3]):
            raise ValueError("malformed_ps")
        pid, ppid, owner = map(int, parts[:3])
        if pid <= 0 or pid in seen:
            raise ValueError("malformed_ps")
        seen.add(pid)
        if owner == uid and pathlib.PurePath(parts[3]).name not in {"ps", "lsof"}:
            records.append({"pid": pid, "ppid": ppid, "executable": parts[3]})
    if not seen:
        raise ValueError("empty_ps")
    return records


def parse_lsof(payload):
    """NUL fields preserve filenames containing whitespace or newlines."""
    records = {}
    pid = None
    for raw in payload.split(b"\0"):
        field = raw.lstrip(b"\n")
        if not field:
            continue
        if field[:1] == b"p":
            value = field[1:]
            if not value.isdigit() or int(value) <= 0:
                raise ValueError("malformed_lsof")
            pid = int(value)
            records.setdefault(pid, [])
        elif field[:1] == b"f" and pid is not None:
            continue
        elif field[:1] == b"n" and pid is not None:
            records[pid].append(field[1:].decode("utf-8", errors="replace"))
        else:
            raise ValueError("malformed_lsof")
    return records


def file_groups(name, home):
    groups = set()
    # A file reference is evidence of shared-state access, not proof of official ownership.
    if name.startswith(str(home / ".claude") + "/") or name == str(home / ".claude.json"):
        groups.add("shared_Claude_state_access")
    if name.startswith(str(home / ".teamo") + "/") or "@teamolab/teamo-cli/" in name:
        groups.add("Teamo")
    if (name.startswith(str(home / ".claude-to-im") + "/")
            or name.startswith(str(home / "code/Claude-to-IM-skill") + "/")):
        groups.add("Claude-to-IM")
    if "@anthropic-ai/claude-code/" in name or "/Claude.app/Contents/" in name:
        groups.add("Claude")
    return groups


def collect_processes(home=None, runner=run_probe, uid=None):
    home = pathlib.Path.home() if home is None else pathlib.Path(home)
    uid = os.getuid() if uid is None else uid
    result = {"complete": True, "scope": "current_user_visible_processes", "running": [],
              "sources": [], "observations": [], "errors": [], "sampled_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    processes = []
    groups_by_pid = {}
    ps_command = ["/bin/ps", "-ww", "-axo", "pid=,ppid=,uid=,comm="]
    first = runner(ps_command)
    result["sources"].append("ps_comm_without_arguments")
    try:
        if first.returncode != 0 or first.stderr:
            raise ValueError("ps_unavailable")
        processes = parse_ps(first.stdout, uid)
    except Exception:
        result["complete"] = False
        result["errors"].append("ps_snapshot_unavailable_or_malformed")
    for process in processes:
        evaluated = evaluate_process_snapshot([process], complete=True)
        if evaluated["running"]:
            groups_by_pid[process["pid"]] = set(evaluated["running"])
    lsof = shutil.which("lsof")
    if lsof and processes:
        command = [lsof, "-nP", "-a", "-p", ",".join(str(p["pid"]) for p in processes), "-F0pn"]
        opened = runner(command)
        result["sources"].append("lsof_selected_process_file_references")
        try:
            if opened.returncode != 0 or opened.stderr:
                raise ValueError("lsof_unavailable")
            files = parse_lsof(opened.stdout)
            known_pids = {p["pid"] for p in processes}
            if any(pid not in known_pids for pid in files):
                raise ValueError("unexpected_pid")
            for pid, names in files.items():
                for name in names:
                    found = file_groups(name, home)
                    if found:
                        groups_by_pid.setdefault(pid, set()).update(found)
        except Exception:
            result["complete"] = False
            result["errors"].append("file_reference_check_unavailable_or_malformed")
    else:
        result["complete"] = False
        result["errors"].append("file_reference_check_not_available")
    # launchctl catches a node/python bridge that need not keep its script open.
    launchctl = shutil.which("launchctl")
    if launchctl:
        bridge = runner([launchctl, "print", f"gui/{uid}/com.claude-to-im.bridge"])
        result["sources"].append("launchctl_Claude_to_IM_service")
        if bridge.returncode == 0:
            text = bridge.stdout.decode("utf-8", errors="replace")
            match = re.search(r"^\s*pid = (\d+)\s*$", text, re.MULTILINE)
            if match:
                groups_by_pid.setdefault(int(match.group(1)), set()).add("Claude-to-IM")
            elif not re.search(r"^\s*state = (?:not running|waiting|spawn scheduled|exited)\s*$", text, re.MULTILINE):
                result["complete"] = False
                result["errors"].append("bridge_service_state_or_pid_unknown")
        elif not re.search(rb"Could not find (?:specified )?service", bridge.stderr):
            result["complete"] = False
            result["errors"].append("bridge_service_state_unknown")
    else:
        result["complete"] = False
        result["errors"].append("launchctl_not_available")
    # Re-sample to flag a changing population; exclude the probe utility processes.
    second = runner(ps_command)
    try:
        if second.returncode != 0 or second.stderr:
            raise ValueError("ps_unavailable")
        after = parse_ps(second.stdout, uid)
        if {(p["pid"], p["executable"]) for p in processes} != {(p["pid"], p["executable"]) for p in after}:
            result["complete"] = False
            result["errors"].append("process_population_changed_during_sampling")
        for process in after:
            found = evaluate_process_snapshot([process], complete=True)["running"]
            if found:
                groups_by_pid.setdefault(process["pid"], set()).update(found)
    except Exception:
        result["complete"] = False
        result["errors"].append("second_ps_snapshot_unavailable_or_malformed")
    result["observations"] = [{"pid": pid, "groups": sorted(groups)} for pid, groups in sorted(groups_by_pid.items())]
    result["running"] = sorted({group for groups in groups_by_pid.values() for group in groups})
    result["visible_process_count"] = len(processes)
    return result


def inspect_tree(path, anchor, max_entries=10000, max_seconds=10):
    """Descriptor-based metadata only: do not read config, log or cache content."""
    started = time.monotonic()
    count = 0
    total = 0
    digest = hashlib.sha256()
    def walk(parent, name, relative):
        nonlocal count, total
        count += 1
        if count > max_entries or time.monotonic() - started > max_seconds:
            raise ValueError("metadata_scan_limit")
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(fd)
            if info.st_uid != os.getuid():
                raise ValueError("foreign_owner")
            before = signature(info)
            digest.update(json.dumps([relative, before], separators=(",", ":")).encode())
            if stat.S_ISDIR(info.st_mode):
                for child in sorted(os.listdir(fd)):
                    walk(fd, child, relative + "/" + child)
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                total += info.st_size
            else:
                raise ValueError("special_file_or_hardlink")
            if signature(os.fstat(fd)) != before:
                raise ValueError("changed_during_metadata_scan")
        finally:
            os.close(fd)
    # Open each component from canonical OS root, rejecting user-path links.
    absolute = pathlib.Path(path).absolute()
    absolute.relative_to(pathlib.Path(anchor).absolute())
    if ".." in absolute.parts:
        return {"state": "unknown", "snapshot_kind": "metadata_only", "reason": "invalid_path"}
    fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in absolute.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        parent = os.fstat(fd)
        walk(fd, absolute.name, ".")
        return {"state": "checked", "snapshot_kind": "metadata_only", "entries": count,
                "estimated_file_bytes": total, "metadata_digest": digest.hexdigest(),
                "parent_identity": {"dev": parent.st_dev, "ino": parent.st_ino, "uid": parent.st_uid}}
    except Exception as exc:
        return {"state": "unknown", "snapshot_kind": "metadata_only",
                "reason": str(exc) if type(exc) is ValueError else type(exc).__name__}
    finally:
        os.close(fd)


def backup_preflight(home, plan_id, estimated_bytes, estimate_complete=True):
    destination = home / "Backups" / "ClaudeCleanup" / plan_id
    current = pathlib.Path(destination.anchor)
    nearest = current
    reason = None
    for name in destination.parts[1:]:
        current /= name
        try:
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                reason = "backup_parent_symlink_or_not_directory"
                break
            nearest = current
        except FileNotFoundError:
            break
        except OSError:
            reason = "backup_parent_unavailable"
            break
    required = estimated_bytes + max(16 * 1024 * 1024, estimated_bytes // 5)
    available = None
    if reason is None:
        try:
            capacity = os.statvfs(nearest)
            available = capacity.f_bavail * capacity.f_frsize
            if nearest.lstat().st_uid != os.getuid():
                reason = "backup_parent_owner_unknown_or_foreign"
            elif not os.access(nearest, os.W_OK | os.X_OK):
                reason = "backup_parent_access_unknown_or_denied"
            elif available < required:
                reason = "insufficient_estimated_space"
        except OSError:
            reason = "backup_capacity_unknown"
    return {"state": "blocked" if reason else "planned_not_created" if estimate_complete else "size_incomplete_not_created",
            "reason": reason or (None if estimate_complete else "payload_size_incomplete"),
            "destination": "~/Backups/ClaudeCleanup/" + plan_id, "created": False, "verified": False,
            "payload_estimate_complete": estimate_complete, "known_scanned_payload_bytes": estimated_bytes,
            "estimated_payload_bytes": estimated_bytes if estimate_complete else None,
            "minimum_required_space_bytes": required,
            "required_space_estimate_bytes": required if estimate_complete else None,
            "available_bytes_at_sampling": available, "directory_mode": "0700", "file_mode": "0600",
            "verification_required": ["all_selected_payload_content_hashes", "complete_directory_structure",
                                      "source_unchanged", "backup_manifest_readback", "fsync_before_removal"],
            "restore_policy": "explicit_review_only; never overwrite recreated source"}


def build_preflight(home=None, applications=None, process_probe=None):
    home = pathlib.Path.home() if home is None else pathlib.Path(home)
    applications = pathlib.Path("/Applications") if applications is None else pathlib.Path(applications)
    plan_id = uuid.uuid4().hex
    inventory = build_manifest(home, applications, "claude")
    processes = (process_probe or (lambda: collect_processes(home)))()
    rows = {row[2]: row for row in definitions(home, applications)}
    candidates = []
    for item in inventory["items"]:
        if item["policy"] != "candidate" or item["observation"]["state"] != "present":
            continue
        path, anchor, *_ = rows[item["path"]]
        check = inspect_tree(path, anchor)
        candidates.append({"id": item["id"], "path": item["path"], "impact": item["impact"],
                           "proposed_action": "backup_verify_then_remove_cache", "selected": False,
                           "path_preflight": check})
    estimated = sum(item["path_preflight"].get("estimated_file_bytes", 0) for item in candidates)
    backup = backup_preflight(home, plan_id, estimated,
                              estimate_complete=all(i["path_preflight"]["state"] == "checked" for i in candidates))
    blockers = []
    if processes.get("complete") is not True:
        blockers.append("process_checks_incomplete")
    if processes.get("running"):
        blockers.append("relevant_processes_or_shared_state_users_active")
    if inventory["completeness"] == "incomplete" or any(i["path_preflight"]["state"] != "checked" for i in candidates):
        blockers.append("path_checks_incomplete")
    if backup["state"] == "blocked":
        blockers.append("backup_location_preflight_blocked")
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        blockers.append("custom_Claude_config_directory_requires_separate_scope")
    return {"schema_version": 1, "plan_id": plan_id, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mode": "production_read_only_preflight", "scope": "claude", "executable": False,
            "status": "blocked_pending_review" if blockers else "review_required",
            "blockers": blockers, "processes": processes, "candidates": candidates,
            "protected_items": [{"id": i["id"], "path": i["path"], "reason": i["protection_reason"]}
                                for i in inventory["items"] if i["policy"] == "protected"],
            "backup_plan": backup,
            "limitations": ["只读采样，未停止进程、写入备份、修改配置或删除数据。",
                            "未读取文件正文；元数据摘要不能代替执行前内容快照。",
                            "只覆盖固定 Claude 路径及当前用户可见进程；不保证识别所有关闭文件的未知包装器。",
                            "进程与空间状态可变化，任何未来执行必须重新预检并获得准确项目授权。",
                            "本报告不可执行，也不能交给临时目录执行器；真实执行只有 trash_cleanup.py，它会重新采样。"]}


def render_markdown(plan):
    lines = ["# Claude 清理只读预检与备份方案", "", f"状态：`{plan['status']}`；可执行：否；所有候选项均未选中。", "",
             "阻塞项：" + ("、".join(plan["blockers"]) or "未发现已测范围内的阻塞，仍须审阅。"), "",
             "进程采集完整：" + str(plan["processes"]["complete"]),
             "相关进程/共享数据使用者：" + ("、".join(plan["processes"]["running"]) or "本次未检测到"), "",
             "| 项目 ID | 路径 | 元数据预检 | 估算字节 |", "|---|---|---|---:|"]
    for item in plan["candidates"]:
        check = item["path_preflight"]
        lines.append(f"| {item['id']} | {item['path']} | {check['state']} | {check.get('estimated_file_bytes', '未知')} |")
    lines.extend(["", "备份拟放置：`" + plan["backup_plan"]["destination"] + "`，尚未创建或验证。", "",
                  "备份总容量估算：" + (str(plan["backup_plan"]["estimated_payload_bytes"]) + " 字节"
                    if plan["backup_plan"]["payload_estimate_complete"] else "未完成；已扫描部分大小不能代表全部容量。"), "",
                  "候选项影响："])
    lines.extend("- " + item["path"] + "：" + item["impact"] for item in plan["candidates"])
    lines.extend(["", "保留项："])
    lines.extend("- " + item["path"] + "：" + item["reason"] for item in plan["protected_items"])
    lines.extend(["", "验证及范围限制："])
    lines.extend("- " + text for text in plan["limitations"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args(argv)
    plan = build_preflight()
    print(json.dumps(plan, ensure_ascii=False, indent=2) if args.format == "json" else render_markdown(plan))
    return 2 if plan["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
