from __future__ import annotations

from typing import Any

from ..models import AccountCandidate, Platform
from .base import AccountIdentityError, AccountProvider, require_identity


class BilibiliProvider(AccountProvider):
    platform = Platform.BILIBILI
    login_url = "https://passport.bilibili.com/login"
    identity_url = "https://www.bilibili.com/"

    def detect_identity(self, page: Any) -> AccountCandidate:
        page.goto(self.identity_url, wait_until="domcontentloaded")
        payload = page.evaluate(
            """async () => {
                const response = await fetch(
                    "https://api.bilibili.com/x/web-interface/nav",
                    { credentials: "include" }
                );
                return await response.json();
            }"""
        )
        return self.parse_nav(payload, source_url=page.url)

    def parse_nav(self, payload: object, source_url: str = "") -> AccountCandidate:
        if not isinstance(payload, dict):
            raise AccountIdentityError("identity_not_found", "哔哩哔哩账号接口返回了无法识别的数据。")
        data = payload.get("data")
        if not isinstance(data, dict) or not data.get("isLogin"):
            raise AccountIdentityError("not_logged_in", "哔哩哔哩尚未登录，请在打开的 Edge 窗口完成登录。")
        return require_identity(
            self.platform,
            str(data.get("uname", "")),
            str(data.get("mid", "")),
            source_url,
        )
