#!/usr/bin/env python3
"""Simple, standalone macOS launcher for Claude environment audit and cleanup.

The default action is always read-only. Cleanup never permanently deletes data:
matched items are moved into a timestamped recovery folder under the user's HOME.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Iterable


APP_DIR = Path(__file__).resolve().parent
AUDIT_ENV = APP_DIR / "scripts" / "audit_claude_env.py"
AUDIT_NETWORK = APP_DIR / "scripts" / "audit_network_env.py"


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def display_path(path: Path, home: Path) -> str:
    try:
        return "~/" + str(path.relative_to(home))
    except ValueError:
        return str(path)


def report_dir(home: Path) -> Path:
    return home / "Documents" / "Claude环境清理报告"


def backup_root(home: Path) -> Path:
    return home / "Backups" / "claude-env-cleanup"


def new_backup_dir(home: Path, mode: str) -> Path:
    base = backup_root(home) / f"{mode}-{now_stamp()}"
    candidate = base
    index = 2
    while candidate.exists():
        candidate = base.with_name(f"{base.name}-{index}")
        index += 1
    return candidate


def safe_targets(home: Path) -> list[Path]:
    library = home / "Library"
    return [
        library / "Caches" / "com.anthropic.claudefordesktop",
        library / "Caches" / "com.anthropic.claudefordesktop.ShipIt",
        library / "Caches" / "claude-cli-nodejs",
        library / "Caches" / "CC Switch",
        library / "Caches" / "cc-switch",
        library / "Logs" / "Claude",
        library / "Logs" / "CC Switch",
        library / "Logs" / "cc-switch",
        home / ".claude" / "cache",
        home / ".claude" / "debug",
        home / ".claude" / "logs",
        home / ".claude" / "telemetry",
    ]


def deep_targets(home: Path, applications_root: Path = Path("/Applications")) -> list[Path]:
    library = home / "Library"
    targets = safe_targets(home) + [
        applications_root / "Claude.app",
        applications_root / "CC Switch.app",
        home / "Applications" / "Chrome Apps.localized" / "Claude.app",
        home / "Applications" / "Claude Code URL Handler.app",
        home / ".cc-switch",
        home / ".claude.json",
        home / ".claude-code-now-last-dir",
        home / ".claude" / ".credentials.json",
        library / "Application Support" / "Claude",
        library / "Application Support" / "com.anthropic.claudefordesktop",
        library / "Application Support" / "CC Switch",
        library / "Application Support" / "cc-switch",
        library / "HTTPStorages" / "com.anthropic.claudefordesktop",
        library / "Preferences" / "com.anthropic.claudefordesktop.plist",
        library / "Preferences" / "com.cc-switch.plist",
        library / "Preferences" / "com.ccswitch.plist",
        library / "Saved Application State" / "com.anthropic.claudefordesktop.savedState",
    ]

    for root in browser_roots(home):
        for name in (
            "com.anthropic.claude_browser_extension.json",
            "com.anthropic.claude_code_browser_extension.json",
        ):
            targets.extend(root.glob(f"NativeMessagingHosts/{name}"))
            targets.extend(root.glob(f"*/NativeMessagingHosts/{name}"))

    launch_agents = library / "LaunchAgents"
    if launch_agents.exists():
        for item in launch_agents.glob("*.plist"):
            if any(word in item.name.lower() for word in ("anthropic", "claude", "cc-switch", "ccswitch")):
                targets.append(item)

    by_host = library / "Preferences" / "ByHost"
    targets.extend(by_host.glob("com.anthropic.claudefordesktop*.plist"))
    return unique_paths(targets)


def browser_roots(home: Path) -> list[Path]:
    support = home / "Library" / "Application Support"
    return [
        support / "Arc" / "User Data",
        support / "BraveSoftware" / "Brave-Browser",
        support / "Chromium",
        support / "Google" / "Chrome",
        support / "Microsoft Edge",
        support / "Vivaldi",
        support / "com.operasoftware.Opera",
    ]


def unique_paths(paths: Iterable[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            result.append(path)
            seen.add(key)
    return result


def existing_targets(paths: Iterable[Path]) -> list[Path]:
    return [path for path in unique_paths(paths) if path.exists() or path.is_symlink()]


def run_audit(script: Path, env: dict[str, str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            [sys.executable, str(script)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=120,
            env=env,
        )
        return completed.returncode, completed.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 1, "检查未完成，请稍后重试。\n"


def one_click_check(home: Path, quiet: bool = False) -> int:
    if not quiet:
        print("\n正在做只读检查，不会删除或修改 Claude 配置……")
    env = os.environ.copy()
    env["HOME"] = str(home)
    env_code, env_output = run_audit(AUDIT_ENV, env)
    net_code, net_output = run_audit(AUDIT_NETWORK, env)

    destination = report_dir(home)
    destination.mkdir(parents=True, exist_ok=True)
    report = destination / "last-report.txt"
    report.write_text(
        "Claude 环境只读检查报告\n"
        + f"时间：{datetime.now().isoformat(timespec='seconds')}\n"
        + "说明：本次检查没有删除或修改任何 Claude 或浏览器配置，只生成了本报告。\n\n"
        + "========== 本机环境 ==========\n"
        + env_output
        + "\n========== 网络环境（本地只读） ==========\n"
        + net_output,
        encoding="utf-8",
    )
    if not quiet:
        if env_code == 0 and net_code == 0:
            print("✓ 检查完成。本次没有删除或修改 Claude 配置。")
        else:
            print("检查已完成，但有一部分未能读取。")
        print(f"报告保存在：{display_path(report, home)}")
    return 0 if env_code == 0 and net_code == 0 else 1


def destination_for(source: Path, backup: Path, home: Path) -> Path:
    try:
        relative = source.relative_to(home)
        destination = backup / "HOME" / relative
    except ValueError:
        destination = backup / "SYSTEM" / str(source).lstrip("/")
    if not destination.exists():
        return destination
    index = 2
    while destination.with_name(f"{destination.name}-{index}").exists():
        index += 1
    return destination.with_name(f"{destination.name}-{index}")


def show_targets(targets: list[Path], home: Path) -> None:
    print("\n将处理以下内容：")
    if not targets:
        print("  （没有找到需要处理的内容）")
        return
    for path in targets:
        print(f"  • {display_path(path, home)}")
    print("\n所有内容都会移到可恢复的备份文件夹，不会永久删除。")
    print("浏览器 Cookie、网站数据、整个浏览器档案和其他工具不会被处理。")


def confirmed_twice(label: str, input_fn=None) -> bool:
    if input_fn is None:
        input_fn = input
    first = input_fn("\n第一次确认：是否继续？输入 y 继续，其他键取消：").strip().lower()
    if first != "y":
        print("已取消，没有修改任何内容。")
        return False
    phrase = f"确认{label}"
    second = input_fn(f'第二次确认：请完整输入“{phrase}”：').strip()
    if second != phrase:
        print("已取消，没有修改任何内容。")
        return False
    return True


def move_to_backup(targets: list[Path], home: Path, mode: str, dry_run: bool = False) -> int:
    backup = new_backup_dir(home, mode)
    manifest: list[dict[str, str]] = []
    failures: list[str] = []
    if not dry_run:
        backup.mkdir(parents=True, exist_ok=False)

    for source in targets:
        destination = destination_for(source, backup, home)
        if dry_run:
            manifest.append({"source": str(source), "backup": str(destination), "status": "dry-run"})
            continue
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            manifest.append({"source": str(source), "backup": str(destination), "status": "moved"})
        except (OSError, shutil.Error):
            failures.append(display_path(source, home))
            manifest.append({"source": str(source), "backup": str(destination), "status": "failed"})

    if dry_run:
        print("\nDry-run 完成：仅列出计划，没有创建备份，也没有移动文件。")
        return 0

    (backup / "manifest.json").write_text(
        json.dumps({"created_at": datetime.now().isoformat(), "mode": mode, "items": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n✓ 处理完成。可恢复备份：{display_path(backup, home)}")
    if failures:
        print("以下内容可能正在使用或需要 Mac 管理员权限，已安全跳过：")
        for item in failures:
            print(f"  • {item}")
    return 0


def clean(home: Path, deep: bool, dry_run: bool = False, applications_root: Path = Path("/Applications")) -> int:
    label = "深度清理" if deep else "安全清理"
    targets = existing_targets(deep_targets(home, applications_root) if deep else safe_targets(home))
    show_targets(targets, home)
    if not targets:
        print("你的 Mac 目前很干净，无需清理。")
        return 0
    if dry_run:
        return move_to_backup(targets, home, "deep" if deep else "safe", dry_run=True)
    if not confirmed_twice(label):
        return 0
    return move_to_backup(targets, home, "deep" if deep else "safe")


def open_report(home: Path) -> int:
    report = report_dir(home) / "last-report.txt"
    if not report.exists():
        print("还没有报告，现在先为你做一次只读检查。")
        one_click_check(home)
    try:
        subprocess.run(["open", str(report)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        print(f"报告位置：{display_path(report, home)}")
    return 0


def menu(home: Path) -> int:
    while True:
        print("\n" + "=" * 34)
        print("  Claude 环境检查与清理")
        print("=" * 34)
        print("  [1] 一键检查（推荐，只读）")
        print("  [2] 安全清理（缓存和日志）")
        print("  [3] 深度清理（会先备份）")
        print("  [4] 查看报告")
        print("  [0] 退出")
        choice = input("\n请选择（直接按回车 = 一键检查）：").strip() or "1"
        if choice == "1":
            one_click_check(home)
        elif choice == "2":
            clean(home, deep=False)
        elif choice == "3":
            clean(home, deep=True)
        elif choice == "4":
            open_report(home)
        elif choice == "0":
            print("已退出。")
            return 0
        else:
            print("请输入 0、1、2、3 或 4。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Claude 环境检查与清理")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="只读检查并生成报告")
    action.add_argument("--safe-clean", action="store_true", help="清理缓存和日志")
    action.add_argument("--deep-clean", action="store_true", help="深度清理")
    parser.add_argument("--dry-run", action="store_true", help="仅列出计划，不做任何修改")
    parser.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
    parser.add_argument("--applications-root", type=Path, default=Path("/Applications"), help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    home = args.home.expanduser().resolve()
    try:
        if args.check:
            return one_click_check(home)
        if args.safe_clean:
            return clean(home, deep=False, dry_run=args.dry_run, applications_root=args.applications_root)
        if args.deep_clean:
            return clean(home, deep=True, dry_run=args.dry_run, applications_root=args.applications_root)
        return menu(home)
    except KeyboardInterrupt:
        print("\n已取消，没有继续操作。")
        return 0
    except Exception:
        print("\n操作没有完成。请重新打开工具再试一次。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
