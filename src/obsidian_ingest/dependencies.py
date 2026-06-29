from __future__ import annotations

import os
import re
import shutil
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .accounts.browser import find_edge_executable
from .config import AppConfig


CommandResolver = Callable[[str], str | None]
EdgeFinder = Callable[[], Path | None]
Downloader = Callable[[str, Path], None]


@dataclass(frozen=True)
class ToolDefinition:
    id: str
    label: str
    config_key: str
    configured: str
    purpose: str
    installable: bool
    url: str
    target: Path
    manual_action: str


def dependency_report(
    config: AppConfig,
    command_resolver: CommandResolver | None = None,
    edge_finder: EdgeFinder | None = None,
) -> dict[str, Any]:
    resolver = command_resolver or _resolve_command
    find_edge = edge_finder or find_edge_executable
    tools_dir = _tools_dir(config)
    items: list[dict[str, Any]] = []

    for definition in _tool_definitions(config):
        resolved = resolver(definition.configured)
        builtin_ocr = definition.id == "ocr" and definition.configured.strip().lower() in {"", "builtin"}
        status = "ready" if resolved or builtin_ocr else "missing"
        items.append(
            {
                "id": definition.id,
                "label": definition.label,
                "status": status,
                "configured": definition.configured,
                "resolved_path": resolved or ("内置 OCR 入口" if builtin_ocr else ""),
                "installable": definition.installable and _is_windows(),
                "config_key": definition.config_key,
                "purpose": definition.purpose,
                "manual_action": definition.manual_action,
                "managed_target": str(definition.target),
            }
        )

    edge = find_edge()
    items.append(
        {
            "id": "edge",
            "label": "Microsoft Edge",
            "status": "ready" if edge else "missing",
            "configured": "",
            "resolved_path": str(edge) if edge else "",
            "installable": False,
            "config_key": "",
            "purpose": "账号登录与 Cookie 导出",
            "manual_action": "安装或修复 Microsoft Edge 后重新检测。",
            "managed_target": "",
        }
    )

    llm_ready = (not config.llm.enabled) or bool(config.llm.api_key)
    items.append(
        {
            "id": "llm-api-key",
            "label": "DeepSeek API Key",
            "status": "ready" if llm_ready else "missing",
            "configured": "configured" if config.llm.api_key else "",
            "resolved_path": "",
            "installable": False,
            "config_key": "llm.api_key",
            "purpose": "LLM 摘要、标签和自动分类",
            "manual_action": "在配置页填写 DeepSeek API key，或设置 DEEPSEEK_API_KEY。",
            "managed_target": "",
        }
    )

    return {
        "status": "done",
        "tools_dir": str(tools_dir),
        "items": items,
        "summary": {
            "ready": sum(1 for item in items if item["status"] == "ready"),
            "missing": sum(1 for item in items if item["status"] != "ready"),
            "installable_missing": sum(
                1 for item in items if item["status"] != "ready" and item["installable"]
            ),
        },
        "notes": [
            "Docker 不是桌面版必需项。",
            "yt-dlp 和 ffmpeg 可由软件托管安装；账号登录、API key 和大型转写模型需要用户确认或单独配置。",
        ],
    }


def install_managed_dependencies(
    config: AppConfig,
    tool_ids: list[str] | None = None,
    dry_run: bool = False,
    downloader: Downloader | None = None,
) -> dict[str, Any]:
    requested = tool_ids or ["yt-dlp", "ffmpeg"]
    definitions = {item.id: item for item in _tool_definitions(config)}
    download = downloader or _download_file
    planned: list[dict[str, str]] = []
    installed: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    updates: dict[str, str] = {}

    for tool_id in requested:
        definition = definitions.get(tool_id)
        if definition is None:
            skipped.append({"id": tool_id, "reason": "unknown_tool"})
            continue
        if not (definition.installable and _is_windows()):
            skipped.append({"id": tool_id, "reason": definition.manual_action})
            continue
        plan = {
            "id": definition.id,
            "label": definition.label,
            "url": definition.url,
            "target": str(definition.target),
            "config_key": definition.config_key,
        }
        planned.append(plan)
        if dry_run:
            continue
        installed_path = _install_tool(definition, download)
        updates[definition.config_key] = installed_path.as_posix()
        installed.append({**plan, "path": str(installed_path)})

    if updates and not dry_run:
        update_tools_config(config.config_path, updates)

    return {
        "status": "done",
        "config_path": str(config.config_path),
        "tools_dir": str(_tools_dir(config)),
        "planned": planned,
        "installed": installed,
        "skipped": skipped,
        "dry_run": dry_run,
    }


def format_dependency_report(report: dict[str, Any]) -> str:
    lines = ["Dependency checks:"]
    for item in report["items"]:
        marker = "OK" if item["status"] == "ready" else "WARN"
        detail = item["resolved_path"] or item["configured"] or item["manual_action"]
        lines.append(f"- [{marker}] {item['label']}: {detail}")
    return "\n".join(lines)


def format_install_result(result: dict[str, Any]) -> str:
    if result["dry_run"]:
        prefix = "Planned"
        items = result["planned"]
    else:
        prefix = "Installed"
        items = result["installed"]
    lines = [f"{prefix} managed dependencies:"]
    if not items:
        lines.append("- none")
    for item in items:
        lines.append(f"- {item['label']}: {item.get('path') or item['target']}")
    for item in result["skipped"]:
        lines.append(f"- skipped {item['id']}: {item['reason']}")
    return "\n".join(lines)


