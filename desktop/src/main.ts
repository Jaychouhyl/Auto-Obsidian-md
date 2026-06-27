import "./styles.css";
import { getVersion } from "@tauri-apps/api/app";
import {
  cancelAccountLogin,
  clipWebpage,
  collectPlatformList,
  collectRss,
  collectDouyin,
  confirmAccountLogin,
  deleteAccount,
  getAccounts,
  getDependencies,
  getQueue,
  getSourceFiles,
  getStatus,
  installDependencies,
  importLinks,
  knowledgeMaintenance,
  listRecentLogs,
  processQueue,
  reloginAccount,
  retryFailed,
  retryItem,
  runDoctor,
  runDoctorJson,
  saveAppConfig,
  saveSourceFiles,
  scanDirectory,
  scanInbox,
  skipItem,
  startAccountLogin,
  switchAccount,
  verifyAccount,
  writeLauncher,
} from "./api";
import { state, setBusy, setError, setMessage } from "./state";
import type {
  AccountPlatform,
  AccountProfile,
  AppConfigDraft,
  CommandResult,
  QueueStatus,
  StatusPayload,
} from "./types";

const appRoot = document.querySelector<HTMLDivElement>("#app");

if (!appRoot) {
  throw new Error("missing #app root");
}

const app = appRoot;

async function refresh(): Promise<void> {
  try {
    const status = await getStatus();
    state.status = status;
    state.configDraft = draftFromStatus(status);
    state.dependencies = await getDependencies();
    state.sourceFiles = await getSourceFiles();
    state.queue = await getQueue(80, state.queueStatus);
    state.logs = await listRecentLogs(30);
    state.accounts = (await getAccounts()).accounts;
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  }
  render();
}

async function loadDoctorSilently(): Promise<void> {
  try {
    state.doctor = await runDoctorJson();
  } catch {
    // 自检失败不阻塞界面；横幅仅在有结果且存在问题时显示
  }
}

async function init(): Promise<void> {
  try {
    state.appVersion = await getVersion();
  } catch {
    // 取不到版本号时留空，更新页显示“未知”
  }
  await refresh();
  await loadDoctorSilently();
  render();
}

function draftFromStatus(status: StatusPayload): AppConfigDraft {
  const tools = status.tools ?? {};
  return {
    queue_db: status.paths.queue_db,
    cache_dir: status.paths.cache_dir,
    obsidian_mode: status.obsidian.mode,
    obsidian_vault: status.paths.obsidian_vault,
    obsidian_folder: status.paths.obsidian_folder,
    rest_base_url: status.obsidian.rest_base_url,
    rest_api_key: "",
    llm_enabled: status.llm.enabled,
    llm_provider: status.llm.provider,
    llm_base_url: status.llm.base_url,
    llm_api_key: "",
    llm_model: status.llm.model,
    llm_language: status.llm.language,
    routing_enabled: status.routing.enabled,
    fallback_folder: status.routing.fallback_folder,
    allowed_folders: status.routing.allowed_folders,
    tools: {
      yt_dlp: tools.yt_dlp ?? "yt-dlp",
      ffmpeg: tools.ffmpeg ?? "ffmpeg",
      douyin_downloader: tools.douyin_downloader ?? "douyin-dl",
      douyin_config: tools.douyin_config ?? "",
      whisper: tools.whisper ?? "whisper",
      funasr: tools.funasr ?? "funasr",
    },
  };
}

async function runAction(label: string, action: () => Promise<CommandResult>): Promise<void> {
  setBusy(true);
  setMessage(`${label} 运行中...`);
  render();
  try {
    const result = await action();
    if (!result.ok) {
      setError(result.stderr || result.stdout || `${label} 失败`);
    } else {
      setMessage(result.stdout || `${label} 完成`);
    }
    await reloadData();
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    render();
  }
}

async function reloadData(): Promise<void> {
  const status = await getStatus();
  state.status = status;
  state.configDraft = draftFromStatus(status);
  state.dependencies = await getDependencies();
  state.sourceFiles = await getSourceFiles();
  state.queue = await getQueue(80, state.queueStatus);
  state.logs = await listRecentLogs(30);
  state.accounts = (await getAccounts()).accounts;
}

function numberFromInput(id: string, fallback: number, min: number, max: number): number | null {
  const element = document.querySelector<HTMLInputElement>(`#${id}`);
  const value = Number.parseInt(element?.value ?? String(fallback), 10);
  if (!Number.isFinite(value) || value < min || value > max) {
    setError(`请输入 ${min} 到 ${max} 之间的整数。`);
    render();
    return null;
  }
  return value;
}

function stringFromInput(id: string): string {
  return document.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(`#${id}`)?.value.trim() ?? "";
}

function boolFromInput(id: string, fallback: boolean): boolean {
  const element = document.querySelector<HTMLInputElement>(`#${id}`);
  if (!element) return fallback;
  if (element.type === "checkbox") return element.checked;
  return ["1", "true", "on", "yes"].includes(element.value.toLowerCase());
}

function foldersFromText(value: string): string[] {
  return value
    .split(/\r?\n|[,，]/)
    .map((item) => item.trim().replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""))
    .filter(Boolean)
    .filter((item, index, array) => array.indexOf(item) === index);
}

