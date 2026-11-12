"""Read-only cleanup review inventory. No removal or config-writing capability."""
from __future__ import annotations

import hashlib
import pathlib
import stat
from datetime import datetime, timezone


def definitions(home, applications, scope="claude"):
    """Fixed targets only; shared assets are never offered as cleanup candidates."""
    rows = []

    def add(relative, category, owner, policy, impact, protection="", external=False):
        path = home / relative
        rows.append((path, home, "~/" + relative, category, owner, policy, impact, protection, external))

    for name in ("cache", "stats-cache.json", "telemetry", "usage-data", "paste-cache"):
        add(".claude/" + name, "cache", "Claude Code", "candidate",
            "移除本地缓存或诊断数据；可能丢失本地统计，后续运行可能重建。")
    for relative in ("Library/Caches/claude-cli-nodejs", "Library/Caches/com.anthropic.claudefordesktop",
                     "Library/Caches/com.anthropic.claudefordesktop.ShipIt",
                     "Library/Application Support/Claude/Cache", "Library/Application Support/Claude/Code Cache",
                     "Library/Application Support/Claude/GPUCache", "Library/Logs/Claude"):
        add(relative, "cache", "Claude", "candidate", "移除缓存或日志；日志不一定可恢复，操作前须备份。")
    for name in ("projects", "sessions", "history.jsonl", "file-history"):
        add(".claude/" + name, "shared_history", "Claude / Teamo shared state", "protected",
            "删除会造成共享会话或历史丢失。", "保留共享会话与历史，不因卸载官方 Claude 而移除。")
    for name in ("skills", "plugins", "hooks", "commands"):
        add(".claude/" + name, "user_asset", "User", "protected",
            "删除会损失个人扩展或工作流。", "个人技能、插件、hooks 和 commands 不属于清理目标。")
    add(".claude", "shared_root", "Claude / Teamo shared state", "protected",
        "整体移除会覆盖共享会话、技能与配置。", "禁止把共享根目录整体列为候选。")
    add(".claude.json", "shared_config", "Claude / Teamo shared state", "protected",
        "整体删除可能损失共享设置、本地项目索引或 MCP 配置。",
        "共享配置默认保留；若未来清理登录字段，须单独审阅字段级变更。")
    for name in ("settings.json", "settings.local.json", "settings.bailian.json"):
        add(".claude/" + name, "config", "Claude / user routes", "review",
            "更改可能影响路由、权限、隐私控制或个人设置。",
            "存在配置不代表残留；保留有意配置，只允许另行审阅后的字段级修改。")
    add(".claude/.credentials.json", "auth", "Claude Code", "review",
        "移除可能退出登录，后续需重新认证。", "凭据仅检查元数据，不读取或输出内容；须明确登录重置范围。")
    add(".claude-code-now-last-dir", "runtime_state", "Claude / shared runtime", "review",
        "移除会重置最近目录记录。", "状态文件存在本身不能证明官方 Claude 已安装。")
    for relative in ("Library/Application Support/Claude", "Library/Application Support/com.anthropic.claudefordesktop",
                     "Library/HTTPStorages/com.anthropic.claudefordesktop",
                     "Library/Preferences/com.anthropic.claudefordesktop.plist",
                     "Library/Saved Application State/com.anthropic.claudefordesktop.savedState"):
        add(relative, "desktop_data", "Claude Desktop", "review",
            "整体移除可能退出登录并丢失本地状态或设置。",
            "需要明确卸载或重置授权；父目录审阅不涵盖受保护资产或自动选择子项。")
    for relative in (".local/bin/claude", ".npm-global/bin/claude",
                     "Applications/Chrome Apps.localized/Claude.app", "Applications/Claude Code URL Handler.app"):
        add(relative, "entrypoint", "Unverified Claude entrypoint", "review",
            "移除可能影响 CLI、PWA 或深链接入口。", "名称不足以确认归属；须核验官方安装方式及 Teamo 依赖。")
    rows.append((applications / "Claude.app", applications, "/Applications/Claude.app", "application",
                 "Claude Desktop", "review", "卸载桌面应用，可能中断当前工作。",
                 "程序本体卸载需明确授权，不能从清缓存推断。", False))
    for relative in (".teamo", ".claude-to-im", "code/Claude-to-IM-skill",
                     "Library/LaunchAgents/com.claude-to-im.bridge.plist"):
        add(relative, "preserved_integration", "Teamo / Claude-to-IM", "protected",
            "移除可能破坏 Teamo 或 Codex 的 IM 接入。",
            "默认保留；不将名字中的 Claude 视为官方 Claude 残留，不读取其数据。", True)
    for relative in (".claude/backups", "ClaudeBackups"):
        add(relative, "backup", "User", "protected", "删除会丢失恢复副本。", "本轮不删除既有备份。")
    if scope == "all":
        for relative in (".codex/config.toml", ".cc-switch/settings.json", ".cc-switch/cc-switch.db",
                         ".claude-code-router/config.json", ".cursor/mcp.json", ".gemini/settings.json",
                         ".kiro/settings/cli.json", ".claude-sync/config.json"):
            add(relative, "cross_tool_config", "Other tools / shared routes", "review",
                "修改可能影响其他工具或共享路由。", "跨工具配置仅供审阅；检测到路径不构成删除依据。")
    return rows


