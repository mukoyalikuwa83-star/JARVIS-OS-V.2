"""full_control env listing must never expose secret-looking values."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.full_control import handle  # noqa: E402


class TestEnvListRedaction(unittest.TestCase):
    def test_sensitive_values_are_redacted(self):
        fake_env = {
            "SAFE_VAR": "visible",
            "MY_API_KEY": "super-secret-value",
            "DB_PASSWORD": "hunter2",
            "AUTH_TOKEN": "tok123",
        }
        with patch.dict(os.environ, fake_env, clear=True):
            out = handle({"action": "list_env_vars"})
        self.assertIn("SAFE_VAR=visible", out)
        self.assertNotIn("super-secret-value", out)
        self.assertNotIn("hunter2", out)
        self.assertNotIn("tok123", out)
        self.assertIn("MY_API_KEY=<redacted>", out)


if __name__ == "__main__":
    unittest.main()
