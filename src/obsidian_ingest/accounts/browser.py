from __future__ import annotations

import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from .models import AccountCandidate
from .providers.base import AccountIdentityError, AccountProvider


class BrowserUnavailableError(RuntimeError):
    pass


def default_edge_candidates() -> list[Path]:
    candidates: list[Path] = []
    for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        root = os.getenv(variable, "").strip()
        if root:
            candidates.append(Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe")
    return candidates


def find_edge_executable(candidates: list[Path] | None = None) -> Path | None:
    for candidate in candidates or default_edge_candidates():
        path = Path(candidate)
        if path.is_file():
            return path
    return None


class EdgeAccountBrowser:
    def __init__(self, edge_executable: Path | None = None):
        self.edge_executable = Path(edge_executable) if edge_executable else find_edge_executable()

    def login(
        self,
        profile_dir: Path,
        provider: AccountProvider,
        timeout_seconds: int = 600,
        poll_seconds: float = 2.0,
    ) -> AccountCandidate:
        with self._playwright() as playwright:
            context = self._launch_context(playwright.chromium, profile_dir, headless=False)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(provider.login_url, wait_until="domcontentloaded")
                deadline = time.monotonic() + timeout_seconds
                last_error: AccountIdentityError | None = None
                while time.monotonic() < deadline:
                    probe = context.new_page()
                    try:
                        return provider.detect_identity(probe)
                    except AccountIdentityError as exc:
                        last_error = exc
                    finally:
                        probe.close()
                    time.sleep(poll_seconds)
                message = str(last_error) if last_error else "登录等待超时。"
                raise AccountIdentityError(
                    "login_timeout",
                    f"{message} 请重新发起登录，并在 {timeout_seconds} 秒内完成。",
                )
            finally:
                context.close()

    def verify(self, profile_dir: Path, provider: AccountProvider) -> AccountCandidate:
        with self._playwright() as playwright:
            context = self._launch_context(playwright.chromium, profile_dir, headless=True)
            try:
                page = context.new_page()
                try:
                    return provider.detect_identity(page)
                finally:
                    page.close()
            finally:
                context.close()

    def read_cookies(self, profile_dir: Path) -> list[dict[str, Any]]:
        with self._playwright() as playwright:
            context = self._launch_context(playwright.chromium, profile_dir, headless=True)
            try:
                return list(context.cookies())
            finally:
                context.close()

    def import_cookies(self, profile_dir: Path, cookies: list[dict[str, Any]]) -> None:
        with self._playwright() as playwright:
            context = self._launch_context(playwright.chromium, profile_dir, headless=True)
            try:
                context.add_cookies(cookies)
            finally:
                context.close()

    def _launch_context(self, chromium: Any, profile_dir: Path, headless: bool) -> Any:
        if self.edge_executable is None or not self.edge_executable.is_file():
            raise BrowserUnavailableError(
                "未找到 Microsoft Edge，请安装或修复 Edge 后重试账号登录。"
            )
        profile = Path(profile_dir)
        profile.mkdir(parents=True, exist_ok=True)
        return chromium.launch_persistent_context(
            user_data_dir=str(profile),
            executable_path=str(self.edge_executable),
            headless=headless,
            args=["--disable-features=Translate", "--no-first-run"],
        )

    @staticmethod
    @contextmanager
    def _playwright() -> Iterator[Any]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserUnavailableError(
                "缺少 Playwright 运行组件，请重新安装 Obsidian Ingest Studio。"
            ) from exc
        with sync_playwright() as playwright:
            yield playwright


def write_netscape_cookie_file(cookies: list[dict[str, Any]], target: Path) -> None:
    lines = ["# Netscape HTTP Cookie File", "# Generated temporarily by Obsidian Ingest Studio", ""]
    for cookie in cookies:
        domain = _single_line(cookie.get("domain", ""))
        if not domain:
            continue
        http_only = bool(cookie.get("httpOnly", False))
        rendered_domain = f"#HttpOnly_{domain}" if http_only else domain
        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
        path = _single_line(cookie.get("path", "/")) or "/"
        secure = "TRUE" if cookie.get("secure") else "FALSE"
        expires = max(0, int(float(cookie.get("expires", 0) or 0)))
        name = _single_line(cookie.get("name", ""))
        value = _single_line(cookie.get("value", ""))
        if not name:
            continue
        lines.append(
            "\t".join(
                [
                    rendered_domain,
                    include_subdomains,
                    path,
                    secure,
                    str(expires),
                    name,
                    value,
                ]
            )
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


@contextmanager
def temporary_cookie_file(
    profile_dir: Path,
    temp_dir: Path,
    cookie_loader: Callable[[Path], list[dict[str, Any]]] | None = None,
) -> Iterator[Path]:
    directory = Path(temp_dir)
    directory.mkdir(parents=True, exist_ok=True)
    loader = cookie_loader or EdgeAccountBrowser().read_cookies
    cookies = loader(Path(profile_dir))
    if not cookies:
        raise AccountIdentityError("no_cookies", "当前账号没有可用 Cookie，请先重新登录并校验账号。")
    handle = tempfile.NamedTemporaryFile(
        prefix="account-",
        suffix=".cookies.txt",
        dir=directory,
        delete=False,
    )
    cookie_path = Path(handle.name)
    handle.close()
    try:
        write_netscape_cookie_file(cookies, cookie_path)
        yield cookie_path
    finally:
        cookie_path.unlink(missing_ok=True)


def _single_line(value: object) -> str:
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()
