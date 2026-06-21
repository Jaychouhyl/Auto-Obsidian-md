from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class PlatformInfo:
    platform: str
    content_type: str


VIDEO_HOSTS = {
    "douyin.com": "douyin",
    "v.douyin.com": "douyin",
    "iesdouyin.com": "douyin",
    "youtube.com": "youtube",
    "www.youtube.com": "youtube",
    "youtu.be": "youtube",
    "bilibili.com": "bilibili",
    "www.bilibili.com": "bilibili",
    "m.bilibili.com": "bilibili",
    "tiktok.com": "tiktok",
    "www.tiktok.com": "tiktok",
}

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".epub"}


def detect_platform(raw: str) -> PlatformInfo:
    value = raw.strip()
    parsed = urlparse(value)

    if not parsed.scheme or len(parsed.scheme) == 1:
        suffix = Path(value).suffix.lower()
        if suffix in AUDIO_EXTENSIONS:
            return PlatformInfo("local_file", "audio")
        if suffix in VIDEO_EXTENSIONS:
            return PlatformInfo("local_file", "video")
        if suffix in DOCUMENT_EXTENSIONS:
            return PlatformInfo("local_file", "document")
        return PlatformInfo("local_file", "document")

    host = parsed.netloc.lower()
    platform = _match_host(host)
    if platform:
        return PlatformInfo(platform, "video")

    suffix = Path(parsed.path).suffix.lower()
    if suffix in AUDIO_EXTENSIONS:
        return PlatformInfo("web", "audio")
    if suffix in VIDEO_EXTENSIONS:
        return PlatformInfo("web", "video")
    if suffix in DOCUMENT_EXTENSIONS:
        return PlatformInfo("web", "document")
    return PlatformInfo("web", "article")


def _match_host(host: str) -> str | None:
    for known, platform in VIDEO_HOSTS.items():
        if host == known or host.endswith("." + known):
            return platform
    return None
