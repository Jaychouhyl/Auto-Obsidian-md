from __future__ import annotations

from dataclasses import dataclass

from .config import AppConfig, tool_available


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def run_doctor(config: AppConfig) -> list[DoctorCheck]:
    checks = [
        DoctorCheck("config", config.config_path.exists(), str(config.config_path)),
        DoctorCheck("queue_db_parent", config.paths.queue_db.parent.exists(), str(config.paths.queue_db.parent)),
        DoctorCheck("cache_dir", config.paths.cache_dir.exists(), str(config.paths.cache_dir)),
        DoctorCheck("obsidian_mode", config.obsidian.mode in {"local", "rest"}, config.obsidian.mode),
        DoctorCheck("obsidian_vault", config.obsidian.vault_path.exists() or config.obsidian.mode == "rest", str(config.obsidian.vault_path)),
    ]
    for name, command in {
        "yt-dlp": config.tools.yt_dlp,
        "ffmpeg": config.tools.ffmpeg,
        "douyin-downloader": config.tools.douyin_downloader,
        "whisper": config.tools.whisper,
        "funasr": config.tools.funasr,
    }.items():
        checks.append(DoctorCheck(name, tool_available(command), command))
    if config.llm.enabled:
        llm_detail = "configured" if config.llm.api_key else "missing; set DEEPSEEK_API_KEY or api_key"
    else:
        llm_detail = "disabled"
    checks.append(DoctorCheck("llm_api_key", (not config.llm.enabled) or bool(config.llm.api_key), llm_detail))
    checks.append(DoctorCheck("obsidian_rest_key", config.obsidian.mode != "rest" or bool(config.obsidian.rest_api_key), "required only in rest mode"))
    return checks


def format_doctor(checks: list[DoctorCheck]) -> str:
    lines = ["Doctor checks:"]
    for check in checks:
        marker = "OK" if check.ok else "WARN"
        lines.append(f"- [{marker}] {check.name}: {check.detail}")
    return "\n".join(lines)
