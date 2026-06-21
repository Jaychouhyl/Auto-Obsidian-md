import { invoke } from "@tauri-apps/api/core";
import type { CommandResult, LogFile, QueueItem, QueueStatus, StatusPayload } from "./types";

export async function getStatus(): Promise<StatusPayload> {
  return invoke<StatusPayload>("get_status");
}

export async function getQueue(limit = 50, status: QueueStatus = "all"): Promise<QueueItem[]> {
  const payload = await invoke<{ items: QueueItem[] }>("get_queue", { limit, status });
  return payload.items;
}

export async function runDoctor(): Promise<CommandResult> {
  return invoke<CommandResult>("run_doctor");
}

export async function collectDouyin(count: number): Promise<CommandResult> {
  return invoke<CommandResult>("collect_douyin", { count });
}

export async function scanInbox(): Promise<CommandResult> {
  return invoke<CommandResult>("scan_inbox");
}

export async function scanDirectory(directory: string): Promise<CommandResult> {
  return invoke<CommandResult>("scan_directory", { directory });
}

export async function collectRss(limit: number): Promise<CommandResult> {
  return invoke<CommandResult>("collect_rss", { limit });
}

export async function clipWebpage(url: string): Promise<CommandResult> {
  return invoke<CommandResult>("clip_webpage", { url });
}

export async function collectPlatformList(url: string, platform: string, limit: number): Promise<CommandResult> {
  return invoke<CommandResult>("collect_platform_list", { url, platform, limit });
}

export async function importLinks(): Promise<CommandResult> {
  return invoke<CommandResult>("import_links");
}

export async function processQueue(limit: number): Promise<CommandResult> {
  return invoke<CommandResult>("process_queue", { limit });
}

export async function retryItem(id: number): Promise<CommandResult> {
  return invoke<CommandResult>("retry_item", { id });
}

export async function retryFailed(limit: number): Promise<CommandResult> {
  return invoke<CommandResult>("retry_failed", { limit });
}

export async function skipItem(id: number, reason: string): Promise<CommandResult> {
  return invoke<CommandResult>("skip_item", { id, reason });
}

export async function knowledgeMaintenance(): Promise<CommandResult> {
  return invoke<CommandResult>("knowledge_maintenance");
}

export async function writeLauncher(): Promise<CommandResult> {
  return invoke<CommandResult>("write_launcher");
}

export async function listRecentLogs(limit = 20): Promise<LogFile[]> {
  return invoke<LogFile[]>("list_recent_logs", { limit });
}
