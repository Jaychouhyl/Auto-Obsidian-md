from __future__ import annotations

from typing import Any

from ..models import AccountCandidate, Platform
from .base import AccountProvider, extract_json_string, require_identity


class YouTubeProvider(AccountProvider):
    platform = Platform.YOUTUBE
    login_url = "https://accounts.google.com/ServiceLogin?service=youtube"
    identity_url = "https://www.youtube.com/account"

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
        user_id = extract_json_string(html, ("channelId", "externalId", "browseId"))
        name = extract_json_string(html, ("accountName", "channelName", "displayName"))
        if not name and user_id:
            name = page_title.replace("- YouTube", "").strip()
        return require_identity(self.platform, name, user_id, source_url)
