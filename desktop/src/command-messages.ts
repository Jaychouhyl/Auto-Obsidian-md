import type { CommandResult } from "./types";

export interface DouyinCollectStats {
  requested: number | null;
  returned: number | null;
  queued: number | null;
  attempts: number | null;
}

export function extractQueuedCount(stdout: string): number | null {
  try {
    const parsed = JSON.parse(stdout) as { queued?: unknown };
    const value = Number(parsed.queued);
    return Number.isFinite(value) ? value : null;
  } catch {
    const match = stdout.match(/queued["'\s:]+(\d+)/i);
    return match ? Number.parseInt(match[1], 10) : null;
  }
}

export function extractDouyinCollectStats(stdout: string): DouyinCollectStats {
  try {
    const parsed = JSON.parse(stdout) as Record<string, unknown>;
    return {
      requested: numericField(parsed.requested),
      returned: numericField(parsed.returned),
      queued: numericField(parsed.queued),
      attempts: numericField(parsed.attempts),
    };
  } catch {
    return { requested: null, returned: null, queued: extractQueuedCount(stdout), attempts: null };
  }
}

export function numericField(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function readableCommandSuccess(label: string, result: CommandResult): string {
  const payload = parseCommandJson(result.stdout);
  if (payload) {
    const queued = numericField(payload.queued);
    const retried = numericField(payload.retried);
    const totalNotes = numericField(payload.total_notes);
    const files = Array.isArray(payload.files) ? payload.files.length : null;
    const backupPath = typeof payload.backup_path === "string" ? payload.backup_path : "";
    if (queued !== null) return `${label} 完成，新增 ${queued} 个待处理任务。`;
    if (retried !== null) return `${label} 完成，已重试 ${retried} 个失败任务。`;
    if (totalNotes !== null) return `${label} 完成，检查了 ${totalNotes} 篇笔记。`;
    if (files !== null) return `${label} 完成，识别到 ${files} 个文件。`;
    if (typeof payload.launcher === "string") return `${label} 完成，启动器已生成。`;
    if (backupPath) return `${label} 完成，备份已创建：${backupPath}`;
    return `${label} 完成。`;
  }
  const text = result.stdout.trim();
  return text && text.length < 240 ? text : `${label} 完成。`;
}

export function readableCommandError(label: string, result: CommandResult): string {
  const text = result.stderr || result.stdout;
  const payload = parseCommandJson(text);
  if (payload) {
    const error = payload.error;
    if (typeof error === "string") return error;
    if (error && typeof error === "object" && "message" in error) {
      return String((error as { message?: unknown }).message || `${label} 失败`);
    }
  }
  const trimmed = text.trim();
  if (!trimmed) return `${label} 失败`;
  if (/api[_ -]?key/i.test(trimmed)) return `${label} 失败：API Key 缺失或不可用，请到配置页检查。`;
  if (/ffmpeg/i.test(trimmed)) return `${label} 失败：ffmpeg 不可用，请到依赖页安装或重新检测。`;
  if (/yt-dlp/i.test(trimmed)) return `${label} 失败：yt-dlp 不可用或下载失败，请到依赖页检查。`;
  if (/whisper|funasr/i.test(trimmed)) return `${label} 失败：转写工具不可用，请到依赖页检查 Whisper/FunASR。`;
  return trimmed;
}

export function parseCommandJson(text: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(text) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}
