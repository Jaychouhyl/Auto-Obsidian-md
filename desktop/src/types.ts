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
  tools: Record<string, string>;
  llm: {
    enabled: boolean;
    provider: string;
    base_url: string;
    model: string;
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

export interface LogFile {
  name: string;
  path: string;
  modified_unix: number;
}

export interface AppState {
  activeView: "run" | "sources" | "queue" | "logs" | "knowledge" | "settings";
  queueStatus: QueueStatus;
  status: StatusPayload | null;
  queue: QueueItem[];
  logs: LogFile[];
  busy: boolean;
  message: string;
  error: string;
}
