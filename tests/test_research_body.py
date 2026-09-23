"""Tests for research body and deep research capabilities."""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResearchBody(unittest.TestCase):
    """Basic research module smoke tests."""

    def test_import_deep_research(self):
        try:
            from actions import deep_research
            self.assertTrue(hasattr(deep_research, 'handle_deep_research'))
        except ImportError:
            self.skipTest("deep_research module not available")

    def test_import_web_search(self):
        try:
            from actions import web_search
            self.assertTrue(hasattr(web_search, 'handle_web_search'))
        except ImportError:
            self.skipTest("web_search module not available")


if __name__ == "__main__":
    unittest.main()
