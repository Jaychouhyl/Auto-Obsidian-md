from __future__ import annotations

import shutil
import subprocess
import re
from dataclasses import dataclass
from pathlib import Path

TEXT_EXTENSIONS = {".txt", ".md", ".srt", ".vtt"}
MEDIA_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".mkv", ".webm", ".mov", ".flac", ".ogg"}


@dataclass(frozen=True)
class AcquisitionRequest:
    url: str
    platform: str
    output_dir: Path
    title: str | None = None


@dataclass(frozen=True)
class AcquisitionResult:
    status: str
    media_path: Path | None
    transcript_hint: str
    notes: list[str]


def build_acquisition_command(
    request: AcquisitionRequest,
    yt_dlp_cmd: str = "yt-dlp",
    douyin_cmd: str = "douyin-downloader",
    douyin_config: str = "",
    cookies_file: Path | None = None,
) -> list[str] | None:
    if request.platform == "douyin":
        command = [
            douyin_cmd,
            "-u",
            request.url,
            "-p",
            str(request.output_dir),
        ]
        if douyin_config:
            command.extend(["-c", douyin_config])
        return command
    if request.platform in {"youtube", "bilibili", "tiktok", "web"}:
        command = [
            yt_dlp_cmd,
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs",
            "zh.*,en.*",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "-o",
            str(request.output_dir / "%(title).120s.%(ext)s"),
        ]
        if cookies_file is not None:
            command.extend(["--cookies", str(cookies_file)])
        command.append(request.url)
        return command
    return None


def acquire_source(
    request: AcquisitionRequest,
    yt_dlp_cmd: str = "yt-dlp",
    douyin_cmd: str = "douyin-downloader",
    douyin_config: str = "",
    cookies_file: Path | None = None,
    dry_run_missing_tools: bool = True,
) -> AcquisitionResult:
    request.output_dir.mkdir(parents=True, exist_ok=True)

    if request.platform == "local_file":
        path = Path(request.url)
        if path.exists() and path.suffix.lower() in TEXT_EXTENSIONS:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if path.suffix.lower() in {".srt", ".vtt"}:
                text = _clean_subtitle_text(text)
            return AcquisitionResult(
                status="local_text",
                media_path=None,
                transcript_hint=text,
                notes=[f"已读取本地文本导出: {path}"],
            )
        if path.exists() and path.suffix.lower() == ".pdf":
            text, notes = _read_pdf_text(path)
            return AcquisitionResult(
                status="local_pdf",
                media_path=None,
                transcript_hint=text or f"本地 PDF: {request.url}",
                notes=notes,
            )
        return AcquisitionResult(
            status="local_file",
            media_path=path if path.exists() and path.suffix.lower() in MEDIA_EXTENSIONS else None,
            transcript_hint=f"本地文件: {request.url}",
            notes=[] if path.exists() else [f"本地文件不存在: {request.url}"],
        )

    command = build_acquisition_command(
        request,
        yt_dlp_cmd=yt_dlp_cmd,
        douyin_cmd=douyin_cmd,
        douyin_config=douyin_config,
        cookies_file=cookies_file,
    )
    executable = command[0] if command else None
    if not command or not executable or shutil.which(executable) is None:
        if dry_run_missing_tools:
            return AcquisitionResult(
                status="metadata_only",
                media_path=None,
                transcript_hint=f"未下载内容。来源链接: {request.url}",
                notes=[f"缺少下载工具或不支持平台: {request.platform}"],
            )
        raise FileNotFoundError(f"Missing acquisition tool for platform {request.platform}: {executable}")

    before = set(request.output_dir.glob("*"))
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if completed.returncode != 0:
        return AcquisitionResult(
            status="failed",
            media_path=None,
            transcript_hint=f"下载失败。来源链接: {request.url}",
            notes=[completed.stderr.strip() or completed.stdout.strip() or "下载命令失败"],
        )

    after = set(request.output_dir.glob("*"))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    media = next((p for p in new_files if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".mp4", ".mkv", ".webm"}), None)
    transcript = _read_first_text(new_files)
    return AcquisitionResult(
        status="downloaded",
        media_path=media,
        transcript_hint=transcript or f"已下载内容。来源链接: {request.url}",
        notes=[],
    )


def _read_first_text(paths: list[Path]) -> str:
    for path in paths:
        if path.suffix.lower() in {".srt", ".vtt", ".txt"}:
            try:
                return path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
    return ""


def _read_pdf_text(path: Path) -> tuple[str, list[str]]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return "", ["缺少 pypdf，无法提取 PDF 文本。"]

    try:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(page.strip() for page in pages if page.strip())
        return text, [f"已提取 PDF 文本: {path}"] if text else [f"PDF 未提取到文本: {path}"]
    except Exception as exc:
        return "", [f"PDF 提取失败: {exc}"]


def _clean_subtitle_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper() == "WEBVTT":
            continue
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        line = re.sub(r"^\d{1,2}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?\s+", "", line).strip()
        if not line:
            continue
        lines.append(line)
    return "\n".join(lines)
