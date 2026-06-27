export type QueueCounts = Record<string, number>;
export type QueueStatus = "all" | "pending" | "processing" | "done" | "failed" | "skipped";
export type AccountPlatform = "douyin" | "bilibili" | "youtube" | "tiktok";
export type AccountStatus = "active" | "expired" | "unknown" | "error";

export interface AccountProfile {
  id: string;
  platform: AccountPlatform;
  display_name: string;
  platform_user_id: string;
  profile_dir: string;
  status: AccountStatus;
  created_at: string;
  updated_at: string;
  last_verified_at: string;
  error: string;
  is_current: boolean;
}

export interface AccountCandidate {
  candidate_id: string;
  platform: AccountPlatform;
  display_name: string;
  platform_user_id: string;
  source_url: string;
  created_at: string;
  replaces_account_id?: string;
}

export interface AccountsPayload {
  status: string;
  accounts: AccountProfile[];
}

export interface StatusPayload {
  paths: {
    project_root: string;
    queue_db: string;
    cache_dir: string;
    obsidian_vault: string;
    obsidian_folder: string;
  };
  queue: QueueCounts;
  routing: {
    enabled: boolean;
    fallback_folder: string;
    allowed_folders: string[];
  };
  obsidian: {
    mode: string;
    rest_base_url: string;
    rest_api_key_configured: boolean;
  };
  tools: Record<string, string>;
  llm: {
    enabled: boolean;
    provider: string;
    base_url: string;
    model: string;
    language: string;
    api_key_configured: boolean;
  };
  outputs: {
    formats: string[];
    html_dir: string;
    csv_path: string;
    notion_configured: boolean;
    notion_database_id_configured: boolean;
    notion_token_configured: boolean;
    notion_title_property: string;
    notion_api_base: string;
  };
}

export interface QueueItem {
  id: number;
  url: string;
  title: string | null;
  platform: string;
  content_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  note_path: string | null;
  error: string | null;
}

export interface CommandResult {
  ok: boolean;
  code: number;
  stdout: string;
  stderr: string;
}

export interface ToolConfigDraft {
  yt_dlp: string;
  ffmpeg: string;
  douyin_downloader: string;
  douyin_config: string;
  whisper: string;
  funasr: string;
}

export interface OutputsConfigDraft {
  formats: string[];
  html_dir: string;
  csv_path: string;
  notion_token: string;
  notion_database_id: string;
  notion_title_property: string;
  notion_api_base: string;
}

export interface AppConfigDraft {
  queue_db: string;
  cache_dir: string;
  obsidian_mode: string;
  obsidian_vault: string;
  obsidian_folder: string;
  rest_base_url: string;
  rest_api_key: string;
  llm_enabled: boolean;
  llm_provider: string;
  llm_base_url: string;
  llm_api_key: string;
  llm_model: string;
  llm_language: string;
  routing_enabled: boolean;
  fallback_folder: string;
  allowed_folders: string[];
  tools: ToolConfigDraft;
  outputs: OutputsConfigDraft;
}

export interface SourceFiles {
  links: string;
  feeds: string;
}

export interface DoctorCheck {
  name: string;
  ok: boolean;
  detail: string;
  required: boolean;
}

export interface DoctorReport {
  ok: boolean;
  checks: DoctorCheck[];
}

export interface DependencyItem {
  id: string;
  label: string;
  status: "ready" | "missing";
  configured: string;
  resolved_path: string;
  installable: boolean;
  config_key: string;
  purpose: string;
  manual_action: string;
  managed_target: string;
}

export interface DependencyReport {
  status: string;
  tools_dir: string;
  items: DependencyItem[];
  summary: {
    ready: number;
    missing: number;
    installable_missing: number;
  };
  notes: string[];
}

export interface DependencyInstallResult {
  status: string;
  config_path: string;
  tools_dir: string;
  planned: Array<Record<string, string>>;
  installed: Array<Record<string, string>>;
  skipped: Array<Record<string, string>>;
  dry_run: boolean;
}

export interface LogFile {
  name: string;
  path: string;
  modified_unix: number;
}

export interface AppState {
  activeView: "setup" | "dependencies" | "run" | "accounts" | "sources" | "queue" | "rules" | "logs" | "knowledge" | "updates" | "settings";
  queueStatus: QueueStatus;
  status: StatusPayload | null;
  configDraft: AppConfigDraft | null;
  sourceFiles: SourceFiles;
  doctor: DoctorReport | null;
  dependencies: DependencyReport | null;
  queue: QueueItem[];
  logs: LogFile[];
  accounts: AccountProfile[];
  accountCandidate: AccountCandidate | null;
  busy: boolean;
  message: string;
  error: string;
  bannerDismissed: boolean;
  appVersion: string;
}
