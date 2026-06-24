from __future__ import annotations

from ..models import Platform
from .base import AccountProvider
from .bilibili import BilibiliProvider
from .douyin import DouyinProvider
from .tiktok import TikTokProvider
from .youtube import YouTubeProvider


def provider_for(platform: Platform) -> AccountProvider:
    providers: dict[Platform, AccountProvider] = {
        Platform.DOUYIN: DouyinProvider(),
        Platform.BILIBILI: BilibiliProvider(),
        Platform.YOUTUBE: YouTubeProvider(),
        Platform.TIKTOK: TikTokProvider(),
    }
    return providers[platform]


__all__ = ["provider_for"]