function buildDraftFromForm(): AppConfigDraft {
  const base = state.configDraft ?? draftFromStatus(state.status as StatusPayload);
  return {
    ...base,
    queue_db: stringFromInput("cfg-queue-db") || base.queue_db,
    cache_dir: stringFromInput("cfg-cache-dir") || base.cache_dir,
    obsidian_mode: stringFromInput("cfg-obsidian-mode") || base.obsidian_mode,
    obsidian_vault: stringFromInput("cfg-vault") || base.obsidian_vault,
    obsidian_folder: stringFromInput("cfg-folder") || base.obsidian_folder,
    rest_base_url: stringFromInput("cfg-rest-url") || base.rest_base_url,
    rest_api_key: stringFromInput("cfg-rest-key"),
    llm_enabled: boolFromInput("cfg-llm-enabled", base.llm_enabled),
    llm_provider: stringFromInput("cfg-llm-provider") || base.llm_provider,
    llm_base_url: stringFromInput("cfg-llm-base") || base.llm_base_url,
    llm_api_key: stringFromInput("cfg-llm-key"),
    llm_model: stringFromInput("cfg-llm-model") || base.llm_model,
    llm_language: stringFromInput("cfg-llm-language") || base.llm_language,
    routing_enabled: boolFromInput("cfg-routing-enabled", base.routing_enabled),
    fallback_folder: stringFromInput("cfg-fallback") || base.fallback_folder,
    allowed_folders: foldersFromText(stringFromInput("cfg-folders")).length
      ? foldersFromText(stringFromInput("cfg-folders"))
      : base.allowed_folders,
    tools: {
      yt_dlp: stringFromInput("cfg-yt-dlp") || base.tools.yt_dlp,
      ffmpeg: stringFromInput("cfg-ffmpeg") || base.tools.ffmpeg,
      douyin_downloader: stringFromInput("cfg-douyin-downloader") || base.tools.douyin_downloader,
      douyin_config: stringFromInput("cfg-douyin-config"),
      whisper: stringFromInput("cfg-whisper") || base.tools.whisper,
      funasr: stringFromInput("cfg-funasr") || base.tools.funasr,
    },
  };
}

async function handleSaveConfig(): Promise<void> {
  await runAction("保存配置", () => saveAppConfig(buildDraftFromForm()));
  await loadDoctorSilently();
  render();
}

async function handleDoctorJson(): Promise<void> {
  setBusy(true);
  setMessage("健康检查运行中...");
  render();
  try {
    state.doctor = await runDoctorJson();
    setMessage(state.doctor.ok ? "健康检查通过" : "健康检查有警告");
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    render();
  }
}

async function handleInstallDependencies(): Promise<void> {
  const installable = state.dependencies?.items
    .filter((item) => item.status !== "ready" && item.installable)
    .map((item) => item.id) ?? [];
  if (!installable.length) {
    setMessage("没有可自动安装的缺失依赖。");
    render();
    return;
  }
  setBusy(true);
  setMessage("正在下载并配置依赖...");
  render();
  try {
    const result = await installDependencies(installable);
    const installed = result.installed.map((item) => `${item.label}: ${item.path}`).join("\n");
    setMessage(installed ? `依赖已配置：\n${installed}` : "依赖安装流程完成。");
    await reloadData();
    await loadDoctorSilently();
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    render();
  }
}

async function handleDouyin(): Promise<void> {
  const count = numberFromInput("douyin-count", 5, 1, 100);
  if (count === null) return;
  await runAction(`处理 ${count} 个抖音收藏`, async () => {
    const collect = await collectDouyin(count);
    if (!collect.ok) return collect;
    return processQueue(count);
  });
}

async function runAccountAction(label: string, action: () => Promise<void>): Promise<void> {
  setBusy(true);
  setMessage(`${label} 处理中...`);
  render();
  try {
    await action();
    setMessage(`${label} 完成`);
  } catch (error) {
    setError(readableError(error));
  } finally {
    try {
      state.accounts = (await getAccounts()).accounts;
    } catch {
      // 保留原错误，账号列表可由“刷新”重新加载
    }
    setBusy(false);
    render();
  }
}

async function handleAddAccount(platform: AccountPlatform): Promise<void> {
  await runAccountAction("登录账号", async () => {
    setMessage("Edge 登录窗口已打开，等待平台登录完成...");
    render();
    const payload = await startAccountLogin(platform);
    state.accountCandidate = payload.candidate;
    setMessage(`已识别账号：${payload.candidate.display_name}`);
  });
}

async function handleConfirmAccount(makeCurrent: boolean): Promise<void> {
  const candidate = state.accountCandidate;
  if (!candidate) return;
  await runAccountAction("保存账号", async () => {
    await confirmAccountLogin(candidate.candidate_id, makeCurrent);
    state.accountCandidate = null;
  });
}

async function handleCancelAccount(): Promise<void> {
  const candidate = state.accountCandidate;
  if (!candidate) return;
  await runAccountAction("取消登录", async () => {
    await cancelAccountLogin(candidate.candidate_id);
    state.accountCandidate = null;
  });
}

async function handleSwitchAccount(platform: AccountPlatform, accountId: string): Promise<void> {
  await runAccountAction("切换账号", async () => {
    await switchAccount(platform, accountId);
  });
}

async function handleVerifyAccount(accountId: string): Promise<void> {
  await runAccountAction("校验账号", async () => {
    const payload = await verifyAccount(accountId);
    if (payload.account.status !== "active") {
      throw new Error(payload.account.error || "账号登录态已失效，请重新登录。");
    }
  });
}

