"""Regression tests for the phone_control screen-verification gate.

The dispatcher used to run a screen `verify_action` (LLM vision) after EVERY
phone_control call — including invalid or failed actions. Verification must
only run after a real call/text initiation (CALL_INITIATED|/TEXT_SENT|),
matching the critical-action gating already used by full_control/screen_auto.
"""
import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402


class _StubUI:
    operational_ready = True
    muted = False

    def set_state(self, *args, **kwargs):
        pass


def _call(args):
    return SimpleNamespace(name="phone_control", args=args, id="call-1")


class TestPhoneControlVerificationGate(unittest.TestCase):
    def _dispatch(self, args, phone_return):
        jarvis = object.__new__(main.JarvisLive)
        jarvis.ui = _StubUI()
        jarvis._intercept_ui_tool_call = lambda name, params: None
        with patch("actions.learning_memory.track_pattern"), \
             patch("actions.learning_memory.set_context"), \
             patch("actions.phone_control.handle", return_value=phone_return), \
             patch("actions.screen_automation.handle",
                   return_value="VERIFY_OK|stub") as verify:
            fr = asyncio.run(jarvis._execute_tool(_call(args)))
        return fr.response["result"], verify

    def test_unknown_action_skips_verification(self):
        result, verify = self._dispatch(
            {"action": "bogus"}, "Unknown action: bogus. Valid: call, text")
        verify.assert_not_called()
        self.assertNotIn("[VERIFIED", result)

    def test_missing_target_error_skips_verification(self):
        result, verify = self._dispatch(
            {"action": "call"}, "ERROR: Provide a phone number or contact name.")
        verify.assert_not_called()

    def test_failed_call_skips_verification(self):
        result, verify = self._dispatch(
            {"action": "call", "number": "123"},
            "CALL_FAILED|Could not open phone app: boom")
        verify.assert_not_called()
        self.assertNotIn("[VERIFIED", result)

    def test_initiated_call_is_verified(self):
        result, verify = self._dispatch(
            {"action": "call", "contact": "Dana"},
            "CALL_INITIATED|Opening Skype to call Dana")
        verify.assert_called_once()
        self.assertIn("[VERIFIED] VERIFY_OK|stub", result)

    def test_sent_text_is_verified(self):
        result, verify = self._dispatch(
            {"action": "text", "contact": "Dana", "message": "hi"},
            "TEXT_SENT|Message sent to Dana: hi")
        verify.assert_called_once()
        self.assertIn("[VERIFIED] VERIFY_OK|stub", result)


if __name__ == "__main__":
    unittest.main()
