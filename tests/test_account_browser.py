from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.accounts.browser import (
    EdgeAccountBrowser,
    find_edge_executable,
    temporary_cookie_file,
    write_netscape_cookie_file,
)


class AccountBrowserTest(unittest.TestCase):
    def test_finds_first_existing_edge_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing.exe"
            edge = root / "msedge.exe"
            edge.write_text("", encoding="utf-8")

            self.assertEqual(find_edge_executable([missing, edge]), edge)

    def test_launches_persistent_context_with_isolated_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            edge = root / "msedge.exe"
            edge.write_text("", encoding="utf-8")
            profile = root / "profile"
            calls: list[dict[str, object]] = []

            class FakeChromium:
                def launch_persistent_context(self, **kwargs):
                    calls.append(kwargs)
                    return object()

            browser = EdgeAccountBrowser(edge_executable=edge)
            browser._launch_context(FakeChromium(), profile, headless=False)

            self.assertEqual(calls[0]["user_data_dir"], str(profile))
            self.assertEqual(calls[0]["executable_path"], str(edge))
            self.assertFalse(calls[0]["headless"])
            self.assertTrue(profile.is_dir())

    def test_writes_netscape_cookie_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "cookies.txt"
            write_netscape_cookie_file(
                [
                    {
                        "domain": ".example.com",
                        "path": "/",
                        "secure": True,
                        "expires": 1999999999,
                        "name": "sessionid",
                        "value": "secret-value",
                        "httpOnly": True,
                    }
                ],
                target,
            )

            text = target.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Netscape HTTP Cookie File"))
            self.assertIn("#HttpOnly_.example.com\tTRUE\t/\tTRUE\t1999999999\tsessionid\tsecret-value", text)

    def test_temporary_cookie_file_is_removed_after_use(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def cookie_loader(_profile: Path):
                return [
                    {
                        "domain": ".example.com",
                        "path": "/",
                        "secure": False,
                        "expires": 0,
                        "name": "sid",
                        "value": "value",
                    }
                ]

            with temporary_cookie_file(root / "profile", root / "temp", cookie_loader) as cookie_path:
                self.assertTrue(cookie_path.exists())
                self.assertNotIn("value", cookie_path.name)

            self.assertFalse(cookie_path.exists())


if __name__ == "__main__":
    unittest.main()
