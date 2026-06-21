from __future__ import annotations

import shutil
import subprocess
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    engine: str
    notes: list[str]


def build_transcription_command(
    media_path: Path,
    engine: str = "whisper",
    whisper_cmd: str = "whisper",
    funasr_cmd: str = "funasr",
    output_dir: Path | None = None,
) -> list[str]:
    if engine == "funasr":
        return [funasr_cmd, str(media_path)]
    directory = output_dir or media_path.parent
    return [
        whisper_cmd,
        str(media_path),
        "--model",
        "tiny",
        "--language",
        "Chinese",
        "--output_dir",
        str(directory),
        "--output_format",
        "txt",
        "--fp16",
        "False",
        "--verbose",
        "False",
    ]


def transcribe_source(
    media_path: Path | None,
    transcript_hint: str = "",
    engine: str = "whisper",
    whisper_cmd: str = "whisper",
    funasr_cmd: str = "funasr",
    dry_run_missing_tools: bool = True,
) -> TranscriptionResult:
    if transcript_hint and not media_path:
        return TranscriptionResult(transcript_hint, "hint", [])
    if not media_path:
        return TranscriptionResult("暂无可转写媒体。", "none", ["没有可转写的音频或视频文件"])

    executable = funasr_cmd if engine == "funasr" else whisper_cmd
    if shutil.which(executable) is None:
        if dry_run_missing_tools:
            text = transcript_hint or f"媒体已获取但缺少转写工具: {media_path}"
            return TranscriptionResult(text, "hint", [f"缺少转写工具: {executable}"])
        raise FileNotFoundError(f"Missing transcription tool: {executable}")

    command = build_transcription_command(media_path, engine=engine, whisper_cmd=whisper_cmd, funasr_cmd=funasr_cmd)
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        return TranscriptionResult(
            transcript_hint or completed.stderr.strip() or "转写失败。",
            engine,
            [completed.stderr.strip() or completed.stdout.strip() or "转写命令失败"],
        )

    txt_path = media_path.with_suffix(".txt")
    if txt_path.exists():
        return TranscriptionResult(txt_path.read_text(encoding="utf-8", errors="ignore"), engine, [])
    return TranscriptionResult(completed.stdout.strip() or transcript_hint, engine, [])
