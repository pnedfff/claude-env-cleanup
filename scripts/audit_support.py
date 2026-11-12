"""Shared, read-only audit status and fail-closed output redaction."""
from __future__ import annotations

import subprocess
import urllib.parse


class AuditStatus:
    def __init__(self):
        self.records = []

    def issue(self, check, state="error", reason="unavailable"):
        self.records.append((check, state, reason))

    def check(self, function, *args, **kwargs):
        before = len(self.records)
        try:
            result = function(*args, **kwargs)
        except Exception as exc:
            self.issue(function.__name__, reason=type(exc).__name__)
            result = None
        if len(self.records) == before:
            self.records.append((function.__name__, "checked", ""))
        return result

    def summary(self):
        incomplete = any(state in {"error", "unknown"} for _, state, _ in self.records)
        print("\n## Check Completeness")
        print(f"- status: {'incomplete' if incomplete else 'complete within requested scope'}")
        print("- completeness describes collection, not environment safety")
        for check, state, reason in self.records:
            print(f"  {check}: {state}" + (f" ({reason})" if reason else ""))
        return 2 if incomplete else 0


AUDIT = AuditStatus()


def safe_error(exc):
    """Exception messages can contain credentials, URLs or private paths."""
    return type(exc).__name__


def sanitize_urlish(value):
    if not value.strip():
        return ""
    try:
        parsed = urllib.parse.urlsplit(value.strip())
        if parsed.scheme not in {"http", "https", "socks5", "socks5h"} or not parsed.hostname:
            return "[present; invalid or non-URL value redacted]"
        port = parsed.port
        host = parsed.hostname
        if ":" in host:
            host = f"[{host}]"
        # Paths, query strings and fragments can all contain subscription tokens.
        return f"{parsed.scheme}://{host}" + (f":{port}" if port else "")
    except (ValueError, TypeError):
        return "[present; invalid URL redacted]"


def run_command(cmd, timeout=8, **kwargs):
    try:
        result = subprocess.run(cmd, timeout=timeout, **kwargs)
    except Exception as exc:
        AUDIT.issue("command", reason=safe_error(exc))
        return subprocess.CompletedProcess(cmd, 999, "", safe_error(exc))
    # lsof/which use 1 for a valid negative lookup; other failures are unknown.
    negative_lookup = result.returncode == 1 and not result.stderr.strip() and (
        "lsof" in str(cmd[0]) or (len(cmd) > 2 and "which -a " in cmd[-1])
    )
    if result.returncode != 0 and not negative_lookup:
        AUDIT.issue("command", reason=f"exit={result.returncode}")
        return subprocess.CompletedProcess(cmd, result.returncode, "", "command failed (details redacted)")
    return result
