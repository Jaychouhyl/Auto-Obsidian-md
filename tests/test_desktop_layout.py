from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "desktop" / "src" / "styles.css"


class DesktopLayoutTest(unittest.TestCase):
    def test_sidebar_is_fixed_while_main_content_scrolls(self) -> None:
        css = CSS.read_text(encoding="utf-8")

        self.assertRegex(css, r"html,\s*\nbody,\s*\n#app\s*\{[^}]*height:\s*100%;")
        self.assertRegex(css, r"\.shell\s*\{[^}]*height:\s*100vh;[^}]*overflow:\s*hidden;")
        self.assertRegex(css, r"aside\s*\{[^}]*height:\s*100vh;[^}]*overflow-y:\s*auto;")
        self.assertRegex(css, r"main\s*\{[^}]*height:\s*100vh;[^}]*overflow-y:\s*auto;")


if __name__ == "__main__":
    unittest.main()
