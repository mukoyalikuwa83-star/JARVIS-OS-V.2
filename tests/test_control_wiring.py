"""Exercise dashboard control adapters without touching the desktop or network."""

import asyncio
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from actions.computer_control import computer_control
from actions.content_engine import ContentEngineAgent, handle as content_handle
from actions.smart_home import SmartHomeAgent


class DesktopAdapterTests(unittest.TestCase):
    def test_types_through_guarded_text_entry_without_enter(self):
        result = types.SimpleNamespace(ok=True, message="Safely typed text.")
        with patch.dict(os.environ, {"JARVIS_QA_MODE": "1", "JARVIS_QA_ALLOW_DESKTOP": "1"}):
            with patch("actions.safe_text_entry.safe_type_text", return_value=result) as safe_type:
                response = computer_control({"action": "smart_type", "text": "hello"})
        self.assertTrue(response["success"])
        safe_type.assert_called_once_with("hello", purpose="generic", clear_first=True)

    def test_click_routes_to_pyautogui_with_screen_bounds_check(self):
        fake = types.SimpleNamespace(
            FAILSAFE=False,
            size=lambda: (1920, 1080),
            click=lambda *args: calls.append(args),
        )
        calls = []
        with patch.dict(os.environ, {"JARVIS_QA_MODE": "1", "JARVIS_QA_ALLOW_DESKTOP": "1"}):
            with patch.dict(sys.modules, {"pyautogui": fake}):
                response = computer_control({"action": "click", "x": 12, "y": 34})
        self.assertTrue(response["success"])
        self.assertTrue(fake.FAILSAFE)
        self.assertEqual(calls, [(12, 34)])

    def test_out_of_bounds_click_is_rejected(self):
        fake = types.SimpleNamespace(size=lambda: (100, 100), click=lambda *_: self.fail("must not click"))
        with patch.dict(os.environ, {"JARVIS_QA_MODE": "1", "JARVIS_QA_ALLOW_DESKTOP": "1"}):
            with patch.dict(sys.modules, {"pyautogui": fake}):
                response = computer_control({"action": "click", "x": 100, "y": 20})
        self.assertFalse(response["success"])

    def test_qa_mode_blocks_desktop_mutations(self):
        with patch.dict(os.environ, {"JARVIS_QA_MODE": "1", "JARVIS_QA_ALLOW_DESKTOP": "0"}):
            response = computer_control({"action": "click", "x": 12, "y": 34})
        self.assertFalse(response["success"])
        self.assertIn("QA SAFETY BLOCK", response["error"])


class SmartHomeAdapterTests(unittest.TestCase):
    def test_unconfigured_connector_does_not_claim_success(self):
        agent = SmartHomeAgent()
        response = asyncio.run(agent._ha_request("GET", "/api/states"))
        self.assertFalse(response["success"])
        self.assertIn("not configured", response["error"])

    def test_remote_home_assistant_hosts_are_rejected(self):
        agent = SmartHomeAgent()
        agent._ha_config = {"url": "https://example.com", "token": "test-only"}
        response = asyncio.run(agent._ha_request("GET", "/api/states"))
        self.assertFalse(response["success"])
        self.assertIn("local network", response["error"])

    def test_light_control_calls_only_the_mapped_service(self):
        agent = SmartHomeAgent()
        entity = {"entity_id": "light.desk", "attributes": {"friendly_name": "Desk"}}
        with patch.object(agent, "_find_entity", new=AsyncMock(return_value=(entity, [entity], None))):
            with patch.object(agent, "_ha_request", new=AsyncMock(return_value={"success": True, "data": []})) as request:
                response = asyncio.run(agent._control_device({"name": "Desk", "command": "on"}))
        self.assertTrue(response["success"])
        request.assert_awaited_once_with(
            "POST", "/api/services/light/turn_on", json_data={"entity_id": "light.desk"}
        )

    def test_locks_cannot_be_controlled_through_generic_device_control(self):
        agent = SmartHomeAgent()
        entity = {"entity_id": "lock.front_door", "attributes": {"friendly_name": "Front Door"}}
        with patch.object(agent, "_find_entity", new=AsyncMock(return_value=(entity, [entity], None))):
            response = asyncio.run(agent._control_device({"name": "Front Door", "command": "off"}))
        self.assertFalse(response["success"])
        self.assertIn("not enabled", response["error"])


class ContentAdapterTests(unittest.TestCase):
    def test_dashboard_content_action_creates_a_draft(self):
        with patch("actions.content_engine._content_engine_agent", None):
            response = content_handle({"action": "tutorial", "target": "Home Assistant"})
        self.assertTrue(response["success"])
        self.assertEqual(response["draft"]["status"], "draft")
        self.assertEqual(response["draft"]["topic"], "Home Assistant")

    def test_unconnected_publishing_does_not_claim_success(self):
        response = asyncio.run(ContentEngineAgent()._publish_to_platform({"title": "Draft"}, "blog"))
        self.assertFalse(response["success"])
        self.assertIn("not connected", response["error"])


if __name__ == "__main__":
    unittest.main()
