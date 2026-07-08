#!/usr/bin/env python3
"""Read-only Claude network environment audit with optional external probes."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any


HOME = pathlib.Path.home()

MANUAL_CHECK_URLS = [
    ("Claude-specific IP, DNS, WebRTC, trust score", "https://ip.net.coffee/claude/"),
    ("Claude environment, DNS/WebRTC, Chinese-fingerprint score", "https://ippure.com/claude"),
    ("Independent IP intelligence, geo consistency, score", "https://iplark.com/"),
]

POST_BAN_CHECK_URLS = [
    ("Net.Coffee Claude detector", "https://ip.net.coffee/claude/"),
    ("IPLark IP intelligence", "https://iplark.com/"),
    ("Net.Coffee tool hub", "https://net.coffee/"),
    ("IPPure detector", "https://ippure.com/"),
    ("CC MastersGo Claude detector", "https://cc.mastersgo.cc/"),
]

PUBLIC_IP_ENDPOINTS = [
    ("api.ipify.org", "https://api.ipify.org?format=json", "json"),
    ("ifconfig.co", "https://ifconfig.co/json", "json"),
    ("cloudflare-trace", "https://www.cloudflare.com/cdn-cgi/trace", "trace"),
]

HTTPS_PROBES = [
    ("claude.ai login", "https://claude.ai/login"),
    ("api.anthropic.com", "https://api.anthropic.com/"),
]

DNS_HOSTS = ["claude.ai", "api.anthropic.com", "chat.openai.com"]
WATCH_PORTS = [15721, 7890, 7892, 1080, 8080, 8888, 6152]

BROWSER_ROOTS = [
    ("Google Chrome", HOME / "Library" / "Application Support" / "Google" / "Chrome"),
    ("Chromium", HOME / "Library" / "Application Support" / "Chromium"),
    ("Microsoft Edge", HOME / "Library" / "Application Support" / "Microsoft Edge"),
    (
        "Brave",
        HOME / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser",
    ),
    ("Arc", HOME / "Library" / "Application Support" / "Arc" / "User Data"),
]

LANGUAGE_KEYS = [
    ("intl", "accept_languages"),
    ("intl", "selected_languages"),
    ("intl", "app_locale"),
    ("browser", "app_locale"),
    ("language", "preferred_languages"),
]

SITE_DATA_MARKERS = [
    ("Cookies", pathlib.Path("Cookies")),
    ("Network/Cookies", pathlib.Path("Network") / "Cookies"),
    ("Local Storage", pathlib.Path("Local Storage")),
    ("IndexedDB", pathlib.Path("IndexedDB")),
    ("Service Worker", pathlib.Path("Service Worker")),
]


def print_section(title: str) -> None:
    print(f"\n## {title}")


def run(cmd: list[str], timeout: int = 8) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except Exception as exc:
        return subprocess.CompletedProcess(cmd, 999, "", str(exc))


def sh(command: str, timeout: int = 8) -> subprocess.CompletedProcess[str]:
    return run(["sh", "-lc", command], timeout=timeout)


def sanitize_urlish(value: str) -> str:
    value = value.strip()
    if not value:
        return value
    try:
        parsed = urllib.parse.urlsplit(value)
    except Exception:
        return value[:160]
    if not parsed.scheme or not parsed.netloc:
        return value[:160]
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    user = "***@" if parsed.username or parsed.password else ""
    path = parsed.path or ""
    if len(path) > 40:
        path = path[:37] + "..."
    return urllib.parse.urlunsplit((parsed.scheme, f"{user}{host}{port}", path, "", ""))


def safe_json(path: pathlib.Path) -> Any | None:
    try:
        return json.loads(path.read_text(errors="replace"))
    except Exception:
        return None


def get_nested(obj: Any, path: tuple[str, ...]) -> Any:
    current = obj
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def request_url(url: str, timeout: int) -> tuple[int | None, str, str, float]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 ClaudeEnvCleanupSkill/1.0",
            "Accept": "application/json,text/plain,text/html;q=0.8,*/*;q=0.5",
        },
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(512_000).decode("utf-8", errors="replace")
            elapsed = time.monotonic() - started
            return resp.status, resp.geturl(), body, elapsed
    except urllib.error.HTTPError as exc:
        body = exc.read(128_000).decode("utf-8", errors="replace")
        elapsed = time.monotonic() - started
        return exc.code, exc.geturl(), body, elapsed
    except Exception as exc:
        elapsed = time.monotonic() - started
        return None, url, f"{type(exc).__name__}: {exc}", elapsed


def parse_cloudflare_trace(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"ip", "loc", "colo", "tls", "warp"}:
            result[key] = value
    return result


def public_ip_probes(timeout: int) -> dict[str, Any]:
    print_section("External IP and Claude Reachability")
    print("- external probes enabled; these requests reveal this machine's public IP to the target services")
    collected: dict[str, Any] = {}
    for label, url, kind in PUBLIC_IP_ENDPOINTS:
        status, final_url, body, elapsed = request_url(url, timeout)
        print(f"- {label}: status={status or 'error'} elapsed={elapsed:.2f}s")
        if status is None:
            print(f"  error: {body[:160]}")
            continue
        data: dict[str, Any] = {}
        if kind == "json":
            try:
                data = json.loads(body)
            except Exception:
                data = {}
        elif kind == "trace":
            data = parse_cloudflare_trace(body)
        if data:
            printable = []
            for key in ["ip", "country", "country_name", "region", "city", "org", "asn", "loc", "colo", "warp"]:
                if key in data:
                    printable.append(f"{key}={data[key]}")
                    collected.setdefault(key, data[key])
            print("  " + "; ".join(printable[:10]))
        if final_url != url:
            print(f"  final_url={sanitize_urlish(final_url)}")

    for label, url in HTTPS_PROBES:
        status, final_url, body, elapsed = request_url(url, timeout)
        print(f"- {label}: status={status or 'error'} elapsed={elapsed:.2f}s")
        if status is None:
            print(f"  error: {body[:160]}")
        elif final_url != url:
            print(f"  final_url={sanitize_urlish(final_url)}")
    return collected


def dns_resolution() -> dict[str, list[str]]:
    print_section("DNS Resolution")
    resolved: dict[str, list[str]] = {}
    for host in DNS_HOSTS:
        try:
            infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        except Exception as exc:
            print(f"- {host}: failed ({exc})")
            continue
        ips = sorted({info[4][0] for info in infos})
        resolved[host] = ips
        print(f"- {host}: {', '.join(ips[:8])}")
    return resolved


def local_proxy_env() -> None:
    print_section("Proxy and Route Surfaces")
    names = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ]
    hits = []
    for name in names:
        value = os.environ.get(name)
        if value:
            hits.append(f"{name}={sanitize_urlish(value)}")
    if hits:
        print("- current process proxy env:")
        for hit in hits:
            print(f"  {hit}")
    else:
        print("- current process proxy env: none")

    result = sh("scutil --proxy", timeout=5)
    if result.returncode == 0 and result.stdout.strip():
        interesting = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped or ":" not in stripped:
                continue
            key, value = [part.strip() for part in stripped.split(":", 1)]
            if key in {
                "HTTPEnable",
                "HTTPProxy",
                "HTTPPort",
                "HTTPSEnable",
                "HTTPSProxy",
                "HTTPSPort",
                "SOCKSEnable",
                "SOCKSProxy",
                "SOCKSPort",
                "ProxyAutoConfigEnable",
                "ProxyAutoConfigURLString",
            }:
                if key.endswith("URLString"):
                    value = sanitize_urlish(value)
                interesting.append(f"{key}={value}")
        print("- macOS proxy settings:")
        for item in interesting[:20]:
            print(f"  {item}")
    else:
        print("- macOS proxy settings: unavailable")

    result = sh("route -n get default 2>/dev/null | egrep 'gateway|interface'", timeout=5)
    if result.stdout.strip():
        print("- default route:")
        for line in result.stdout.strip().splitlines():
            print(f"  {line.strip()}")
    else:
        print("- default route: unavailable")


def dns_system_summary() -> None:
    result = sh("scutil --dns", timeout=5)
    if result.returncode != 0 or not result.stdout.strip():
        print("- system DNS resolvers: unavailable")
        return
    nameservers = []
    search_domains = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("nameserver["):
            value = stripped.split(":", 1)[-1].strip()
            if value not in nameservers:
                nameservers.append(value)
        elif stripped.startswith("search domain["):
            value = stripped.split(":", 1)[-1].strip()
            if value not in search_domains:
                search_domains.append(value)
    print("- system DNS nameservers:")
    for item in nameservers[:12]:
        print(f"  {item}")
    if search_domains:
        print("- DNS search domains:")
        for item in search_domains[:8]:
            print(f"  {item}")


def watched_ports() -> list[str]:
    lsof = shutil.which("lsof")
    listeners: list[str] = []
    if not lsof:
        print("- watched proxy ports: lsof not found")
        return listeners
    for port in WATCH_PORTS:
        result = run([lsof, "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"], timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()[1:]
            for line in lines[:6]:
                listeners.append(line)
    if listeners:
        print("- watched proxy-port listeners:")
        for line in listeners[:20]:
            print(f"  {line}")
    else:
        print("- watched proxy-port listeners: none")
    return listeners


def browser_language_summary() -> dict[str, dict[str, Any]]:
    print_section("Browser and System Correlation")
    summary: dict[str, dict[str, Any]] = {}
    for name, root in BROWSER_ROOTS:
        if not root.exists():
            continue
        print(f"- {name}:")
        browser_summary: dict[str, Any] = {}
        for pref_path in sorted(root.glob("*/Preferences")):
            profile = pref_path.parent.name
            obj = safe_json(pref_path)
            if obj is None:
                continue
            values = {}
            profile_name = get_nested(obj, ("profile", "name"))
            if profile_name:
                values["profile.name"] = profile_name
            for key_path in LANGUAGE_KEYS:
                value = get_nested(obj, key_path)
                if value is not None:
                    values[".".join(key_path)] = value
            if values:
                browser_summary[profile] = values
                rendered = "; ".join(f"{key}={json.dumps(value, ensure_ascii=False)}" for key, value in values.items())
                print(f"  {profile}: {rendered}")
        summary[name] = browser_summary
    if not summary:
        print("- Chromium-family browser preferences not found")

    languages = sh("defaults read -g AppleLanguages 2>/dev/null", timeout=5).stdout.strip()
    locale = sh("defaults read -g AppleLocale 2>/dev/null", timeout=5).stdout.strip()
    localtime = ""
    try:
        localtime = os.readlink("/etc/localtime")
    except OSError:
        localtime = ""
    print(f"- AppleLanguages: {languages if languages else 'unavailable'}")
    print(f"- AppleLocale: {locale if locale else 'unavailable'}")
    print(f"- /etc/localtime: {localtime if localtime else 'unavailable'}")
    return summary


def browser_site_data_targets() -> None:
    print_section("Browser Site-Data Cleanup Targets")
    print("- read-only inventory only; cookie databases and storage contents are not opened or printed")
    found = False
    for name, root in BROWSER_ROOTS:
        if not root.exists():
            continue
        for pref_path in sorted(root.glob("*/Preferences")):
            profile = pref_path.parent
            markers = [label for label, rel_path in SITE_DATA_MARKERS if (profile / rel_path).exists()]
            if not markers:
                continue
            found = True
            print(f"- {name}/{profile.name}: {', '.join(markers)}")
    safari_cookie_dir = HOME / "Library" / "Containers" / "com.apple.Safari" / "Data" / "Library" / "Cookies"
    safari_local_storage = HOME / "Library" / "Safari" / "LocalStorage"
    safari_markers = []
    if safari_cookie_dir.exists():
        safari_markers.append(str(safari_cookie_dir))
    if safari_local_storage.exists():
        safari_markers.append(str(safari_local_storage))
    if safari_markers:
        found = True
        print("- Safari:")
        for marker in safari_markers:
            print(f"  {marker}")
    if not found:
        print("- no common browser site-data stores found")
    print("- MANUAL REQUIRED: clear Claude/Anthropic site data from every browser profile used by the banned account")


def post_ban_manual_cleanup_reminders() -> None:
    print_section("Post-Ban Manual Cleanup Reminders")
    print("- MANUAL REQUIRED: clear cookies/site data/cache for claude.ai, anthropic.com, console.anthropic.com, and any Claude login helper domains in every browser profile used")
    print("- MANUAL REQUIRED: remove or disable Claude/Anthropic browser extensions and session-key helper extensions tied to the banned account")
    print("- MANUAL REQUIRED: restart the browser after clearing site data, then re-run the five browser checks")
    print("- DO NOT delete an entire browser profile unless the user explicitly requested full browser-data removal and a backup exists")


def manual_quality_checks(post_ban: bool = False) -> None:
    print_section("Manual Quality Checks")
    if post_ban:
        print("- post-ban mode uses the five sites from the pasted Claude guide")
        print("- net.coffee is a tool hub; use its relevant Claude/DNS/WebRTC tools when it opens as a homepage")
        urls = POST_BAN_CHECK_URLS
    else:
        print("- use these browser checks when judging node cleanliness; do not rely on one site only")
        urls = MANUAL_CHECK_URLS
    for label, url in urls:
        print(f"  {label}: {url}")
    print("- target criteria from the pasted Claude guide:")
    print("  overseas IP, stable country/region, no frequent auto-switching, risk score below 20%, shared users <= 10 when the site reports it")
    print("- also record PWR telemetry fingerprint warnings when a browser check reports them; store only verdict/risk, not raw telemetry payloads")
    print("- ping0.cc can be used as a reference only; do not treat it as the deciding signal")


def load_last_history(path: pathlib.Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        lines = [line for line in path.read_text(errors="replace").splitlines() if line.strip()]
    except Exception:
        return None
    for line in reversed(lines):
        try:
            return json.loads(line)
        except Exception:
            continue
    return None


def compare_history(path: pathlib.Path | None, snapshot: dict[str, Any], append: bool) -> None:
    print_section("Stability History")
    if path is None:
        print("- no history path supplied; pass --history PATH to compare or --append-history PATH to record")
        return
    last = load_last_history(path)
    if last:
        fields = ["ip", "country", "country_name", "region", "city", "org", "asn", "loc"]
        changes = []
        for field in fields:
            old = last.get(field)
            new = snapshot.get(field)
            if old and new and old != new:
                changes.append(f"{field}: {old} -> {new}")
        if changes:
            print("- changes since previous snapshot:")
            for item in changes:
                print(f"  {item}")
        else:
            print("- no public-IP metadata changes detected against previous snapshot")
    else:
        print("- no previous usable snapshot found")

    if append:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n")
        print(f"- appended snapshot: {path}")
    else:
        print("- history not modified")


def build_snapshot(external: dict[str, Any], browser_summary: dict[str, Any], listeners: list[str]) -> dict[str, Any]:
    snapshot = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "timezone": os.environ.get("TZ") or "",
        "browser_languages": browser_summary,
        "proxy_port_listener_count": len(listeners),
    }
    for key in ["ip", "country", "country_name", "region", "city", "org", "asn", "loc", "colo", "warp"]:
        if key in external:
            snapshot[key] = external[key]
    try:
        snapshot["localtime"] = os.readlink("/etc/localtime")
    except OSError:
        pass
    return snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external", action="store_true", help="query public IP services and Claude endpoints")
    parser.add_argument("--post-ban", action="store_true", help="print the post-ban browser cleanup checklist and five-site review list")
    parser.add_argument("--timeout", type=int, default=8, help="network timeout in seconds")
    parser.add_argument("--history", type=pathlib.Path, help="compare against a JSONL history file without writing")
    parser.add_argument("--append-history", type=pathlib.Path, help="append this run to a JSONL history file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("# Claude Network Environment Audit")
    print(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    print("Mode: read-only by default; no secrets or raw browser cookies are printed")
    print_section("Baseline Criteria")
    print("- expected Claude account hygiene: one clean overseas region, stable node, no automatic country switching")
    print("- risk thresholds from pasted guide: prefer all-green checks, risk score below 20%, shared users <= 10 when available")
    if args.post_ban:
        print("- post-ban checklist mode: audit first, then perform browser/app cleanup manually or only after explicit delete requests")

    local_proxy_env()
    dns_system_summary()
    listeners = watched_ports()
    dns_resolution()
    browser_summary = browser_language_summary()

    external: dict[str, Any] = {}
    if args.external:
        external = public_ip_probes(args.timeout)
    else:
        print_section("External IP and Claude Reachability")
        print("- skipped; pass --external to query public IP services and Claude endpoints")

    if args.post_ban:
        browser_site_data_targets()
        post_ban_manual_cleanup_reminders()
    manual_quality_checks(post_ban=args.post_ban)
    history_path = args.append_history or args.history
    snapshot = build_snapshot(external, browser_summary, listeners)
    compare_history(history_path, snapshot, append=bool(args.append_history))
    return 0


if __name__ == "__main__":
    sys.exit(main())