def metadata(path, anchor):
    """Check every component without following symlinks, including symlinked parents."""
    relative = path.relative_to(anchor)
    current = anchor
    for part in (None, *relative.parts):
        if part is not None:
            current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return {"state": "not_found", "object_type": None, "file_bytes": None}
        except OSError as exc:
            return {"state": "error", "reason": type(exc).__name__, "object_type": None, "file_bytes": None}
        if stat.S_ISLNK(info.st_mode):
            return {"state": "blocked_symlink", "object_type": "symlink", "file_bytes": None}
    kind = "directory" if stat.S_ISDIR(info.st_mode) else "file" if stat.S_ISREG(info.st_mode) else "other"
    return {"state": "present", "object_type": kind,
            "file_bytes": info.st_size if kind == "file" else None,
            "identity": {"dev": info.st_dev, "ino": info.st_ino, "uid": info.st_uid,
                         "mode": info.st_mode, "size": info.st_size,
                         "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns}}


def build_manifest(home=None, applications=None, scope="claude"):
    if scope not in {"claude", "all"}:
        raise ValueError("unsupported scope")
    home = pathlib.Path.home() if home is None else pathlib.Path(home)
    applications = pathlib.Path("/Applications") if applications is None else pathlib.Path(applications)
    items = []
    for path, anchor, display, category, owner, policy, impact, protection, external in definitions(home, applications, scope):
        observed = {"state": "not_checked", "object_type": None, "file_bytes": None} if external else metadata(path, anchor)
        state = observed["state"]
        disposition = "protected" if policy == "protected" else "not_found" if state == "not_found" else (
            "review" if state in {"blocked_symlink", "error"} else policy)
        items.append({"id": hashlib.sha256(display.encode()).hexdigest()[:16], "path": display,
                      "category": category, "owner": owner, "policy": policy,
                      "disposition": disposition, "observation": observed, "impact": impact,
                      "protection_reason": protection, "selected": False,
                      "proposed_action": "preserve" if policy == "protected" else "review_only",
                      "evidence": "policy_only" if external else "fixed_path_metadata_only"})
    return {"schema_version": 2, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "scope": scope, "mode": "read_only_review", "executable": False,
            "completeness": "incomplete" if any(i["observation"]["state"] in {"error", "blocked_symlink"} for i in items) else "complete_within_inventory_scope",
            "limitations": ["仅固定路径元数据，不读取凭据、配置或会话正文，不递归统计目录。",
                            "未核验进程、包管理器、登录有效性、网络或自定义 CLAUDE_CONFIG_DIR。",
                            "候选项不等于授权；不存在、未检查和受保护项都不会被选择。",
                            "identity 仅为路径元数据；执行准备仍须生成内容快照并重新审阅。"],
            "items": items}


def render_text(manifest):
    print("# Claude 清理审阅清单")
    print(f"范围：{manifest['scope']}；只读；可执行：否；检查完整性：{manifest['completeness']}")
    for item in manifest["items"]:
        print(f"\n- {item['id']} | {item['path']}")
        print(f"  类别：{item['category']}；判定：{item['disposition']}；检测：{item['observation']['state']}；未选中")
        print(f"  影响：{item['impact']}")
        if item["protection_reason"]:
            print(f"  保护/审阅原因：{item['protection_reason']}")
    for limitation in manifest["limitations"]:
        print(f"\n限制：{limitation}")
