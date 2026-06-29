import type { AppState } from "./types";

export const state: AppState = {
  activeView: "run",
  queueStatus: "all",
  status: null,
  configDraft: null,
  sourceFiles: {
    links: "",
    feeds: "",
  },
  doctor: null,
  dependencies: null,
  queue: [],
  logs: [],
  accounts: [],
  accountCandidate: null,
  busy: false,
  message: "",
  error: "",
  bannerDismissed: false,
  appVersion: "",
  latestRelease: null,
  progressSteps: [],
  savedTemplates: [],
  customSourcePlugins: [],
};

export function setBusy(value: boolean): void {
  state.busy = value;
}

export function setMessage(message: string): void {
  state.message = message;
  state.error = "";
}

export function setError(error: string): void {
  state.error = error;
  state.message = "";
}
