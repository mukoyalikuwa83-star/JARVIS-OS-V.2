"""Local dashboard routing, display, and loopback safety checks."""

import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.dashboard import _is_local_same_origin, app


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url="http://127.0.0.1:8080")

    def test_blue_dashboard_page_renders_with_unknown_initial_state(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("JARVIS Dashboard", response.text)
        self.assertIn("Operations Overview", response.text)
        self.assertIn("Verify Integrity", response.text)
        self.assertIn("STATUS UNKNOWN", response.text)
        self.assertIn("Kill Switch Status", response.text)

    def test_local_status_endpoint_returns_guardian_state(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("any_active", payload)
        self.assertIn("active_kills", payload)

    def test_operations_overview_shows_runtime_and_connector_readiness_without_secrets(self):
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "configured-test-key",
            "JARVIS_HOME_ASSISTANT_URL": "http://homeassistant.local:8123",
            "JARVIS_HOME_ASSISTANT_TOKEN": "configured-test-token",
        }):
            response = self.client.get("/api/overview")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("runtime_seconds", payload)
        self.assertIn("python_version", payload)
        self.assertTrue(all(item["configured"] for item in payload["integrations"]))
        serialized = json.dumps(payload)
        self.assertNotIn("configured-test-key", serialized)
        self.assertNotIn("configured-test-token", serialized)

    def test_operations_overview_marks_missing_connectors_for_setup(self):
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY",
            "JARVIS_HOME_ASSISTANT_URL": "",
            "JARVIS_HOME_ASSISTANT_TOKEN": "",
        }, clear=False):
            response = self.client.get("/api/overview")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(not item["configured"] for item in response.json()["integrations"]))

    def test_cross_origin_requests_are_rejected_before_control_routes(self):
        response = self.client.post(
            "/api/kill",
            headers={"origin": "https://attacker.example"},
            json={"layer": "LOCAL_STOP", "reason": "MANUAL_LOCAL", "domain": "all"},
        )
        self.assertEqual(response.status_code, 403)

    def test_non_loopback_host_is_rejected(self):
        response = self.client.get("/api/status", headers={"host": "jarvis.attacker.example"})
        self.assertEqual(response.status_code, 403)

    def test_audit_recent_honors_and_caps_the_requested_count(self):
        with patch("core.audit_log.get_recent_entries", return_value=[]) as recent:
            response = self.client.get("/api/audit/recent?count=9999")
        self.assertEqual(response.status_code, 200)
        recent.assert_called_once_with(domain=None, count=200)

    def test_websocket_origin_must_match_the_local_dashboard(self):
        self.assertTrue(_is_local_same_origin(
            "127.0.0.1:8080", "http://127.0.0.1:8080", "http"
        ))
        self.assertFalse(_is_local_same_origin(
            "127.0.0.1:8080", "https://attacker.example", "http"
        ))
        self.assertFalse(_is_local_same_origin(
            "192.168.1.10:8080", None, "http"
        ))

    def test_local_websocket_receives_initial_safety_status(self):
        with self.client.websocket_connect(
            "/ws", headers={
                "host": "127.0.0.1:8080",
                "origin": "http://127.0.0.1:8080",
            }
        ) as websocket:
            message = json.loads(websocket.receive_text())
        self.assertEqual(message["type"], "status")
        self.assertIn("any_active", message["data"])


if __name__ == "__main__":
    unittest.main()
