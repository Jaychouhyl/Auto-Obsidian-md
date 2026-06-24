from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from ..models import AccountCandidate, Platform


class AccountIdentityError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class AccountProvider(ABC):
    platform: Platform
    login_url: str
    identity_url: str

    @abstractmethod
    def detect_identity(self, page: Any) -> AccountCandidate:
        raise NotImplementedError


def extract_json_string(text: str, keys: tuple[str, ...]) -> str:
    for key in keys:
        pattern = rf'["\']{re.escape(key)}["\']\s*:\s*["\']((?:\\.|[^"\\\'])*)["\']'
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1)
        try:
            return str(json.loads(f'"{raw}"')).strip()
        except json.JSONDecodeError:
            return raw.strip()
    return ""


def clean_identity(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def require_identity(
    platform: Platform,
    display_name: str,
    platform_user_id: str,
    source_url: str = "",
) -> AccountCandidate:
    name = clean_identity(display_name)
    user_id = clean_identity(platform_user_id)
    if not name or not user_id:
        raise AccountIdentityError(
            "identity_not_found",
            f"未能从 {platform.value} 页面识别账号，请确认已经登录并打开个人主页。",
        )
    return AccountCandidate(
        platform=platform,
        display_name=name,
        platform_user_id=user_id,
        source_url=source_url,
    )