async function handleReloginAccount(accountId: string): Promise<void> {
  await runAccountAction("重新登录", async () => {
    setMessage("Edge 登录窗口已打开，等待平台登录完成...");
    render();
    const payload = await reloginAccount(accountId);
    state.accountCandidate = payload.candidate;
  });
}

async function handleDeleteAccount(accountId: string, displayName: string): Promise<void> {
  if (!window.confirm(`删除账号“${displayName}”及其本机登录资料？`)) return;
  await runAccountAction("删除账号", async () => {
    await deleteAccount(accountId);
  });
}

function readableError(error: unknown): string {
  const text = error instanceof Error ? error.message : String(error);
  try {
    const parsed = JSON.parse(text) as { error?: { message?: string } };
    return parsed.error?.message || text;
  } catch {
    return text;
  }
}

async function handleDirectoryScan(): Promise<void> {
  const directory = stringFromInput("directory-path");
  if (!directory) {
    setError("请填写目录路径。");
    render();
    return;
  }
  await runAction("扫描目录", () => scanDirectory(directory));
}

async function handleRss(): Promise<void> {
  const limit = numberFromInput("rss-limit", 10, 1, 100);
  if (limit === null) return;
  await runAction("导入 RSS", () => collectRss(limit));
}

async function handleWebpage(): Promise<void> {
  const url = stringFromInput("webpage-url");
  if (!url) {
    setError("请填写网页 URL。");
    render();
    return;
  }
  await runAction("网页剪藏", () => clipWebpage(url));
}

async function handlePlatformList(): Promise<void> {
  const platform = stringFromInput("platform-kind") || "auto";
  const url = stringFromInput("platform-url");
  const limit = numberFromInput("platform-limit", 20, 1, 200);
  if (!url || limit === null) {
    setError("请填写列表链接和数量。");
    render();
    return;
  }
  await runAction("导入平台列表", () => collectPlatformList(url, platform, limit));
}

async function handleSaveSources(): Promise<void> {
  await runAction("保存来源文件", () => saveSourceFiles(stringFromInput("links-text"), stringFromInput("feeds-text")));
}

async function handleImportLinks(): Promise<void> {
  await runAction("导入链接", async () => {
    const saved = await saveSourceFiles(stringFromInput("links-text"), stringFromInput("feeds-text"));
    if (!saved.ok) return saved;
    return importLinks();
  });
}

async function handleRetryFailed(): Promise<void> {
  const limit = numberFromInput("retry-limit", 20, 1, 200);
  if (limit === null) return;
  await runAction("重试失败项", () => retryFailed(limit));
}

async function handleRetryItem(id: number): Promise<void> {
  await runAction(`重试 #${id}`, () => retryItem(id));
}

async function handleSkipItem(id: number): Promise<void> {
  const reason = window.prompt("跳过原因", "manual skip")?.trim();
  if (!reason) return;
  await runAction(`跳过 #${id}`, () => skipItem(id, reason));
}

async function handleProcessQueue(): Promise<void> {
  const limit = numberFromInput("process-limit", 10, 1, 200);
  if (limit === null) return;
  await runAction("处理队列", () => processQueue(limit));
}

async function handleCheckUpdates(): Promise<void> {
  setBusy(true);
  setMessage("检查更新中...");
  render();
  try {
    const response = await fetch("https://api.github.com/repos/Jaychouhyl/Auto-Obsidian-md/releases/latest");
    if (!response.ok) {
      setMessage("当前没有可用发布版本。");
    } else {
      const payload = (await response.json()) as { tag_name?: string; html_url?: string; name?: string };
      const latest = (payload.tag_name || payload.name || "").replace(/^v/i, "");
      const current = state.appVersion;
      if (!latest) {
        setMessage("未能识别最新版本号。");
      } else if (!current) {
        setMessage(`最新版本：${latest}\n${payload.html_url || ""}`);
      } else if (compareVersions(current, latest) >= 0) {
        setMessage(`已是最新版本（当前 ${current}，最新 ${latest}）。`);
      } else {
        setMessage(`有新版本可更新：当前 ${current} → 最新 ${latest}\n${payload.html_url || ""}`);
      }
    }
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    render();
  }
}

function compareVersions(a: string, b: string): number {
  const pa = a.split(".").map((part) => Number.parseInt(part, 10) || 0);
  const pb = b.split(".").map((part) => Number.parseInt(part, 10) || 0);
  const length = Math.max(pa.length, pb.length);
  for (let i = 0; i < length; i += 1) {
    const da = pa[i] ?? 0;
    const db = pb[i] ?? 0;
    if (da !== db) return da < db ? -1 : 1;
  }
  return 0;
}

function setView(view: typeof state.activeView): void {
  state.activeView = view;
  render();
}

async function setQueueStatus(status: QueueStatus): Promise<void> {
  state.queueStatus = status;
  await refresh();
}

function renderNav(): string {
  const items: Array<[typeof state.activeView, string]> = [
    ["setup", "配置"],
    ["dependencies", "依赖"],
    ["run", "运行"],
    ["accounts", "账号"],
    ["sources", "导入"],
    ["queue", "队列"],
    ["rules", "规则"],
    ["logs", "日志"],
    ["knowledge", "知识库"],
    ["updates", "更新"],
    ["settings", "高级"],
  ];
  return items
    .map(
      ([key, label]) =>
        `<button class="nav-item ${state.activeView === key ? "active" : ""}" data-view="${key}">${label}</button>`,
    )
    .join("");
}

