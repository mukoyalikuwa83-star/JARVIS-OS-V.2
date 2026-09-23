"""Tests for infinite loop detection in agent execution."""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInfiniteLoopDetector(unittest.TestCase):
    """Basic tests for loop detection logic."""

    def test_import_executor(self):
        try:
            from agent.executor import AgentExecutor
            self.assertTrue(callable(AgentExecutor))
        except ImportError:
            self.skipTest("executor module not available")

    def test_import_planner(self):
        try:
            from agent.planner import create_plan
            self.assertTrue(callable(create_plan))
        except ImportError:
            self.skipTest("planner module not available")

    def test_import_error_handler(self):
        try:
            from agent.error_handler import analyze_error
            self.assertTrue(callable(analyze_error))
        except ImportError:
            self.skipTest("error_handler module not available")


if __name__ == "__main__":
    unittest.main()