def update_tools_config(config_path: Path, replacements: dict[str, str]) -> None:
    path = Path(config_path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    output: list[str] = []
    in_tools = False
    tools_seen = False
    written: set[str] = set()

    def write_missing() -> None:
        for key, value in replacements.items():
            if key not in written:
                output.append(f"{key} = {_toml_string(value)}")
                written.add(key)

    for line in lines:
        section = re.match(r"\s*\[([^\]]+)]\s*$", line)
        if section:
            if in_tools:
                write_missing()
            in_tools = section.group(1).strip() == "tools"
            tools_seen = tools_seen or in_tools
            output.append(line)
            continue

        if in_tools:
            key_match = re.match(r"\s*([A-Za-z0-9_-]+)\s*=", line)
            if key_match:
                key = key_match.group(1)
                if key in replacements:
                    output.append(f"{key} = {_toml_string(replacements[key])}")
                    written.add(key)
                    continue
        output.append(line)

    if in_tools:
        write_missing()
    if not tools_seen:
        output.extend(["", "[tools]"])
        write_missing()
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def _tool_definitions(config: AppConfig) -> list[ToolDefinition]:
    tools_dir = _tools_dir(config)
    return [
        ToolDefinition(
            id="yt-dlp",
            label="yt-dlp",
            config_key="yt_dlp",
            configured=config.tools.yt_dlp,
            purpose="YouTube、B站、TikTok 列表解析和下载",
            installable=True,
            url="https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
            target=tools_dir / "yt-dlp" / "yt-dlp.exe",
            manual_action="可自动下载；也可以手动安装后在高级页填写路径。",
        ),
        ToolDefinition(
            id="ffmpeg",
            label="ffmpeg",
            config_key="ffmpeg",
            configured=config.tools.ffmpeg,
            purpose="视频、音频处理和转写前处理",
            installable=True,
            url="https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
            target=tools_dir / "ffmpeg" / "bin" / "ffmpeg.exe",
            manual_action="可自动下载；也可以手动安装后在高级页填写路径。",
        ),
        ToolDefinition(
            id="douyin-downloader",
            label="抖音下载器",
            config_key="douyin_downloader",
            configured=config.tools.douyin_downloader,
            purpose="抖音收藏夹导出和下载",
            installable=False,
            url="",
            target=tools_dir / "douyin" / "douyin-dl.exe",
            manual_action="需要按项目说明安装 douyin-dl，或在高级页填写已有路径。",
        ),
        ToolDefinition(
            id="whisper",
            label="Whisper",
            config_key="whisper",
            configured=config.tools.whisper,
            purpose="本地音视频转文字",
            installable=False,
            url="",
            target=tools_dir / "whisper" / "whisper.exe",
            manual_action="转写模型体积较大，建议按需要手动安装 Whisper 或改用已有转写服务。",
        ),
        ToolDefinition(
            id="funasr",
            label="FunASR",
            config_key="funasr",
            configured=config.tools.funasr,
            purpose="中文音视频转文字的可选引擎",
            installable=False,
            url="",
            target=tools_dir / "funasr" / "funasr.exe",
            manual_action="FunASR 为可选转写引擎，按需要手动安装后填写路径。",
        ),
        ToolDefinition(
            id="ocr",
            label="OCR 命令",
            config_key="ocr",
            configured=config.tools.ocr,
            purpose="图片文字识别；留空时图片会作为待识别素材入库",
            installable=False,
            url="",
            target=tools_dir / "ocr" / "ocr.exe",
            manual_action="默认 builtin 会自动尝试本机 OCR 引擎；也可填写任意能把图片路径转成 stdout 文本的 OCR 命令。",
        ),
    ]


def _install_tool(definition: ToolDefinition, downloader: Downloader) -> Path:
    definition.target.parent.mkdir(parents=True, exist_ok=True)
    if definition.id == "ffmpeg":
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "ffmpeg.zip"
            downloader(definition.url, archive)
            _extract_ffmpeg(archive, definition.target.parent)
        if not definition.target.is_file():
            raise FileNotFoundError("ffmpeg.exe was not found after extraction")
        return definition.target

    downloader(definition.url, definition.target)
    if not definition.target.is_file():
        raise FileNotFoundError(f"{definition.target} was not downloaded")
    return definition.target


def _extract_ffmpeg(archive: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zip_file:
        for member in zip_file.infolist():
            normalized = member.filename.replace("\\", "/")
            if normalized.endswith("/bin/ffmpeg.exe"):
                (target_dir / "ffmpeg.exe").write_bytes(zip_file.read(member))
            elif normalized.endswith("/bin/ffprobe.exe"):
                (target_dir / "ffprobe.exe").write_bytes(zip_file.read(member))


def _download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Obsidian-Ingest-Studio"})
    with urllib.request.urlopen(request, timeout=120) as response:
        target.write_bytes(response.read())


def _resolve_command(command: str) -> str | None:
    if not command.strip():
        return None
    return shutil.which(command)


def _tools_dir(config: AppConfig) -> Path:
    return config.config_path.parent / "tools"


def _is_windows() -> bool:
    return os.name == "nt"


def _toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
