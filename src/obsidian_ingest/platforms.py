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

ARTICLE_HOSTS = {
    "mp.weixin.qq.com": "wechat",
    "weixin.qq.com": "wechat",
    "zhihu.com": "zhihu",
    "www.zhihu.com": "zhihu",
    "xiaohongshu.com": "xiaohongshu",
    "www.xiaohongshu.com": "xiaohongshu",
    "xhslink.com": "xiaohongshu",
    "sspai.com": "sspai",
    "medium.com": "medium",
    "notion.site": "notion",
}

PODCAST_HOSTS = {
    "xiaoyuzhoufm.com": "podcast",
    "www.xiaoyuzhoufm.com": "podcast",
    "podcasts.apple.com": "podcast",
    "open.spotify.com": "podcast",
}

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".epub"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


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
        if suffix in IMAGE_EXTENSIONS:
            return PlatformInfo("local_file", "image")
        return PlatformInfo("local_file", "document")

    host = parsed.netloc.lower()
    platform = _match_host(host)
    if platform:
        return PlatformInfo(platform, "video")
    platform = _match_host(host, ARTICLE_HOSTS)
    if platform:
        return PlatformInfo(platform, "article")
    platform = _match_host(host, PODCAST_HOSTS)
    if platform:
        return PlatformInfo(platform, "audio")

    suffix = Path(parsed.path).suffix.lower()
    if suffix in AUDIO_EXTENSIONS:
        return PlatformInfo("web", "audio")
    if suffix in VIDEO_EXTENSIONS:
        return PlatformInfo("web", "video")
    if suffix in DOCUMENT_EXTENSIONS:
        return PlatformInfo("web", "document")
    if suffix in IMAGE_EXTENSIONS:
        return PlatformInfo("web", "image")
    return PlatformInfo("web", "article")


def _match_host(host: str, hosts: dict[str, str] | None = None) -> str | None:
    for known, platform in (hosts or VIDEO_HOSTS).items():
        if host == known or host.endswith("." + known):
            return platform
    return None
