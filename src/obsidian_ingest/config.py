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
class OutputsConfig:
    formats: list[str]
    html_dir: Path
    csv_path: Path
    notion_token: str
    notion_database_id: str
    notion_title_property: str
    notion_api_base: str


@dataclass(frozen=True)
class PromptConfig:
    active_template: str
    custom_instruction: str


@dataclass(frozen=True)
class NoteTemplateConfig:
    active_template: str
    include_transcript: bool
    include_source_notes: bool
    attribution_name: str


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    paths: PathsConfig
    obsidian: ObsidianConfig
    tools: ToolsConfig
    llm: LlmConfig
    routing: RoutingConfig
    outputs: OutputsConfig
    prompt: PromptConfig
    note_template: NoteTemplateConfig


def _default_project_dir() -> Path:
    override = os.getenv("OBSIDIAN_INGEST_HOME", "").strip()
    if override:
        return Path(override)
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "Obsidian Ingest Studio"
    return Path.home() / ".obsidian-ingest"


DEFAULT_PROJECT_DIR = _default_project_dir()


def write_default_config(config_path: Path, vault_path: Path) -> None:
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    template = Path(__file__).resolve().parents[2] / "config.example.toml"
    if template.exists():
        text = template.read_text(encoding="utf-8")
        text = text.replace('vault_path = "./sample-vault"', f'vault_path = "{vault_path.as_posix()}"')
        text = text.replace('queue_db = "./data/queue.sqlite"', f'queue_db = "{(config_path.parent / "data" / "queue.sqlite").as_posix()}"')
        text = text.replace('cache_dir = "./cache"', f'cache_dir = "{(config_path.parent / "cache").as_posix()}"')
    else:
        text = _default_config_template(config_path, vault_path)
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
    outputs = raw.get("outputs", {})
    prompt = raw.get("prompt", {})
    note_template = raw.get("note_template", {})
    base_dir = config_path.parent
    fallback_folder = str(routing.get("fallback_folder", obsidian.get("folder", "Inbox/Learning Inbox")))
    allowed_folders = _string_list(routing.get("allowed_folders", []))
    if fallback_folder and fallback_folder not in allowed_folders:
        allowed_folders.append(fallback_folder)
    output_formats = _output_formats(outputs.get("formats", ["markdown"]))
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
        outputs=OutputsConfig(
            formats=output_formats,
            html_dir=_path(outputs.get("html_dir", base_dir / "exports" / "html")),
            csv_path=_path(outputs.get("csv_path", base_dir / "exports" / "notes-index.csv")),
            notion_token=_secret_value(str(outputs.get("notion_token", "")), ("NOTION_TOKEN", "NOTION_API_KEY")),
            notion_database_id=str(outputs.get("notion_database_id", "")).strip(),
            notion_title_property=str(outputs.get("notion_title_property", "Name")).strip() or "Name",
            notion_api_base=str(outputs.get("notion_api_base", "https://api.notion.com/v1")).rstrip("/"),
        ),
        prompt=PromptConfig(
            active_template=str(prompt.get("active_template", "learning")).strip() or "learning",
            custom_instruction=str(prompt.get("custom_instruction", "")).strip(),
        ),
        note_template=NoteTemplateConfig(
            active_template=str(note_template.get("active_template", "study_note")).strip() or "study_note",
            include_transcript=bool(note_template.get("include_transcript", True)),
            include_source_notes=bool(note_template.get("include_source_notes", True)),
            attribution_name=str(note_template.get("attribution_name", "小黄狗")).strip() or "小黄狗",
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


def _secret_value(value: str, env_names: tuple[str, ...]) -> str:
    value = value.strip()
    if value:
        return value
    for name in env_names:
        candidate = os.getenv(name, "").strip()
        if candidate:
            return candidate
        candidate = _windows_user_env(name)
        if candidate:
            return candidate
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


def _output_formats(value: object) -> list[str]:
    allowed = {"markdown", "html", "csv", "notion"}
    result: list[str] = []
    for item in _string_list(value):
        normalized = item.strip().lower()
        if normalized == "excel":
            normalized = "csv"
        if normalized in allowed and normalized not in result:
            result.append(normalized)
    return result or ["markdown"]


def _default_config_template(config_path: Path, vault_path: Path) -> str:
    queue_db = (config_path.parent / "data" / "queue.sqlite").as_posix()
    cache_dir = (config_path.parent / "cache").as_posix()
    vault = vault_path.as_posix()
    return f"""[paths]
queue_db = "{queue_db}"
cache_dir = "{cache_dir}"

[obsidian]
mode = "local"
vault_path = "{vault}"
folder = "Inbox/Learning Inbox"
rest_base_url = "http://127.0.0.1:27123"
rest_api_key = ""

[tools]
yt_dlp = "yt-dlp"
ffmpeg = "ffmpeg"
douyin_downloader = "douyin-dl"
douyin_config = ""
whisper = "whisper"
funasr = "funasr"

[llm]
enabled = false
provider = "openai-compatible"
base_url = "https://api.deepseek.com/v1"
api_key = ""
model = "deepseek-chat"
language = "zh-CN"

[outputs]
formats = ["markdown"]
html_dir = "{(config_path.parent / "exports" / "html").as_posix()}"
csv_path = "{(config_path.parent / "exports" / "notes-index.csv").as_posix()}"
notion_token = ""
notion_database_id = ""
notion_title_property = "Name"
notion_api_base = "https://api.notion.com/v1"

[prompt]
active_template = "learning"
custom_instruction = ""

[note_template]
active_template = "study_note"
include_transcript = true
include_source_notes = true
attribution_name = "小黄狗"

[routing]
enabled = true
fallback_folder = "Inbox/Learning Inbox"
allowed_folders = [
    "AI学习",
    "考研资料汇总",
    "炒股与量化学习",
    "研后/英语学习",
    "工作",
    "Life",
    "Inbox/Learning Inbox",
]
"""
