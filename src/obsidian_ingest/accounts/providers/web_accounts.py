from __future__ import annotations

import re
from typing import Any

from ..models import AccountCandidate, Platform
from .base import AccountProvider, extract_json_string, require_identity


class ZhihuProvider(AccountProvider):
    platform = Platform.ZHIHU
    login_url = "https://www.zhihu.com/signin"
    identity_url = "https://www.zhihu.com/settings/profile"

    def detect_identity(self, page: Any) -> AccountCandidate:
        page.goto(self.identity_url, wait_until="domcontentloaded")
        return self.parse_identity(page.content(), page_title=page.title())

    def parse_identity(self, html: str, page_title: str = "") -> AccountCandidate:
        name = extract_json_string(html, ("fullname", "name", "displayName"))
        user_id = extract_json_string(html, ("urlToken", "url_token", "id"))
        if not name:
            name = _title_name(page_title, " - 知乎")
        if not user_id:
            match = re.search(r"people/([A-Za-z0-9_-]+)", html)
            user_id = match.group(1) if match else name
        return require_identity(self.platform, name, user_id, self.identity_url)


class XiaohongshuProvider(AccountProvider):
    platform = Platform.XIAOHONGSHU
    login_url = "https://www.xiaohongshu.com/explore"
    identity_url = "https://www.xiaohongshu.com/user/profile"

    def detect_identity(self, page: Any) -> AccountCandidate:
        page.goto(self.identity_url, wait_until="domcontentloaded")
        return self.parse_identity(page.content(), page_title=page.title())

    def parse_identity(self, html: str, page_title: str = "") -> AccountCandidate:
        name = extract_json_string(html, ("nickname", "nickName", "userName", "name"))
        user_id = extract_json_string(html, ("userId", "user_id", "redId", "red_id"))
        if not name:
            name = _title_name(page_title, " - 小红书")
        if not user_id:
            match = re.search(r"/user/profile/([A-Za-z0-9_-]+)", html)
            user_id = match.group(1) if match else name
        return require_identity(self.platform, name, user_id, self.identity_url)


class WeChatProvider(AccountProvider):
    platform = Platform.WECHAT
    login_url = "https://mp.weixin.qq.com/"
    identity_url = "https://mp.weixin.qq.com/"

    def detect_identity(self, page: Any) -> AccountCandidate:
        page.goto(self.identity_url, wait_until="domcontentloaded")
        return self.parse_identity(page.content(), page_title=page.title())

    def parse_identity(self, html: str, page_title: str = "") -> AccountCandidate:
        name = extract_json_string(html, ("nickname", "alias", "user_name", "username", "name"))
        user_id = extract_json_string(html, ("fakeid", "user_name", "username", "uin"))
        if not name:
            name = _title_name(page_title, "微信公众平台")
        if not user_id:
            user_id = name
        return require_identity(self.platform, name, user_id, self.identity_url)


def _title_name(title: str, suffix: str) -> str:
    text = str(title).strip()
    if suffix and text.endswith(suffix):
        text = text[: -len(suffix)].strip()
    return text.strip(" -|·")
