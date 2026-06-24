from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any


class Platform(StrEnum):
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass(frozen=True)
class AccountCandidate:
    platform: Platform
    display_name: str
    platform_user_id: str
    source_url: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "platform": self.platform.value,
            "display_name": self.display_name,
            "platform_user_id": self.platform_user_id,
            "source_url": self.source_url,
        }


@dataclass(frozen=True)
class AccountProfile:
    id: str
    platform: Platform
    display_name: str
    platform_user_id: str
    profile_dir: str
    status: AccountStatus = AccountStatus.UNKNOWN
    created_at: str = ""
    updated_at: str = ""
    last_verified_at: str = ""
    error: str = ""
    is_current: bool = False

    def with_current(self, is_current: bool) -> AccountProfile:
        return replace(self, is_current=is_current)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform.value,
            "display_name": self.display_name,
            "platform_user_id": self.platform_user_id,
            "profile_dir": self.profile_dir,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_verified_at": self.last_verified_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AccountProfile:
        return cls(
            id=str(value["id"]),
            platform=Platform(str(value["platform"])),
            display_name=str(value.get("display_name", "")).strip(),
            platform_user_id=str(value.get("platform_user_id", "")).strip(),
            profile_dir=str(value.get("profile_dir", "")).replace("\\", "/").strip("/"),
            status=AccountStatus(str(value.get("status", AccountStatus.UNKNOWN.value))),
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
            last_verified_at=str(value.get("last_verified_at", "")),
            error=str(value.get("error", "")),
        )