function renderView(): string {
  if (state.activeView === "setup") return renderSetupView();
  if (state.activeView === "dependencies") return renderDependenciesView();
  if (state.activeView === "run") return renderRunView();
  if (state.activeView === "accounts") return renderAccountsView();
  if (state.activeView === "sources") return renderSourcesView();
  if (state.activeView === "queue") return renderQueueView();
  if (state.activeView === "rules") return renderRulesView();
  if (state.activeView === "logs") return renderLogsView();
  if (state.activeView === "knowledge") return renderKnowledgeView();
  if (state.activeView === "updates") return renderUpdatesView();
  return renderSettingsView();
}

function renderSetupView(): string {
  const draft = state.configDraft;
  if (!draft) return renderLoadingView("配置");
  return `
    <section class="view">
      <div class="view-header">
        <h1>配置</h1>
        <div class="toolbar">
          <button id="save-config" ${disabledAttr()}>保存</button>
          <button id="doctor-json" ${disabledAttr()}>健康检查</button>
        </div>
      </div>
      <div class="form-grid">
        ${field("Vault", "cfg-vault", draft.obsidian_vault)}
        ${field("默认文件夹", "cfg-folder", draft.obsidian_folder)}
        ${field("队列数据库", "cfg-queue-db", draft.queue_db)}
        ${field("缓存目录", "cfg-cache-dir", draft.cache_dir)}
        ${checkbox("启用 LLM", "cfg-llm-enabled", draft.llm_enabled)}
        ${field("LLM Base URL", "cfg-llm-base", draft.llm_base_url)}
        ${field("LLM Model", "cfg-llm-model", draft.llm_model)}
        ${field("API Key", "cfg-llm-key", "", "password")}
      </div>
      ${renderDoctorReport()}
      ${renderMessageArea()}
    </section>
  `;
}

function renderDependenciesView(): string {
  const report = state.dependencies;
  if (!report) return renderLoadingView("依赖");
  const installableMissing = report.items.filter((item) => item.status !== "ready" && item.installable);
  return `
    <section class="view">
      <div class="view-header">
        <h1>依赖</h1>
        <div class="toolbar">
          <button id="install-dependencies" ${disabledAttr()} ${installableMissing.length ? "" : "disabled"}>安装缺失工具</button>
          <button id="refresh-dependencies" ${disabledAttr()}>重新检测</button>
        </div>
      </div>
      <div class="dependency-summary">
        <div><b>${report.summary.ready}</b><span>可用</span></div>
        <div><b>${report.summary.missing}</b><span>待处理</span></div>
        <div><b>${report.summary.installable_missing}</b><span>可自动安装</span></div>
      </div>
      <div class="dependency-grid">
        ${report.items.map(renderDependencyItem).join("")}
      </div>
      ${renderMessageArea()}
    </section>
  `;
}

function renderDependencyItem(item: { id: string; label: string; status: string; installable: boolean; purpose: string; resolved_path: string; configured: string; manual_action: string; managed_target: string }): string {
  const ready = item.status === "ready";
  const detail = item.resolved_path || item.configured || item.manual_action;
  return `
    <div class="dependency-item ${ready ? "ready" : "missing"}">
      <div class="dependency-head">
        <h2>${escapeHtml(item.label)}</h2>
        <span class="badge ${ready ? "done" : item.installable ? "pending" : "failed"}">${ready ? "可用" : item.installable ? "可安装" : "手动"}</span>
      </div>
      <p>${escapeHtml(item.purpose)}</p>
      <small>${escapeHtml(detail)}</small>
      ${!ready && item.installable ? `<small>将安装到：${escapeHtml(item.managed_target)}</small>` : ""}
    </div>
  `;
}

function renderRunView(): string {
  const counts = state.status?.queue ?? {};
  return `
    <section class="view">
      <div class="view-header">
        <h1>运行</h1>
        <button id="refresh" ${disabledAttr()}>刷新</button>
      </div>
      <div class="stats">
        <div class="stat"><b>${counts.pending ?? 0}</b><span>待处理</span></div>
        <div class="stat"><b>${counts.done ?? 0}</b><span>已完成</span></div>
        <div class="stat"><b>${counts.failed ?? 0}</b><span>失败</span></div>
      </div>
      ${renderAccountSummary(["douyin"])}
      <div class="control-band">
        ${field("处理数量", "process-limit", "10", "number")}
        <button id="process-queue" ${disabledAttr()}>处理队列</button>
        ${field("抖音数量", "douyin-count", "5", "number")}
        <button id="run-douyin" ${disabledAttr()}>处理抖音收藏</button>
        ${field("重试数量", "retry-limit", "20", "number")}
        <button id="retry-failed" ${disabledAttr()}>重试失败项</button>
        <button id="scan-inbox" ${disabledAttr()}>扫描 inbox</button>
      </div>
      ${renderMessageArea()}
    </section>
  `;
}

const PlatformDefinition: Record<AccountPlatform, { label: string; short: string }> = {
  douyin: { label: "抖音", short: "抖音收藏" },
  bilibili: { label: "哔哩哔哩", short: "B站列表" },
  youtube: { label: "YouTube", short: "YouTube 列表" },
  tiktok: { label: "TikTok", short: "TikTok 内容" },
};

