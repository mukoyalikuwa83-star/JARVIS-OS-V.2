"""Tests for desktop integration capabilities."""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDesktopIntegration(unittest.TestCase):
    """Basic desktop integration smoke tests."""

    def test_import_open_app(self):
        try:
            from actions.open_app import open_application
            self.assertTrue(callable(open_application))
        except ImportError:
            self.skipTest("open_app module not available")

    def test_import_computer_control(self):
        try:
            from actions import computer_control
            self.assertTrue(hasattr(computer_control, 'handle_computer_control'))
        except ImportError:
            self.skipTest("computer_control module not available")

    def test_import_media_control(self):
        try:
            from actions import media_control
            self.assertTrue(hasattr(media_control, 'handle_media_control'))
        except ImportError:
            self.skipTest("media_control module not available")

    def test_import_file_controller(self):
        try:
            from actions import file_controller
            self.assertTrue(hasattr(file_controller, 'handle_file_controller'))
        except ImportError:
            self.skipTest("file_controller module not available")


if __name__ == "__main__":
    unittest.main()
