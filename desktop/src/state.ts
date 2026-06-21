import type { AppState } from "./types";

export const state: AppState = {
  activeView: "run",
  status: null,
  queue: [],
  logs: [],
  busy: false,
  message: "",
  error: "",
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
