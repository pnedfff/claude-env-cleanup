"""Regression fixtures only: no real processes, network, configs or cleanup."""
import contextlib
import io
import json
import pathlib
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

import audit_support as support
import audit_network_env as network
import audit_claude_env as claude


class MinimalAuditTests(unittest.TestCase):
    def setUp(self):
        support.AUDIT.records.clear()
        self.output = io.StringIO()
        self.capture = contextlib.redirect_stdout(self.output)
        self.capture.__enter__()
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()
        self.capture.__exit__(None, None, None)

    def history(self, value):
        path = self.root / "history.jsonl"
        path.write_text(json.dumps(value) + "\n")
        return path

    def test_no_observation_is_unknown(self):
        network.compare_history(self.history({"country": "US", "ip": "203.0.113.10"}), {}, False)
        self.assertIn("stability cannot be determined", self.output.getvalue())
        self.assertNotIn("no public-IP metadata changes", self.output.getvalue())
        self.assertEqual(support.AUDIT.summary(), 2)

    def test_partial_comparison_reports_missing(self):
        network.compare_history(self.history({"country": "US", "asn": "AS123"}), {"country": "US"}, False)
        self.assertIn("match for measured fields only: country", self.output.getvalue())
        self.assertIn("unknown/unmeasured fields: asn", self.output.getvalue())
        self.assertEqual(support.AUDIT.summary(), 2)

    def test_complete_match(self):
        network.compare_history(self.history({"country": "US", "asn": "AS123"}), {"country": "US", "asn": "AS123"}, False)
        self.assertEqual(support.AUDIT.summary(), 0)

    def test_mismatch_is_a_measurement_not_collection_error(self):
        network.compare_history(self.history({"country": "US", "asn": "AS123"}), {"country": "SG", "asn": "AS456"}, False)
        self.assertIn("mismatch country", self.output.getvalue())
        self.assertEqual(support.AUDIT.summary(), 0)

    def test_corrupt_history_marks_incomplete(self):
        path = self.root / "broken.jsonl"
        path.write_text('not-json-secret\n[]\n')
        network.compare_history(path, {}, False)
        self.assertEqual(support.AUDIT.summary(), 2)
        self.assertNotIn("not-json-secret", self.output.getvalue())

    def test_legacy_history_is_not_rewritten(self):
        path = self.history({"country": "US", "asn": "AS123", "ip": "203.0.113.10"})
        original = path.read_bytes()
        network.compare_history(path, {"country": "US", "asn": "AS123"}, False)
        self.assertEqual(path.read_bytes(), original)
        self.assertNotIn("203.0.113.10", self.output.getvalue())

    def test_append_only_sanitized_fields(self):
        path = self.root / "new.jsonl"
        network.compare_history(path, {"country": "US", "asn": "AS123", "ip": "203.0.113.10",
                                      "token": "fixture-secret", "org": "private-provider"}, True)
        saved = json.loads(path.read_text())
        self.assertEqual(saved, {"country": "US", "asn": "AS123"})

    def test_snapshot_removes_profiles_and_payload(self):
        browser = {"Google Chrome": {"Private Profile": {"profile.name": "Kevin fixture",
                    "intl.accept_languages": "en-US,zh-CN", "token": "fixture-secret"}}}
        with patch.object(network.os, "readlink", return_value="/var/db/timezone/zoneinfo/Asia/Singapore"):
            snapshot = network.build_snapshot({"ip": "203.0.113.10", "country": "SG", "asn": 123}, browser, [])
        rendered = json.dumps(snapshot)
        for private in ("203.0.113.10", "Private Profile", "Kevin fixture", "fixture-secret"):
            self.assertNotIn(private, rendered)
        self.assertEqual(snapshot["browser_languages"], {"Google Chrome": ["en-US", "zh-CN"]})
        self.assertEqual(snapshot["localtime"], "Asia/Singapore")

    def test_url_secrets_are_removed(self):
        for value in ["http://user:fixture-secret@proxy.example:8080/token-secret?q=query-secret#fragment-secret",
                      "proxy.example:8080/fixture-secret", "http://proxy.example:bad/fixture-secret",
                      "fixture-secret"]:
            redacted = support.sanitize_urlish(value)
            for secret in ("fixture-secret", "token-secret", "query-secret", "fragment-secret"):
                self.assertNotIn(secret, redacted)
        self.assertEqual(support.sanitize_urlish("socks5://user:pass@proxy.example:1080"), "socks5://proxy.example:1080")

    def test_command_timeout_is_incomplete_and_redacted(self):
        with patch.object(support.subprocess, "run", side_effect=subprocess.TimeoutExpired("fixture-secret", 1)):
            result = support.run_command(["fixture"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 999)
        self.assertNotIn("fixture-secret", result.stderr)
        self.assertEqual(support.AUDIT.summary(), 2)

    def test_negative_lsof_is_valid_but_failed_command_is_not(self):
        with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess(["lsof"], 1, "", "")):
            support.run_command(["lsof"])
        self.assertEqual(support.AUDIT.summary(), 0)
        with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess(["fixture"], 1, "fixture-secret", "private-error")):
            result = support.run_command(["fixture"])
        self.assertEqual(result.stdout, "")
        self.assertNotIn("private-error", result.stderr)
        self.assertEqual(support.AUDIT.summary(), 2)

    def test_invalid_config_is_not_a_clean_pass(self):
        path = self.root / "settings.json"
        path.write_text('{"ANTHROPIC_API_KEY":"fixture-secret",broken}')
        claude.scan_json_file(path)
        self.assertEqual(support.AUDIT.summary(), 2)
        self.assertNotIn("fixture-secret", self.output.getvalue())

    def test_broken_sqlite_is_incomplete(self):
        path = self.root / "fixture.db"
        path.write_text("fixture-secret-not-a-database")
        support.AUDIT.check(claude.scan_sqlite, path)
        self.assertEqual(support.AUDIT.summary(), 2)
        self.assertNotIn("fixture-secret", self.output.getvalue())

    def test_failed_browser_json_is_incomplete(self):
        path = self.root / "Preferences"
        path.write_text("fixture-secret-invalid-json")
        self.assertIsNone(network.safe_json(path))
        self.assertEqual(support.AUDIT.summary(), 2)

    def test_external_fixture_error_and_invalid_shape(self):
        with patch.object(network, "PUBLIC_IP_ENDPOINTS", [("fixture", "https://fixture.invalid", "json")]), \
             patch.object(network, "HTTPS_PROBES", []), \
             patch.object(network, "request_url", return_value=(200, "https://fixture.invalid", '[]', 0.01)):
            network.public_ip_probes(1)
        self.assertEqual(support.AUDIT.summary(), 2)
        support.AUDIT.records.clear()
        with patch.object(network, "PUBLIC_IP_ENDPOINTS", [("fixture", "https://fixture.invalid", "json")]), \
             patch.object(network, "HTTPS_PROBES", []), \
             patch.object(network, "request_url", return_value=(None, "https://fixture.invalid", 'fixture-secret', 0.01)):
            network.public_ip_probes(1)
        self.assertEqual(support.AUDIT.summary(), 2)
        self.assertNotIn("fixture-secret", self.output.getvalue())

    def test_claude_main_continues_after_failed_check(self):
        names = [name for name in vars(claude) if name.startswith("scan_")]
        called = []
        def fixture(*args):
            called.append(True)
        def broken_fixture(*args):
            raise PermissionError("fixture-secret")
        with contextlib.ExitStack() as stack:
            for name in names:
                stack.enter_context(patch.object(claude, name, broken_fixture if name == "scan_files" else fixture))
            stack.enter_context(patch.object(claude, "build_manifest", return_value={"completeness": "complete_within_inventory_scope"}))
            stack.enter_context(patch.object(claude, "render_text"))
            self.assertEqual(claude.main(["--audit"]), 2)
        self.assertTrue(called)
        self.assertNotIn("fixture-secret", self.output.getvalue())

    def test_network_main_without_external_is_explicitly_unmeasured(self):
        args = types.SimpleNamespace(external=False, post_ban=False, timeout=1,
                                     append_history=None, history=None)
        def fixture():
            return None
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(network, "parse_args", return_value=args))
            for name in ("local_proxy_env", "dns_system_summary", "watched_ports",
                         "dns_resolution", "browser_language_summary"):
                stack.enter_context(patch.object(network, name, fixture))
            stack.enter_context(patch.object(network.os, "readlink", return_value="/zoneinfo/Asia/Singapore"))
            request = stack.enter_context(patch.object(network, "request_url", side_effect=AssertionError("network forbidden")))
            self.assertEqual(network.main(), 0)
            request.assert_not_called()
        self.assertIn("external_probe: not_checked", self.output.getvalue())
        self.assertIn("browser_dns_webrtc: not_checked", self.output.getvalue())

    def test_sqlite_query_error_is_not_silently_skipped(self):
        class FakeConnection:
            def execute(self, query, *args):
                if "sqlite_master" in query:
                    return [("settings",)]
                if "PRAGMA" in query:
                    return types.SimpleNamespace(fetchall=lambda: [(0, "value")])
                raise RuntimeError("fixture-secret")

            def close(self):
                pass

        with patch.object(claude.sqlite3, "connect", return_value=FakeConnection()):
            claude.scan_sqlite(self.root / "fixture.db")
        self.assertEqual(support.AUDIT.summary(), 2)
        self.assertNotIn("fixture-secret", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
