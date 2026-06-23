export type QueueCounts = Record<string, number>;
export type QueueStatus = "all" | "pending" | "processing" | "done" | "failed" | "skipped";

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

export interface LogFile {
  name: string;
  path: string;
  modified_unix: number;
}

export interface AppState {
  activeView: "setup" | "run" | "sources" | "queue" | "rules" | "logs" | "knowledge" | "updates" | "settings";
  queueStatus: QueueStatus;
  status: StatusPayload | null;
  configDraft: AppConfigDraft | null;
  sourceFiles: SourceFiles;
  doctor: DoctorReport | null;
  queue: QueueItem[];
  logs: LogFile[];
  busy: boolean;
  message: string;
  error: string;
  bannerDismissed: boolean;
  appVersion: string;
}