function renderAccountsView(): string {
  const platforms = Object.keys(PlatformDefinition) as AccountPlatform[];
  return `
    <section class="view">
      <div class="view-header">
        <h1>账号</h1>
        <button id="refresh" ${disabledAttr()}>刷新</button>
      </div>
      <div class="account-platforms">
        ${platforms.map(renderAccountPlatform).join("")}
      </div>
      ${renderAccountCandidate()}
      ${renderMessageArea()}
    </section>
  `;
}

function renderAccountPlatform(platform: AccountPlatform): string {
  const definition = PlatformDefinition[platform];
  const accounts = state.accounts.filter((account) => account.platform === platform);
  return `
    <section class="account-platform">
      <div class="account-platform-head">
        <div>
          <h2>${escapeHtml(definition.label)}</h2>
          <span>${accounts.length} 个账号</span>
        </div>
        <button data-add-account="${platform}" ${disabledAttr()}>添加账号</button>
      </div>
      <div class="account-rows">
        ${
          accounts.length
            ? accounts.map(renderAccountRow).join("")
            : '<div class="account-empty">尚未添加账号</div>'
        }
      </div>
    </section>
  `;
}

function renderAccountRow(account: AccountProfile): string {
  const statusLabel = account.status === "active" ? "可用" : account.status === "expired" ? "已失效" : "待校验";
  return `
    <div class="account-row">
      <div class="account-identity">
        <div class="account-name">
          <b>${escapeHtml(account.display_name)}</b>
          ${account.is_current ? '<span class="badge current">当前</span>' : ""}
          <span class="badge ${escapeAttr(account.status)}">${statusLabel}</span>
        </div>
        <span>${escapeHtml(account.platform_user_id)}</span>
        ${account.error ? `<small>${escapeHtml(account.error)}</small>` : ""}
      </div>
      <div class="row-actions">
        ${account.is_current ? "" : `<button data-switch-account="${account.id}" data-platform="${account.platform}" ${disabledAttr()}>切换</button>`}
        <button data-verify-account="${account.id}" ${disabledAttr()}>校验</button>
        <button data-relogin-account="${account.id}" ${disabledAttr()}>重新登录</button>
        <button data-delete-account="${account.id}" data-account-name="${escapeAttr(account.display_name)}" ${disabledAttr()}>删除</button>
      </div>
    </div>
  `;
}

function renderAccountCandidate(): string {
  const candidate = state.accountCandidate;
  if (!candidate) return "";
  return `
    <section class="account-candidate">
      <div>
        <span class="candidate-label">检测到新账号</span>
        <h2>${escapeHtml(candidate.display_name)}</h2>
        <p>${escapeHtml(PlatformDefinition[candidate.platform].label)} · ${escapeHtml(candidate.platform_user_id)}</p>
      </div>
      <div class="toolbar">
        <button id="confirm-account-current" ${disabledAttr()}>保存并切换</button>
        <button id="confirm-account-only" ${disabledAttr()}>仅保存</button>
        <button id="cancel-account" ${disabledAttr()}>取消</button>
      </div>
    </section>
  `;
}

function renderAccountSummary(platforms: AccountPlatform[]): string {
  return `
    <div class="account-summary">
      ${platforms
        .map((platform) => {
          const account = state.accounts.find((item) => item.platform === platform && item.is_current);
          const stateText = account
            ? `${account.display_name} · ${account.status === "active" ? "可用" : "需重新登录"}`
            : "未设置";
          return `<div><span>${escapeHtml(PlatformDefinition[platform].short)}</span><b>${escapeHtml(stateText)}</b></div>`;
        })
        .join("")}
      <button data-view="accounts">管理账号</button>
    </div>
  `;
}

function renderSourcesView(): string {
  return `
    <section class="view">
      <div class="view-header">
        <h1>导入</h1>
        <button id="save-sources" ${disabledAttr()}>保存来源</button>
      </div>
      ${renderAccountSummary(["bilibili", "youtube", "tiktok"])}
      <div class="split">
        <div class="panel">
          <h2>链接</h2>
          <textarea id="links-text" rows="10">${escapeHtml(state.sourceFiles.links)}</textarea>
          <button id="run-links" ${disabledAttr()}>导入 links.txt</button>
        </div>
        <div class="panel">
          <h2>RSS</h2>
          <textarea id="feeds-text" rows="10">${escapeHtml(state.sourceFiles.feeds)}</textarea>
          <div class="inline-form">
            ${field("数量", "rss-limit", "10", "number")}
            <button id="run-rss" ${disabledAttr()}>导入 RSS</button>
          </div>
        </div>
      </div>
      <div class="form-grid">
        ${field("网页 URL", "webpage-url", "https://example.com/article")}
        <button id="clip-webpage" ${disabledAttr()}>网页剪藏</button>
        ${field("目录路径", "directory-path", "D:\\Downloads")}
        <button id="run-directory" ${disabledAttr()}>扫描目录</button>
        ${selectField("平台", "platform-kind", [["auto", "自动"], ["youtube", "YouTube"], ["bilibili", "B站"], ["tiktok", "TikTok"]])}
        ${field("列表链接", "platform-url", "")}
        ${field("列表数量", "platform-limit", "20", "number")}
        <button id="run-platform-list" ${disabledAttr()}>导入列表</button>
      </div>
      ${renderMessageArea()}
    </section>
  `;
}

