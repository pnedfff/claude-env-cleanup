#!/usr/bin/env python3
"""Read-only Claude/coding-agent route audit with secret-safe output."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from typing import Any, Iterable


HOME = pathlib.Path.home()

FILES = [
    HOME / ".claude" / "settings.json",
    HOME / ".claude" / "settings.bailian.json",
    HOME / ".claude.json",
    HOME / ".codex" / "config.toml",
    HOME / ".cc-switch" / "settings.json",
    HOME / ".cc-switch" / "cc-switch.db",
]

CODING_AGENT_CONFIGS = [
    HOME / ".claude" / "settings.json",
    HOME / ".claude" / "settings.local.json",
    HOME / ".claude.json",
    HOME / ".codex" / "config.toml",
    HOME / ".teamo" / "settings.json",
    HOME / ".cc-switch" / "settings.json",
    HOME / ".claude-code-router" / "config.json",
    HOME / ".cursor" / "mcp.json",
    HOME / ".gemini" / "settings.json",
    HOME / ".gemini" / "config" / "mcp_config.json",
    HOME / ".gemini" / "antigravity" / "mcp_config.json",
    HOME / ".kiro" / "settings" / "cli.json",
    HOME / ".openclaw-lan-u1" / "openclaw.json",
    HOME / ".openclaw-lan-u2" / "openclaw.json",
    HOME / ".openclaw-lan-u3" / "openclaw.json",
    HOME / ".claude-sync" / "config.json",
]

APP_PATHS = [
    pathlib.Path("/Applications/Claude.app"),
    HOME / "Applications" / "Chrome Apps.localized" / "Claude.app",
    HOME / "Applications" / "Claude Code URL Handler.app",
    HOME / "Library" / "Application Support" / "Claude",
    HOME / "Library" / "Application Support" / "com.anthropic.claudefordesktop",
    HOME / "Library" / "Caches" / "com.anthropic.claudefordesktop",
    HOME / "Library" / "Caches" / "com.anthropic.claudefordesktop.ShipIt",
    HOME / "Library" / "Caches" / "claude-cli-nodejs",
    HOME / "Library" / "HTTPStorages" / "com.anthropic.claudefordesktop",
    HOME / "Library" / "Preferences" / "com.anthropic.claudefordesktop.plist",
    HOME
    / "Library"
    / "Saved Application State"
    / "com.anthropic.claudefordesktop.savedState",
    HOME / "Library" / "Logs" / "Claude",
]

CLI_PATHS = [
    HOME / ".local" / "bin" / "claude",
    HOME / ".npm-global" / "bin" / "claude",
    pathlib.Path("/opt/homebrew/bin/claude"),
    pathlib.Path("/usr/local/bin/claude"),
]

STATE_PATHS = [
    HOME / ".claude",
    HOME / ".claude.json",
    HOME / ".claude-code-now-last-dir",
]

APP_GLOBS = [
    HOME / "Library" / "Preferences" / "ByHost" / "com.anthropic.claudefordesktop*.plist",
]

NATIVE_HOST_NAMES = [
    "com.anthropic.claude_browser_extension.json",
    "com.anthropic.claude_code_browser_extension.json",
]

NATIVE_HOST_ROOTS = [
    HOME / "Library" / "Application Support" / "Arc" / "User Data",
    HOME / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser",
    HOME / "Library" / "Application Support" / "Chromium",
    HOME / "Library" / "Application Support" / "Google" / "Chrome",
    HOME / "Library" / "Application Support" / "Microsoft Edge",
    HOME / "Library" / "Application Support" / "Vivaldi",
    HOME / "Library" / "Application Support" / "com.operasoftware.Opera",
]

CLAUDE_CHROME_EXTENSION_IDS = [
    "fcoeoabgfenejglbffodgkkbkcdhcgfn",
    "dihbgbndebgnbjfmelmegjepbnkhlgni",
    "dngcpimnedloihjnnfngkgjoidhnaolf",
]

TEAMO_PATHS = [
    pathlib.Path("/opt/homebrew/bin/teamo"),
    pathlib.Path("/usr/local/bin/teamo"),
    HOME / ".teamo",
    HOME / ".claude" / "projects",
]

CC_SWITCH_PATHS = [
    pathlib.Path("/Applications/CC Switch.app"),
    HOME / ".cc-switch",
    HOME / "Library" / "Application Support" / "CC Switch",
    HOME / "Library" / "Application Support" / "cc-switch",
    HOME / "Library" / "Caches" / "CC Switch",
    HOME / "Library" / "Caches" / "cc-switch",
    HOME / "Library" / "Logs" / "CC Switch",
    HOME / "Library" / "Logs" / "cc-switch",
    HOME / "Library" / "Preferences" / "com.cc-switch.plist",
    HOME / "Library" / "Preferences" / "com.ccswitch.plist",
]

USER_FONT_NAMES = [
    "ZCOOLKuaiLe-Regular.ttf",
    "ZCOOLQingKeHuangYou-Regular.ttf",
]

SYSTEM_FONT_HINTS = [
    pathlib.Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
    pathlib.Path("/System/Library/Fonts/STHeiti Light.ttc"),
    pathlib.Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    pathlib.Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
    pathlib.Path(
        "/System/Library/PrivateFrameworks/FontServices.framework/Resources/Reserved/PingFangUI.ttc"
    ),
]

SENSITIVE_KEYS = {
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_MODEL_NAME",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "apiKey",
    "api_key",
    "authToken",
    "auth_token",
    "refreshToken",
    "refresh_token",
    "accessToken",
    "access_token",
    "oauthAccount",
}

CORE_PRIVACY_CONTROL_KEYS = [
    "DISABLE_TELEMETRY",
    "DISABLE_ERROR_REPORTING",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
    "DISABLE_FEEDBACK_COMMAND",
    "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY",
    "DO_NOT_TRACK",
]

PRIVACY_CONTROL_KEYS = set(CORE_PRIVACY_CONTROL_KEYS)

PRIVACY_OVERRIDE_KEYS = {
    "CLAUDE_CODE_ENABLE_FEEDBACK_SURVEY_FOR_OTEL",
}

PRIVACY_SETTING_KEYS = {
    "skipWebFetchPreflight",
    "feedbackSurveyRate",
}

MARKERS = [
    "127.0.0.1:15721",
    "localhost:15721",
    "PROXY_MANAGED",
    "302ai-claude-code",
    "claude-official",
    "api.302.ai",
    "glm-5.2",
    "proxy_live_backup",
    "claude-code-router",
    "openrouter",
    "anyrouter",
    "api.deepseek.com",
    "open.bigmodel.cn",
    "teamocode.com",
    "code.newcli.com",
    "bypassPermissions",
    "skipDangerousModePermissionPrompt",
    "dangerouslyAllowHostHeaderOriginFallback",
    "ANTHROPIC_BASE_URL",
    "OPENAI_BASE_URL",
]

SQLITE_CONFIG_TABLES = {
    "mcp_servers",
    "provider_endpoints",
    "providers",
    "proxy_config",
    "proxy_live_backup",
    "settings",
}

ROUTE_KEYS = {
    "ANTHROPIC_BASE_URL",
    "OPENAI_BASE_URL",
    "base_url",
    "baseUrl",
    "api_base_url",
    "endpoint",
    "url",
    "PROXY_URL",
    "HOST",
    "PORT",
}

PERMISSION_KEYS = {
    "defaultMode",
    "skipDangerousModePermissionPrompt",
    "dangerouslyAllowHostHeaderOriginFallback",
}


def rel(path: pathlib.Path) -> str:
    try:
        return "~/" + str(path.relative_to(HOME))
    except ValueError:
        return str(path)


def print_section(title: str) -> None:
    print(f"\n## {title}")


def iter_json_paths(obj: Any, prefix: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f"{prefix}.{key}"
            yield child, value
            yield from iter_json_paths(value, child)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            child = f"{prefix}[{index}]"
            yield child, value
            yield from iter_json_paths(value, child)


def scan_text_file(path: pathlib.Path) -> None:
    text = path.read_text(errors="replace")
    hits = [marker for marker in MARKERS if marker in text]
    key_hits = [key for key in SENSITIVE_KEYS if key in text]
    privacy_hits = [key for key in [*PRIVACY_CONTROL_KEYS, *PRIVACY_OVERRIDE_KEYS] if key in text]
    if key_hits:
        print(f"- {rel(path)} sensitive-key names present: {', '.join(sorted(key_hits))}")
    if privacy_hits:
        print(f"- {rel(path)} privacy-control names present: {', '.join(sorted(privacy_hits))}")
    if hits:
        print(f"- {rel(path)} route markers present: {', '.join(sorted(hits))}")
    if not key_hits and not privacy_hits and not hits:
        print(f"- {rel(path)} no configured key names, privacy controls, or known route markers found")


def scan_json_file(path: pathlib.Path) -> None:
    try:
        obj = json.loads(path.read_text(errors="replace"))
    except Exception as exc:
        print(f"- {rel(path)} JSON parse failed: {exc}")
        scan_text_file(path)
        return

    key_paths: list[str] = []
    privacy_paths: list[str] = []
    marker_hits: dict[str, list[str]] = {marker: [] for marker in MARKERS}

    for json_path, value in iter_json_paths(obj):
        key = json_path.split(".")[-1].split("[")[0]
        if key in SENSITIVE_KEYS:
            key_paths.append(json_path)
        if key in PRIVACY_CONTROL_KEYS or key in PRIVACY_OVERRIDE_KEYS or key in PRIVACY_SETTING_KEYS:
            privacy_paths.append(json_path)
        if isinstance(value, str):
            for marker in MARKERS:
                if marker in value:
                    marker_hits[marker].append(json_path)

    if key_paths:
        print(f"- {rel(path)} sensitive-key paths present: {', '.join(sorted(key_paths)[:30])}")
    else:
        print(f"- {rel(path)} no sensitive-key paths found")

    if privacy_paths:
        print(f"- {rel(path)} privacy-control paths present: {', '.join(sorted(privacy_paths)[:30])}")

    for marker, paths in marker_hits.items():
        if paths:
            print(f"  marker {marker!r} at: {', '.join(paths[:20])}")


def scan_json_config_summary(path: pathlib.Path) -> None:
    try:
        obj = json.loads(path.read_text(errors="replace"))
    except Exception:
        scan_text_file(path)
        return

    route_paths: list[str] = []
    permission_paths: list[str] = []
    marker_hits: dict[str, list[str]] = {marker: [] for marker in MARKERS}
    sensitive_paths: list[str] = []
    privacy_paths: list[str] = []

    for json_path, value in iter_json_paths(obj):
        key = json_path.split(".")[-1].split("[")[0]
        if key in ROUTE_KEYS:
            route_paths.append(json_path)
        if key == "defaultMode" and value == "bypassPermissions":
            permission_paths.append(f"{json_path}={value!r}")
        elif key == "skipDangerousModePermissionPrompt" and value is True:
            permission_paths.append(f"{json_path}={value!r}")
        elif key == "dangerouslyAllowHostHeaderOriginFallback" and value is True:
            permission_paths.append(f"{json_path}={value!r}")
        if key in SENSITIVE_KEYS:
            sensitive_paths.append(json_path)
        if key in PRIVACY_CONTROL_KEYS or key in PRIVACY_OVERRIDE_KEYS or key in PRIVACY_SETTING_KEYS:
            privacy_paths.append(json_path)
        if isinstance(value, str):
            for marker in MARKERS:
                if marker in value:
                    marker_hits[marker].append(json_path)

    if route_paths:
        print(f"- {rel(path)} route-related keys: {', '.join(route_paths[:30])}")
    if permission_paths:
        print(f"- {rel(path)} permission-risk keys: {', '.join(permission_paths[:30])}")
    if sensitive_paths:
        print(f"- {rel(path)} sensitive-key paths present: {', '.join(sensitive_paths[:30])}")
    if privacy_paths:
        print(f"- {rel(path)} privacy-control paths present: {', '.join(privacy_paths[:30])}")
    for marker, paths in marker_hits.items():
        if paths:
            print(f"  marker {marker!r} at: {', '.join(paths[:20])}")
    if (
        not route_paths
        and not permission_paths
        and not sensitive_paths
        and not privacy_paths
        and not any(marker_hits.values())
    ):
        print(f"- {rel(path)} no route, permission-risk, or sensitive-key paths found")


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def scan_sqlite(path: pathlib.Path) -> None:
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except Exception as exc:
        print(f"- {rel(path)} SQLite open failed: {exc}")
        return

    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        config_tables = [table for table in tables if table in SQLITE_CONFIG_TABLES]
        skipped = len(tables) - len(config_tables)
        print(
            f"- {rel(path)} config tables: "
            f"{', '.join(config_tables) if config_tables else '(none)'}"
            + (f" (skipped {skipped} history/cache table(s))" if skipped else "")
        )
        for table in config_tables:
            cols = conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
            text_cols = [row[1] for row in cols]
            for col in text_cols:
                for marker in [
                    *MARKERS,
                    *SENSITIVE_KEYS,
                    *PRIVACY_CONTROL_KEYS,
                    *PRIVACY_OVERRIDE_KEYS,
                ]:
                    try:
                        count = conn.execute(
                            f"SELECT COUNT(*) FROM {quote_ident(table)} "
                            f"WHERE CAST({quote_ident(col)} AS TEXT) LIKE ?",
                            (f"%{marker}%",),
                        ).fetchone()[0]
                    except Exception:
                        continue
                    if count:
                        if marker in SENSITIVE_KEYS:
                            label = "sensitive-key name"
                        elif marker in PRIVACY_CONTROL_KEYS or marker in PRIVACY_OVERRIDE_KEYS:
                            label = "privacy-control name"
                        else:
                            label = "route marker"
                        print(
                            f"  {label} {marker!r}: {count} row(s) in "
                            f"{table}.{col}"
                        )
    finally:
        conn.close()


def scan_files() -> None:
    print_section("Config Files")
    for path in FILES:
        if not path.exists():
            print(f"- {rel(path)} missing")
            continue
        print(f"- {rel(path)} exists ({path.stat().st_size} bytes)")
        if path.suffix == ".json":
            scan_json_file(path)
        elif path.suffix == ".db":
            scan_sqlite(path)
        else:
            scan_text_file(path)


def scan_coding_agent_configs() -> None:
    print_section("Coding Agent Config Chain")
    for path in CODING_AGENT_CONFIGS:
        if not path.exists():
            print(f"- {rel(path)} missing")
            continue
        print(f"- {rel(path)} exists ({path.stat().st_size} bytes)")
        if path.suffix == ".json":
            scan_json_config_summary(path)
        else:
            scan_text_file(path)

    auth_files = [
        HOME / ".codex" / "auth.json",
        HOME / ".teamo" / "auth.json",
        HOME / ".gemini" / "oauth_creds.json",
        HOME / ".openclaw-lan-u1" / "identity" / "device-auth.json",
        HOME / ".openclaw-lan-u2" / "identity" / "device-auth.json",
        HOME / ".openclaw-lan-u3" / "identity" / "device-auth.json",
    ]
    print("- auth-bearing files (presence only):")
    for path in auth_files:
        print(f"  {rel(path)} {'exists' if path.exists() else 'missing'}")


def scan_env() -> None:
    print_section("Current Process Environment")
    names = sorted(name for name in os.environ if name.startswith("ANTHROPIC_"))
    if names:
        print(f"- ANTHROPIC_* names present: {', '.join(names)}")
    else:
        print("- no ANTHROPIC_* names present in this process")


def privacy_value_state(value: Any) -> str:
    if value is True:
        return "enabled"
    if value is False or value is None:
        return "disabled-looking"
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return "enabled"
    if text in {"", "0", "false", "no", "off"}:
        return "disabled-looking"
    return "set"


def scan_privacy_controls() -> None:
    print_section("Official Claude Privacy Controls")
    process_configured = [
        f"{key}={privacy_value_state(os.environ.get(key))}"
        for key in CORE_PRIVACY_CONTROL_KEYS
        if key in os.environ
    ]
    if process_configured:
        print(f"- current process: {', '.join(process_configured)}")
    else:
        print("- current process: no official privacy-control env names present")

    for path in [
        HOME / ".claude" / "settings.json",
        HOME / ".claude" / "settings.local.json",
    ]:
        if not path.exists():
            print(f"- {rel(path)} missing")
            continue
        try:
            obj = json.loads(path.read_text(errors="replace"))
        except Exception as exc:
            print(f"- {rel(path)} JSON parse failed: {exc}")
            continue

        env = obj.get("env")
        if not isinstance(env, dict):
            print(f"- {rel(path)} has no top-level env block")
            continue

        configured = [
            f"{key}={privacy_value_state(env.get(key))}"
            for key in CORE_PRIVACY_CONTROL_KEYS
            if key in env
        ]
        missing = [key for key in CORE_PRIVACY_CONTROL_KEYS if key not in env]
        if configured:
            print(f"- {rel(path)} env privacy controls: {', '.join(configured)}")
        if missing:
            print(f"  missing recommended controls: {', '.join(missing)}")
        if "skipWebFetchPreflight" in obj:
            state = privacy_value_state(obj.get("skipWebFetchPreflight"))
            print(
                "  WebFetch preflight override present: "
                f"skipWebFetchPreflight={state} (separate security tradeoff)"
            )


def scan_port() -> None:
    print_section("Port 15721")
    lsof = shutil.which("lsof")
    if not lsof:
        print("- lsof not found")
        return
    result = subprocess.run(
        [lsof, "-nP", "-iTCP:15721", "-sTCP:LISTEN"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        lines = result.stdout.strip().splitlines()
        print("- listener present:")
        for line in lines[:10]:
            print(f"  {line}")
    else:
        print("- no listener detected")


def scan_cc_switch_artifacts() -> None:
    print_section("CC Switch App and State")
    for path in CC_SWITCH_PATHS:
        print(f"- {rel(path)} {'exists' if path.exists() else 'missing'}")

    brew = shutil.which("brew")
    if brew:
        result = subprocess.run(
            [brew, "list", "--cask"],
            text=True,
            capture_output=True,
            check=False,
        )
        casks = [line.strip() for line in result.stdout.splitlines()]
        state = "installed" if "cc-switch" in casks else "not installed"
        print(f"- Homebrew cask cc-switch: {state}")
    else:
        print("- brew not found")

    result = subprocess.run(
        ["sh", "-lc", "which -a cc-switch ccswitch 2>/dev/null"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout.strip():
        print("- PATH lookup for cc-switch/ccswitch:")
        for line in result.stdout.strip().splitlines()[:20]:
            print(f"  {line}")
    else:
        print("- PATH lookup for cc-switch/ccswitch: not found")

    result = subprocess.run(
        ["ps", "ax", "-o", "pid=,ppid=,comm="],
        text=True,
        capture_output=True,
        check=False,
    )
    matches = [
        line
        for line in result.stdout.splitlines()
        if any(token in line.lower() for token in ["cc switch", "cc-switch", "ccswitch"])
    ]
    if matches:
        print("- CC Switch-like processes:")
        for line in matches[:20]:
            print(f"  {line.strip()}")
    else:
        print("- no CC Switch-like processes found")


def scan_locale_font_signals() -> None:
    print_section("Locale Timezone and Font Signals")
    localtime = pathlib.Path("/etc/localtime")
    if localtime.exists():
        try:
            target = os.readlink(localtime)
        except OSError:
            target = "(not a symlink)"
        print(f"- /etc/localtime -> {target}")
    else:
        print("- /etc/localtime missing")

    result = subprocess.run(
        ["date", "+%Y-%m-%d %H:%M:%S %Z %z"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout.strip():
        print(f"- date: {result.stdout.strip()}")

    user_font_dir = HOME / "Library" / "Fonts"
    if user_font_dir.exists():
        user_fonts = sorted(item for item in user_font_dir.iterdir() if item.is_file())
        print(f"- {rel(user_font_dir)} file count: {len(user_fonts)}")
        for item in user_fonts[:20]:
            print(f"  {item.name}")
        for name in USER_FONT_NAMES:
            print(f"  tracked user font {name}: {'exists' if (user_font_dir / name).exists() else 'missing'}")
    else:
        print(f"- {rel(user_font_dir)} missing")

    global_font_dir = pathlib.Path("/Library/Fonts")
    if global_font_dir.exists():
        global_fonts = sorted(item for item in global_font_dir.iterdir() if item.is_file())
        print(f"- /Library/Fonts file count: {len(global_fonts)}")
    else:
        print("- /Library/Fonts missing")

    print("- macOS system Chinese font hints (do not delete these):")
    for path in SYSTEM_FONT_HINTS:
        print(f"  {path}: {'exists' if path.exists() else 'missing'}")


def scan_official_install() -> None:
    print_section("Official App and CLI Surfaces")
    for path in APP_PATHS:
        print(
            f"- {rel(path)} {'exists' if path.exists() else 'missing'}"
            + (f" ({path.stat().st_size} bytes)" if path.is_file() else "")
        )
    for pattern in APP_GLOBS:
        matches = sorted(pattern.parent.glob(pattern.name))
        if matches:
            print(f"- {rel(pattern)} matched:")
            for item in matches[:20]:
                print(f"  {rel(item)}")
        else:
            print(f"- {rel(pattern)} no matches")

    print("- PATH lookup for claude:")
    result = subprocess.run(
        ["sh", "-lc", "which -a claude"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
    else:
        print("  not found")

    for path in CLI_PATHS:
        print(
            f"- {rel(path)} {'exists' if path.exists() else 'missing'}"
            + (f" ({path.stat().st_size} bytes)" if path.is_file() else "")
        )

    print("- shared Claude state markers (not proof of official install by themselves):")
    for path in STATE_PATHS:
        print(
            f"  {rel(path)} {'exists' if path.exists() else 'missing'}"
            + (f" ({path.stat().st_size} bytes)" if path.is_file() else "")
        )

    npm = shutil.which("npm")
    if npm:
        result = subprocess.run(
            [npm, "list", "-g", "--depth=0"],
            text=True,
            capture_output=True,
            check=False,
        )
        lines = [
            line.strip()
            for line in (result.stdout + "\n" + result.stderr).splitlines()
            if "claude" in line.lower() or "anthropic" in line.lower()
        ]
        if lines:
            print("- global npm Claude/Anthropic packages:")
            for line in lines[:20]:
                print(f"  {line}")
        else:
            print("- no global npm Claude/Anthropic packages reported")
    else:
        print("- npm not found")

    npx_root = HOME / ".npm" / "_npx"
    if npx_root.exists():
        matches = sorted(npx_root.glob("*/node_modules/@anthropic-ai/claude-code"))
        if matches:
            print("- npx cached @anthropic-ai/claude-code packages:")
            for item in matches[:20]:
                print(f"  {rel(item)}")
        else:
            print("- no npx cached @anthropic-ai/claude-code packages found")
    else:
        print(f"- {rel(npx_root)} missing")


def scan_browser_bridge() -> None:
    print_section("Claude Browser Native Messaging")
    native_hosts: list[pathlib.Path] = []
    for root in NATIVE_HOST_ROOTS:
        for name in NATIVE_HOST_NAMES:
            native_hosts.extend(root.glob(f"NativeMessagingHosts/{name}"))
            native_hosts.extend(root.glob(f"*/NativeMessagingHosts/{name}"))

    if native_hosts:
        for path in sorted(set(native_hosts)):
            print(f"- manifest present: {rel(path)}")
            try:
                obj = json.loads(path.read_text(errors="replace"))
            except Exception as exc:
                print(f"  JSON parse failed: {exc}")
                continue
            target = obj.get("path")
            if isinstance(target, str):
                target_path = pathlib.Path(target)
                state = "exists" if target_path.exists() else "missing"
                print(f"  target path: {target} ({state})")
            origins = obj.get("allowed_origins")
            if isinstance(origins, list):
                safe_origins = [str(origin) for origin in origins[:10]]
                print(f"  allowed origins: {', '.join(safe_origins)}")
    else:
        print("- no Anthropic/Claude Native Messaging manifests found")

    print("- Claude Chrome extension IDs:")
    any_extensions = False
    chrome_roots = [root for root in NATIVE_HOST_ROOTS if root.exists()]
    for root in chrome_roots:
        for ext_id in CLAUDE_CHROME_EXTENSION_IDS:
            for ext_root in sorted(root.glob(f"*/Extensions/{ext_id}")):
                any_extensions = True
                print(f"  {ext_id} installed under {rel(ext_root)}")
                versions = sorted(
                    [item for item in ext_root.iterdir() if item.is_dir()],
                    key=lambda item: item.name,
                )
                if versions:
                    manifest = versions[-1] / "manifest.json"
                    if manifest.exists():
                        try:
                            obj = json.loads(manifest.read_text(errors="replace"))
                            print(
                                "    "
                                + ", ".join(
                                    part
                                    for part in [
                                        f"name={obj.get('name')!r}",
                                        f"version={obj.get('version')!r}",
                                        "permissions="
                                        + ",".join(obj.get("permissions", [])[:12])
                                        if isinstance(obj.get("permissions"), list)
                                        else "",
                                        "host_permissions="
                                        + ",".join(obj.get("host_permissions", [])[:6])
                                        if isinstance(obj.get("host_permissions"), list)
                                        else "",
                                    ]
                                    if part
                                )
                            )
                        except Exception as exc:
                            print(f"    manifest parse failed: {exc}")
    if not any_extensions:
        print("  no known Claude Chrome extension IDs found")


def scan_teamo_preservation() -> None:
    print_section("Teamo Preservation Surfaces")
    for path in TEAMO_PATHS:
        print(f"- {rel(path)} {'exists' if path.exists() else 'missing'}")

    result = subprocess.run(
        ["sh", "-lc", "which -a teamo"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        print("- PATH lookup for teamo:")
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
    else:
        print("- PATH lookup for teamo: not found")

    npm = shutil.which("npm")
    if npm:
        result = subprocess.run(
            [npm, "list", "-g", "--depth=0"],
            text=True,
            capture_output=True,
            check=False,
        )
        lines = [
            line.strip()
            for line in (result.stdout + "\n" + result.stderr).splitlines()
            if "teamolab" in line.lower() or "teamo" in line.lower()
        ]
        if lines:
            print("- global npm Teamo packages:")
            for line in lines[:20]:
                print(f"  {line}")
        else:
            print("- no global npm Teamo packages reported")


def scan_launch_agents() -> None:
    print_section("Likely LaunchAgents")
    root = HOME / "Library" / "LaunchAgents"
    if not root.exists():
        print(f"- {rel(root)} missing")
        return
    matches = []
    for item in root.glob("*.plist"):
        name = item.name.lower()
        if any(token in name for token in ["claude", "cc-switch", "anthropic"]):
            matches.append(item)
    if matches:
        for item in matches:
            print(f"- {rel(item)}")
    else:
        print("- no obvious Claude/CC Switch LaunchAgent names found")


def main() -> int:
    print("# Claude and Coding-Agent Environment Audit")
    print(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    print("Mode: read-only; secret values are not printed")
    scan_files()
    scan_coding_agent_configs()
    scan_env()
    scan_privacy_controls()
    scan_port()
    scan_cc_switch_artifacts()
    scan_locale_font_signals()
    scan_official_install()
    scan_browser_bridge()
    scan_teamo_preservation()
    scan_launch_agents()
    return 0


if __name__ == "__main__":
    sys.exit(main())
