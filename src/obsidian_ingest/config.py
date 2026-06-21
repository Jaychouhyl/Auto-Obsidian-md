from __future__ import annotations

import shutil
import tomllib
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathsConfig:
    queue_db: Path
    cache_dir: Path


@dataclass(frozen=True)
class ObsidianConfig:
    mode: str
    vault_path: Path
    folder: str
    rest_base_url: str
    rest_api_key: str


@dataclass(frozen=True)
class ToolsConfig:
    yt_dlp: str
    ffmpeg: str
    douyin_downloader: str
    douyin_config: str
    whisper: str
    funasr: str


@dataclass(frozen=True)
class LlmConfig:
    enabled: bool
    provider: str
    base_url: str
    api_key: str
    model: str
    language: str


@dataclass(frozen=True)
class RoutingConfig:
    enabled: bool
    fallback_folder: str
    allowed_folders: list[str]


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    paths: PathsConfig
    obsidian: ObsidianConfig
    tools: ToolsConfig
    llm: LlmConfig
    routing: RoutingConfig


DEFAULT_PROJECT_DIR = Path("D:/obsidian-ingest-pipeline")


def write_default_config(config_path: Path, vault_path: Path) -> None:
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    template = Path(__file__).resolve().parents[2] / "config.example.toml"
    text = template.read_text(encoding="utf-8")
    text = text.replace('vault_path = "D:/ObsidianVault"', f'vault_path = "{vault_path.as_posix()}"')
    text = text.replace('queue_db = "D:/obsidian-ingest-pipeline/data/queue.sqlite"', f'queue_db = "{(config_path.parent / "data" / "queue.sqlite").as_posix()}"')
    text = text.replace('cache_dir = "D:/obsidian-ingest-pipeline/cache"', f'cache_dir = "{(config_path.parent / "cache").as_posix()}"')
    config_path.write_text(text, encoding="utf-8")


def load_config(config_path: Path) -> AppConfig:
    config_path = Path(config_path)
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    paths = raw.get("paths", {})
    obsidian = raw.get("obsidian", {})
    tools = raw.get("tools", {})
    llm = raw.get("llm", {})
    routing = raw.get("routing", {})
    base_dir = config_path.parent
    fallback_folder = str(routing.get("fallback_folder", obsidian.get("folder", "Inbox/Learning Inbox")))
    allowed_folders = _string_list(routing.get("allowed_folders", []))
    if fallback_folder and fallback_folder not in allowed_folders:
        allowed_folders.append(fallback_folder)
    return AppConfig(
        config_path=config_path,
        paths=PathsConfig(
            queue_db=_path(paths.get("queue_db", base_dir / "data" / "queue.sqlite")),
            cache_dir=_path(paths.get("cache_dir", base_dir / "cache")),
        ),
        obsidian=ObsidianConfig(
            mode=str(obsidian.get("mode", "local")),
            vault_path=_path(obsidian.get("vault_path", base_dir / "vault")),
            folder=str(obsidian.get("folder", "Inbox/Learning Inbox")),
            rest_base_url=str(obsidian.get("rest_base_url", "http://127.0.0.1:27123")),
            rest_api_key=str(obsidian.get("rest_api_key", "")),
        ),
        tools=ToolsConfig(
            yt_dlp=str(tools.get("yt_dlp", "yt-dlp")),
            ffmpeg=str(tools.get("ffmpeg", "ffmpeg")),
            douyin_downloader=str(tools.get("douyin_downloader", "douyin-downloader")),
            douyin_config=str(tools.get("douyin_config", "")),
            whisper=str(tools.get("whisper", "whisper")),
            funasr=str(tools.get("funasr", "funasr")),
        ),
        llm=LlmConfig(
            enabled=bool(llm.get("enabled", False)),
            provider=str(llm.get("provider", "openai-compatible")),
            base_url=str(llm.get("base_url", "https://api.openai.com/v1")),
            api_key=_llm_api_key(str(llm.get("api_key", "")), str(llm.get("base_url", ""))),
            model=str(llm.get("model", "gpt-4o-mini")),
            language=str(llm.get("language", "zh-CN")),
        ),
        routing=RoutingConfig(
            enabled=bool(routing.get("enabled", False)),
            fallback_folder=fallback_folder,
            allowed_folders=allowed_folders,
        ),
    )


def tool_available(command: str) -> bool:
    return shutil.which(command) is not None


def _path(value: object) -> Path:
    return Path(str(value)).expanduser()


def _llm_api_key(value: str, base_url: str) -> str:
    value = value.strip()
    if value:
        return value
    generic = os.getenv("OBSIDIAN_INGEST_LLM_API_KEY", "").strip()
    if generic:
        return generic
    generic = _windows_user_env("OBSIDIAN_INGEST_LLM_API_KEY")
    if generic:
        return generic
    if "deepseek" in base_url.lower():
        deepseek = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if deepseek:
            return deepseek
        return _windows_user_env("DEEPSEEK_API_KEY")
    return ""


def _windows_user_env(name: str) -> str:
    try:
        import winreg  # type: ignore
    except ImportError:
        return ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return ""
    return str(value).strip()


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().replace("\\", "/").strip("/") for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip().replace("\\", "/").strip("/")]
    return []
