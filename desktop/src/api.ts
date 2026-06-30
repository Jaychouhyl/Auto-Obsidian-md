import { invoke } from "@tauri-apps/api/core";
import type {
  AccountCandidate,
  AccountPlatform,
  AccountProfile,
  AccountsPayload,
  AppConfigDraft,
  CommandResult,
  DependencyInstallResult,
  DependencyReport,
  DoctorReport,
  LogFile,
  QueueItem,
  QueueStatus,
  SourceFiles,
  StatusPayload,
} from "./types";

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

export async function runDoctorJson(): Promise<DoctorReport> {
  return invoke<DoctorReport>("run_doctor_json");
}

export async function getDependencies(): Promise<DependencyReport> {
  return invoke<DependencyReport>("get_dependencies");
}

export async function installDependencies(tools: string[]): Promise<DependencyInstallResult> {
  return invoke<DependencyInstallResult>("install_dependencies", { tools });
}

export async function getAppConfig(): Promise<StatusPayload> {
  return invoke<StatusPayload>("get_app_config");
}

export async function saveAppConfig(draft: AppConfigDraft): Promise<CommandResult> {
  return invoke<CommandResult>("save_app_config", { draft });
}

export async function openPath(path: string): Promise<CommandResult> {
  return invoke<CommandResult>("open_path", { path });
}

export async function chooseDirectory(current: string): Promise<string | null> {
  return invoke<string | null>("choose_directory", { current });
}

export async function chooseBackupFile(current: string): Promise<string | null> {
  return invoke<string | null>("choose_backup_file", { current });
}

export async function openUrl(url: string): Promise<CommandResult> {
  return invoke<CommandResult>("open_url", { url });
}

export async function openOutput(kind: string): Promise<CommandResult> {
  return invoke<CommandResult>("open_output", { kind });
}

export async function backupProject(): Promise<CommandResult> {
  return invoke<CommandResult>("backup_project");
}

export async function restoreProject(backupFile: string): Promise<CommandResult> {
  return invoke<CommandResult>("restore_project", { backupFile });
}

export async function getSourceFiles(): Promise<SourceFiles> {
  return invoke<SourceFiles>("get_source_files");
}

export async function saveSourceFiles(links: string, feeds: string): Promise<CommandResult> {
  return invoke<CommandResult>("save_source_files", { links, feeds });
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

export async function getAccounts(): Promise<AccountsPayload> {
  return invoke<AccountsPayload>("get_accounts");
}

export async function startAccountLogin(platform: AccountPlatform): Promise<{ status: string; candidate: AccountCandidate }> {
  return invoke("start_account_login", { platform });
}

export async function confirmAccountLogin(
  candidateId: string,
  makeCurrent: boolean,
): Promise<{ status: string; account: AccountProfile }> {
  return invoke("confirm_account_login", { candidateId, makeCurrent });
}

export async function cancelAccountLogin(candidateId: string): Promise<{ status: string }> {
  return invoke("cancel_account_login", { candidateId });
}

export async function switchAccount(
  platform: AccountPlatform,
  accountId: string,
): Promise<{ status: string; account: AccountProfile }> {
  return invoke("switch_account", { platform, accountId });
}

export async function verifyAccount(accountId: string): Promise<{ status: string; account: AccountProfile }> {
  return invoke("verify_account", { accountId });
}

export async function reloginAccount(accountId: string): Promise<{ status: string; candidate: AccountCandidate }> {
  return invoke("relogin_account", { accountId });
}

export async function deleteAccount(accountId: string): Promise<{ status: string }> {
  return invoke("delete_account", { accountId });
}