function renderQueueView(): string {
  const filters: Array<[QueueStatus, string]> = [
    ["all", "全部"],
    ["pending", "待处理"],
    ["processing", "处理中"],
    ["failed", "失败"],
    ["done", "已完成"],
    ["skipped", "已跳过"],
  ];
  return `
    <section class="view">
      <div class="view-header">
        <h1>队列</h1>
        <div class="filters">
          ${filters
            .map(
              ([status, label]) =>
                `<button class="filter-button ${state.queueStatus === status ? "active" : ""}" data-queue-status="${status}">${label}</button>`,
            )
            .join("")}
        </div>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>ID</th><th>状态</th><th>标题</th><th>平台</th><th>错误 / 输出</th><th>操作</th></tr></thead>
          <tbody>
            ${
              state.queue.length
                ? state.queue.map(renderQueueRow).join("")
                : '<tr><td colspan="6" class="empty">当前筛选下没有队列项。</td></tr>'
            }
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderQueueRow(item: { id: number; status: string; title: string | null; url: string; platform: string; error: string | null; note_path: string | null }): string {
  return `<tr>
    <td>${item.id}</td>
    <td><span class="badge ${escapeAttr(item.status)}">${escapeHtml(item.status)}</span></td>
    <td>${escapeHtml(item.title ?? item.url)}</td>
    <td>${escapeHtml(item.platform)}</td>
    <td>${escapeHtml(item.error ?? item.note_path ?? "")}</td>
    <td class="row-actions">
      <button data-retry-id="${item.id}" ${disabledAttr()}>重试</button>
      <button data-skip-id="${item.id}" ${disabledAttr()}>跳过</button>
    </td>
  </tr>`;
}

function renderRulesView(): string {
  const draft = state.configDraft;
  if (!draft) return renderLoadingView("规则");
  return `
    <section class="view">
      <div class="view-header">
        <h1>规则</h1>
        <button id="save-config" ${disabledAttr()}>保存</button>
      </div>
      <div class="form-grid">
        ${checkbox("启用自动分类", "cfg-routing-enabled", draft.routing_enabled)}
        ${field("兜底文件夹", "cfg-fallback", draft.fallback_folder)}
      </div>
      <label class="field wide">
        <span>允许写入的文件夹</span>
        <textarea id="cfg-folders" rows="10">${escapeHtml(draft.allowed_folders.join("\n"))}</textarea>
      </label>
      ${hiddenAdvancedConfig(draft)}
      ${renderMessageArea()}
    </section>
  `;
}

function renderLogsView(): string {
  const rows = state.logs
    .map((log) => `<div class="log-row"><b>${escapeHtml(log.name)}</b><span>${escapeHtml(log.path)}</span></div>`)
    .join("");
  return `<section class="view"><h1>日志</h1>${rows || '<p class="muted">暂无日志文件。</p>'}</section>`;
}

function renderKnowledgeView(): string {
  return `
    <section class="view">
      <div class="view-header">
        <h1>知识库</h1>
        <button id="knowledge-maintenance" ${disabledAttr()}>生成报告</button>
      </div>
      <div class="settings">
        <p><b>输出目录：</b>${escapeHtml(state.status?.paths.obsidian_vault ?? "")}\\Obsidian Ingest Pipeline</p>
      </div>
      ${renderMessageArea()}
    </section>
  `;
}

function renderUpdatesView(): string {
  return `
    <section class="view">
      <div class="view-header">
        <h1>更新</h1>
        <button id="check-updates" ${disabledAttr()}>检查更新</button>
      </div>
      <div class="settings">
        <p><b>仓库：</b>Jaychouhyl/Auto-Obsidian-md</p>
        <p><b>当前版本：</b>${escapeHtml(state.appVersion || "未知")}</p>
      </div>
      ${renderMessageArea()}
    </section>
  `;
}

function renderSettingsView(): string {
  const draft = state.configDraft;
  if (!draft) return renderLoadingView("高级");
  return `
    <section class="view">
      <div class="view-header">
        <h1>高级</h1>
        <div class="toolbar">
          <button id="save-config" ${disabledAttr()}>保存</button>
          <button id="write-launcher" ${disabledAttr()}>生成启动器</button>
          <button id="doctor" ${disabledAttr()}>doctor</button>
        </div>
      </div>
      <div class="form-grid">
        ${selectField("写入模式", "cfg-obsidian-mode", [["local", "local"], ["rest", "rest"]], draft.obsidian_mode)}
        ${field("REST URL", "cfg-rest-url", draft.rest_base_url)}
        ${field("REST Key", "cfg-rest-key", draft.rest_api_key, "password")}
        ${field("yt-dlp", "cfg-yt-dlp", draft.tools.yt_dlp)}
        ${field("ffmpeg", "cfg-ffmpeg", draft.tools.ffmpeg)}
        ${field("douyin downloader", "cfg-douyin-downloader", draft.tools.douyin_downloader)}
        ${field("douyin config", "cfg-douyin-config", draft.tools.douyin_config)}
        ${field("whisper", "cfg-whisper", draft.tools.whisper)}
        ${field("funasr", "cfg-funasr", draft.tools.funasr)}
      </div>
      ${hiddenCoreConfig(draft)}
      ${renderMessageArea()}
    </section>
  `;
}

function hiddenAdvancedConfig(draft: AppConfigDraft): string {
  return `
    ${hidden("cfg-vault", draft.obsidian_vault)}
    ${hidden("cfg-folder", draft.obsidian_folder)}
    ${hidden("cfg-queue-db", draft.queue_db)}
    ${hidden("cfg-cache-dir", draft.cache_dir)}
    ${hidden("cfg-obsidian-mode", draft.obsidian_mode)}
    ${hidden("cfg-rest-url", draft.rest_base_url)}
    ${hidden("cfg-rest-key", draft.rest_api_key)}
    ${hidden("cfg-llm-provider", draft.llm_provider)}
    ${hidden("cfg-llm-base", draft.llm_base_url)}
    ${hidden("cfg-llm-key", "")}
    ${hidden("cfg-llm-model", draft.llm_model)}
    ${hidden("cfg-llm-language", draft.llm_language)}
    ${hidden("cfg-yt-dlp", draft.tools.yt_dlp)}
    ${hidden("cfg-ffmpeg", draft.tools.ffmpeg)}
    ${hidden("cfg-douyin-downloader", draft.tools.douyin_downloader)}
    ${hidden("cfg-douyin-config", draft.tools.douyin_config)}
    ${hidden("cfg-whisper", draft.tools.whisper)}
    ${hidden("cfg-funasr", draft.tools.funasr)}
  `;
}

function hiddenCoreConfig(draft: AppConfigDraft): string {
  return `
    ${hidden("cfg-vault", draft.obsidian_vault)}
    ${hidden("cfg-folder", draft.obsidian_folder)}
    ${hidden("cfg-queue-db", draft.queue_db)}
    ${hidden("cfg-cache-dir", draft.cache_dir)}
    ${hidden("cfg-llm-enabled", draft.llm_enabled ? "on" : "")}
    ${hidden("cfg-llm-provider", draft.llm_provider)}
    ${hidden("cfg-llm-base", draft.llm_base_url)}
    ${hidden("cfg-llm-key", "")}
    ${hidden("cfg-llm-model", draft.llm_model)}
    ${hidden("cfg-llm-language", draft.llm_language)}
    ${hidden("cfg-routing-enabled", draft.routing_enabled ? "on" : "")}
    ${hidden("cfg-fallback", draft.fallback_folder)}
    <textarea id="cfg-folders" hidden>${escapeHtml(draft.allowed_folders.join("\n"))}</textarea>
  `;
}

function renderDoctorReport(): string {
  if (!state.doctor) return "";
  return `<div class="doctor-grid">
    ${state.doctor.checks
      .map(
        (check) =>
          `<div class="doctor-row ${check.ok ? "ok" : check.required ? "bad" : "warn"}">
            <b>${escapeHtml(check.name)}</b>
            <span>${check.ok ? "OK" : check.required ? "FAIL" : "WARN"}</span>
            <small>${escapeHtml(check.detail)}</small>
          </div>`,
      )
      .join("")}
  </div>`;
}

function renderLoadingView(title: string): string {
  return `<section class="view"><h1>${title}</h1><p class="muted">Loading...</p>${renderMessageArea()}</section>`;
}

function renderMessageArea(): string {
  return `
    ${state.message ? `<pre class="message">${escapeHtml(state.message)}</pre>` : ""}
    ${state.error ? `<pre class="error">${escapeHtml(state.error)}</pre>` : ""}
  `;
}

function renderBanner(): string {
  if (state.bannerDismissed || !state.doctor) return "";
  const issues = state.doctor.checks.filter((check) => !check.ok);
  if (issues.length === 0) return "";
  const items = issues
    .map(
      (check) =>
        `<li class="${check.required ? "bad" : "warn"}"><b>${escapeHtml(check.name)}</b> — ${escapeHtml(check.detail)}</li>`,
    )
    .join("");
  return `
    <div class="banner">
      <div class="banner-head">
        <b>环境检查发现 ${issues.length} 项待处理</b>
        <span class="banner-actions">
          <button data-view="dependencies">去依赖</button>
          <button data-view="setup">去配置</button>
          <button id="dismiss-banner">关闭</button>
        </span>
      </div>
      <ul class="banner-list">${items}</ul>
      <small class="muted">缺失的下载 / 转写工具只影响视频处理；只做网页 / RSS / 本地文本入库可忽略。</small>
    </div>
  `;
}

function bindEvents(): void {
  document.querySelectorAll<HTMLButtonElement>("[data-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view as typeof state.activeView));
  });
  document.querySelectorAll<HTMLButtonElement>("[data-queue-status]").forEach((button) => {
    button.addEventListener("click", () => void setQueueStatus(button.dataset.queueStatus as QueueStatus));
  });
  document.querySelector<HTMLButtonElement>("#refresh")?.addEventListener("click", refresh);
  document.querySelector<HTMLButtonElement>("#refresh-dependencies")?.addEventListener("click", refresh);
  document.querySelector<HTMLButtonElement>("#save-config")?.addEventListener("click", () => void handleSaveConfig());
  document.querySelector<HTMLButtonElement>("#doctor-json")?.addEventListener("click", () => void handleDoctorJson());
  document.querySelector<HTMLButtonElement>("#install-dependencies")?.addEventListener("click", () => void handleInstallDependencies());
  document.querySelector<HTMLButtonElement>("#doctor")?.addEventListener("click", () => runAction("doctor", runDoctor));
  document.querySelector<HTMLButtonElement>("#run-douyin")?.addEventListener("click", () => void handleDouyin());
  document.querySelector<HTMLButtonElement>("#run-links")?.addEventListener("click", () => void handleImportLinks());
  document.querySelector<HTMLButtonElement>("#save-sources")?.addEventListener("click", () => void handleSaveSources());
  document.querySelector<HTMLButtonElement>("#scan-inbox")?.addEventListener("click", () => runAction("扫描 inbox", scanInbox));
  document.querySelector<HTMLButtonElement>("#run-directory")?.addEventListener("click", () => void handleDirectoryScan());
  document.querySelector<HTMLButtonElement>("#run-rss")?.addEventListener("click", () => void handleRss());
  document.querySelector<HTMLButtonElement>("#clip-webpage")?.addEventListener("click", () => void handleWebpage());
  document.querySelector<HTMLButtonElement>("#run-platform-list")?.addEventListener("click", () => void handlePlatformList());
  document.querySelector<HTMLButtonElement>("#process-queue")?.addEventListener("click", () => void handleProcessQueue());
  document.querySelector<HTMLButtonElement>("#retry-failed")?.addEventListener("click", () => void handleRetryFailed());
  document.querySelector<HTMLButtonElement>("#knowledge-maintenance")?.addEventListener("click", () => runAction("生成知识库报告", knowledgeMaintenance));
  document.querySelector<HTMLButtonElement>("#write-launcher")?.addEventListener("click", () => runAction("生成启动器", writeLauncher));
  document.querySelector<HTMLButtonElement>("#check-updates")?.addEventListener("click", () => void handleCheckUpdates());
  document.querySelector<HTMLButtonElement>("#dismiss-banner")?.addEventListener("click", () => {
    state.bannerDismissed = true;
    render();
  });
  document.querySelectorAll<HTMLButtonElement>("[data-add-account]").forEach((button) => {
    button.addEventListener("click", () => void handleAddAccount(button.dataset.addAccount as AccountPlatform));
  });
  document.querySelector<HTMLButtonElement>("#confirm-account-current")?.addEventListener("click", () => {
    void handleConfirmAccount(true);
  });
  document.querySelector<HTMLButtonElement>("#confirm-account-only")?.addEventListener("click", () => {
    void handleConfirmAccount(false);
  });
  document.querySelector<HTMLButtonElement>("#cancel-account")?.addEventListener("click", () => {
    void handleCancelAccount();
  });
  document.querySelectorAll<HTMLButtonElement>("[data-switch-account]").forEach((button) => {
    button.addEventListener("click", () => {
      void handleSwitchAccount(
        button.dataset.platform as AccountPlatform,
        button.dataset.switchAccount ?? "",
      );
    });
  });
  document.querySelectorAll<HTMLButtonElement>("[data-verify-account]").forEach((button) => {
    button.addEventListener("click", () => void handleVerifyAccount(button.dataset.verifyAccount ?? ""));
  });
  document.querySelectorAll<HTMLButtonElement>("[data-relogin-account]").forEach((button) => {
    button.addEventListener("click", () => void handleReloginAccount(button.dataset.reloginAccount ?? ""));
  });
  document.querySelectorAll<HTMLButtonElement>("[data-delete-account]").forEach((button) => {
    button.addEventListener("click", () => {
      void handleDeleteAccount(
        button.dataset.deleteAccount ?? "",
        button.dataset.accountName ?? "",
      );
    });
  });
  document.querySelectorAll<HTMLButtonElement>("[data-retry-id]").forEach((button) => {
    button.addEventListener("click", () => void handleRetryItem(Number.parseInt(button.dataset.retryId ?? "0", 10)));
  });
  document.querySelectorAll<HTMLButtonElement>("[data-skip-id]").forEach((button) => {
    button.addEventListener("click", () => void handleSkipItem(Number.parseInt(button.dataset.skipId ?? "0", 10)));
  });
}

function render(): void {
  app.innerHTML = `<div class="shell"><aside><div class="brand">Obsidian Ingest</div>${renderNav()}</aside><main>${renderBanner()}${renderView()}</main></div>`;
  bindEvents();
}

function disabledAttr(): string {
  return state.busy ? "disabled" : "";
}

function field(label: string, id: string, value: string, type = "text"): string {
  return `<label class="field"><span>${escapeHtml(label)}</span><input id="${id}" type="${type}" value="${escapeAttr(value)}" /></label>`;
}

function checkbox(label: string, id: string, checkedValue: boolean): string {
  return `<label class="field check"><input id="${id}" type="checkbox" ${checkedValue ? "checked" : ""} /><span>${escapeHtml(label)}</span></label>`;
}

function selectField(label: string, id: string, options: Array<[string, string]>, selected = ""): string {
  return `<label class="field"><span>${escapeHtml(label)}</span><select id="${id}">
    ${options.map(([value, text]) => `<option value="${escapeAttr(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(text)}</option>`).join("")}
  </select></label>`;
}

function hidden(id: string, value: string): string {
  return `<input id="${id}" type="hidden" value="${escapeAttr(value)}" />`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char] ?? char;
  });
}

function escapeAttr(value: string): string {
  return escapeHtml(value);
}

render();
void init();
