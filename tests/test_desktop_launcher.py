"""Keep the desktop launcher bound to the project-local runtime entry point."""

import unittest
from pathlib import Path


class DesktopLauncherTests(unittest.TestCase):
    def test_launcher_uses_its_own_checkout_and_local_virtualenv(self):
        root = Path(__file__).resolve().parent.parent
        source = (root / "JARVIS.bat").read_text(encoding="utf-8")
        self.assertIn('pushd "%~dp0"', source)
        self.assertIn('".venv\\Scripts\\python.exe" -u main.py', source)
        self.assertIn('if not exist ".venv\\Scripts\\python.exe"', source)
        self.assertNotIn("C:\\Users\\2025\\OneDrive\\Desktop\\JARVIS-OS-V.2-main", source)


if __name__ == "__main__":
    unittest.main()
