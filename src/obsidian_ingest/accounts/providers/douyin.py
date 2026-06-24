from __future__ import annotations

import re
from typing import Any

from ..models import AccountCandidate, Platform
from .base import AccountProvider, extract_json_string, require_identity


class DouyinProvider(AccountProvider):
    platform = Platform.DOUYIN
    login_url = "https://www.douyin.com/"
    identity_url = "https://www.douyin.com/user/self?showTab=favorite_collection"

    def detect_identity(self, page: Any) -> AccountCandidate:
        page.goto(self.identity_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        return self.parse_identity(
            page.content(),
            page_title=page.title(),
            source_url=page.url,
        )

    def parse_identity(
        self,
        html: str,
        page_title: str = "",
        source_url: str = "",
    ) -> AccountCandidate:
        user_id = extract_json_string(html, ("uniqueId", "unique_id", "shortId"))
        if not user_id:
            match = re.search(r"抖音号\s*[：:]\s*([A-Za-z0-9_.-]+)", html)
            user_id = match.group(1) if match else ""
        name = extract_json_string(html, ("nickname", "nickName", "displayName"))
        if not name and page_title:
            name = re.sub(r"\s*[-_的].*$", "", page_title).strip()
        return require_identity(self.platform, name, user_id, source_url)
