import "./styles.css";
import { getVersion } from "@tauri-apps/api/app";
import { getCurrentWindow } from "@tauri-apps/api/window";
import {
  backupProject,
  cancelAccountLogin,
  chooseBackupFile,
  chooseDirectory,
  clipWebpage,
  collectPlatformList,
  collectRss,
  collectDouyin,
  confirmAccountLogin,
  deleteAccount,
  exportDiagnostics,
  getAccounts,
  getDependencies,
  getQueue,
  getSourceFiles,
  getStatus,
  installDependencies,
  importLinks,
  knowledgeMaintenance,
  listRecentLogs,
  openOutput,
  openUrl,
  processQueue,
  reloginAccount,
  retryFailed,
  retryItem,
  restoreProject,
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
import {
  appBrandName,
  appBrandSubtitle,
  editionDisplayName,
  editionInstallShape,
  editionShellClass,
  editionVersionStrategy,
  isPrivateEdition,
  isPersonalEdition,
} from "./edition";
import {
  extractDouyinCollectStats,
  readableCommandError,
  readableCommandSuccess,
} from "./command-messages";
import { state, setBusy, setError, setMessage } from "./state";
import {
  checkbox,
  escapeAttr,
  escapeHtml,
  field,
  hidden,
  iconSvg,
  pathField as renderPathField,
  selectField,
} from "./ui";
import type {
  AccountPlatform,
  AccountProfile,
  AppConfigDraft,
  CommandResult,
  CustomSourcePlugin,
  ProgressStep,
  QueueStatus,
  SavedNoteTemplate,
  StatusPayload,
} from "./types";

const appRoot = document.querySelector<HTMLDivElement>("#app");

if (!appRoot) {
  throw new Error("missing #app root");
}

const app = appRoot;
const STORAGE_KEYS = {
  onboardingDone: "knowledgeStudio.onboarding.done",
  templates: "knowledgeStudio.templates",
  sourcePlugins: "knowledgeStudio.sourcePlugins",
};
const sourcePrefill = {
  webpage: "",
  directory: "",
};
document.title = appBrandName;
void getCurrentWindow().setTitle(appBrandName);

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
  loadLocalState();
  try {
    state.appVersion = await getVersion();
  } catch {
    // 取不到版本号时留空，更新页显示“未知”
  }
  await refresh();
  await loadDoctorSilently();
  render();
}

function loadLocalState(): void {
  state.savedTemplates = readJson<SavedNoteTemplate[]>(STORAGE_KEYS.templates, []);
  state.customSourcePlugins = readJson<CustomSourcePlugin[]>(
    STORAGE_KEYS.sourcePlugins,
    defaultSourcePlugins(),
  );
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown): void {
  localStorage.setItem(key, JSON.stringify(value));
}

function defaultSourcePlugins(): CustomSourcePlugin[] {
  return [
    {
      id: "web-clipper",
      name: "网页剪藏",
      mode: "webpage",
      description: "公众号、知乎、小红书、少数派、Medium、普通网页正文；需要登录的网站可先到账号页保存登录态。",
      sample: "https://example.com/article",
    },
    {
      id: "rss-reader",
      name: "RSS 批量导入",
      mode: "rss",
      description: "把订阅源写入 feeds.txt 后按上限导入。",
      sample: "https://example.com/feed.xml",
    },
    {
      id: "local-folder",
      name: "本地目录",
      mode: "directory",
      description: "扫描文本、PDF、音视频和图片文件。",
      sample: "D:\\资料\\inbox",
    },
  ];
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
      ocr: tools.ocr ?? "",
    },
    outputs: {
      formats: status.outputs?.formats?.length ? status.outputs.formats : ["markdown"],
      html_dir: status.outputs?.html_dir ?? "",
      csv_path: status.outputs?.csv_path ?? "",
      notion_token: "",
      notion_database_id: status.outputs?.notion_database_id_configured ? "configured" : "",
      notion_title_property: status.outputs?.notion_title_property ?? "Name",
      notion_api_base: status.outputs?.notion_api_base ?? "https://api.notion.com/v1",
    },
    prompt: {
      active_template: status.prompt?.active_template ?? "learning",
      custom_instruction: status.prompt?.custom_instruction ?? "",
    },
    note_template: {
      active_template: status.note_template?.active_template ?? "study_note",
      include_transcript: status.note_template?.include_transcript ?? true,
      include_source_notes: status.note_template?.include_source_notes ?? true,
      attribution_name: status.note_template?.attribution_name ?? "小黄狗",
      custom_structure: status.note_template?.custom_structure ?? "",
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
      setError(readableCommandError(label, result));
    } else {
      setMessage(readableCommandSuccess(label, result));
    }
    await reloadData();
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    render();
  }
}

function setProgressSteps(steps: ProgressStep[]): void {
  state.progressSteps = steps;
}

function updateProgressStep(id: string, status: ProgressStep["status"], detail?: string): void {
  state.progressSteps = state.progressSteps.map((step) =>
    step.id === id ? { ...step, status, detail: detail ?? step.detail } : step,
  );
  render();
}

function clearProgressSoon(): void {
  window.setTimeout(() => {
    if (!state.busy) {
      state.progressSteps = [];
      render();
    }
  }, 5000);
}

async function runSimpleProgress(
  label: string,
  steps: ProgressStep[],
  action: () => Promise<CommandResult>,
): Promise<void> {
  setProgressSteps(steps);
  setBusy(true);
  setMessage(`${label} 运行中...`);
  render();
  try {
    const active = steps[0];
    if (active) updateProgressStep(active.id, "active");
    const result = await action();
    if (!result.ok) {
      for (const step of state.progressSteps) {
        if (step.status === "active") updateProgressStep(step.id, "error", "失败");
      }
      setError(readableCommandError(label, result));
      return;
    }
    for (const step of state.progressSteps) {
      updateProgressStep(step.id, "done");
    }
    setMessage(readableCommandSuccess(label, result));
    await reloadData();
  } catch (error) {
    const active =
      state.progressSteps.find((step) => step.status === "active") ??
      state.progressSteps[state.progressSteps.length - 1];
    if (active) updateProgressStep(active.id, "error", readableError(error));
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    clearProgressSoon();
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

function optionalStringFromInput(id: string): string | null {
  const element = document.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(`#${id}`);
  return element ? element.value.trim() : null;
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

function outputFormatsFromForm(base: AppConfigDraft): string[] {
  const formats: string[] = [];
  if (boolFromInput("cfg-output-markdown", base.outputs.formats.includes("markdown"))) formats.push("markdown");
  if (boolFromInput("cfg-output-html", base.outputs.formats.includes("html"))) formats.push("html");
  if (boolFromInput("cfg-output-csv", base.outputs.formats.includes("csv"))) formats.push("csv");
  if (boolFromInput("cfg-output-notion", base.outputs.formats.includes("notion"))) formats.push("notion");
  return formats.length ? formats : ["markdown"];
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
      douyin_config: stringFromInput("cfg-douyin-config") || base.tools.douyin_config,
      whisper: stringFromInput("cfg-whisper") || base.tools.whisper,
      funasr: stringFromInput("cfg-funasr") || base.tools.funasr,
      ocr: stringFromInput("cfg-ocr"),
    },
    outputs: {
      formats: outputFormatsFromForm(base),
      html_dir: stringFromInput("cfg-output-html-dir") || base.outputs.html_dir,
      csv_path: stringFromInput("cfg-output-csv-path") || base.outputs.csv_path,
      notion_token: stringFromInput("cfg-output-notion-token"),
      notion_database_id: stringFromInput("cfg-output-notion-db") === "configured"
        ? base.outputs.notion_database_id
        : stringFromInput("cfg-output-notion-db") || base.outputs.notion_database_id,
      notion_title_property: stringFromInput("cfg-output-notion-title") || base.outputs.notion_title_property,
      notion_api_base: stringFromInput("cfg-output-notion-api") || base.outputs.notion_api_base,
    },
    prompt: {
      active_template: stringFromInput("cfg-prompt-template") || base.prompt.active_template,
      custom_instruction: stringFromInput("cfg-prompt-custom") || "",
    },
    note_template: {
      active_template: stringFromInput("cfg-note-template") || base.note_template.active_template,
      include_transcript: boolFromInput("cfg-note-include-transcript", base.note_template.include_transcript),
      include_source_notes: boolFromInput("cfg-note-include-source-notes", base.note_template.include_source_notes),
      attribution_name: stringFromInput("cfg-note-attribution") || base.note_template.attribution_name,
      custom_structure: optionalStringFromInput("cfg-note-custom-structure") ?? base.note_template.custom_structure,
    },
  };
}

async function handleSaveConfig(): Promise<void> {
  await runAction("保存配置", () => saveAppConfig(buildDraftFromForm()));
  await loadDoctorSilently();
  render();
}

async function handleOpenOutput(kind: string): Promise<void> {
  await runAction("打开位置", () => openOutput(kind));
}

async function handleChooseDirectory(targetId: string): Promise<void> {
  try {
    const selected = await chooseDirectory(stringFromInput(targetId));
    if (!selected) return;
    const element = document.querySelector<HTMLInputElement>(`#${targetId}`);
    if (element) element.value = selected;
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
    render();
  }
}

async function handleChooseBackupFile(): Promise<void> {
  try {
    const selected = await chooseBackupFile(stringFromInput("restore-backup-path"));
    if (!selected) return;
    const element = document.querySelector<HTMLInputElement>("#restore-backup-path");
    if (element) element.value = selected;
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
    render();
  }
}

async function handleBackupProject(): Promise<void> {
  setBusy(true);
  setMessage("正在创建项目备份...");
  render();
  try {
    const result = await backupProject();
    if (!result.ok) {
      setError(result.stderr || result.stdout || "备份失败");
      return;
    }
    let backupPath = "";
    try {
      const parsed = JSON.parse(result.stdout) as { backup_path?: string };
      backupPath = parsed.backup_path ?? "";
    } catch {
      backupPath = "";
    }
    setMessage(backupPath ? `备份完成：${backupPath}` : result.stdout || "备份完成");
    await reloadData();
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    render();
  }
}

async function handleRestoreProject(): Promise<void> {
  const backupFile = stringFromInput("restore-backup-path");
  if (!backupFile) {
    setError("请先填写备份 zip 文件路径。");
    render();
    return;
  }
  if (!window.confirm("恢复会覆盖当前配置、队列和账号资料。确认继续？")) return;
  await runAction("恢复备份", () => restoreProject(backupFile));
  await refresh();
}

async function handleExportDiagnostics(): Promise<void> {
  await runAction("导出诊断包", exportDiagnostics);
  await reloadData();
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
  setProgressSteps([
    { id: "account", label: "检查账号", detail: "使用当前抖音登录态", status: "active" },
    { id: "collect", label: "抓取收藏", detail: `目标 ${count} 条`, status: "pending" },
    { id: "queue", label: "写入队列", detail: "自动去重", status: "pending" },
    { id: "process", label: "生成笔记", detail: "下载、转写、摘要、写出", status: "pending" },
    { id: "refresh", label: "刷新结果", detail: "更新队列和日志", status: "pending" },
  ]);
  setBusy(true);
  setMessage(`正在抓取抖音收藏，目标 ${count} 条...`);
  render();
  try {
    updateProgressStep("account", "done", "账号检查已通过");
    updateProgressStep("collect", "active");
    const collect = await collectDouyin(count);
    if (!collect.ok) {
      updateProgressStep("collect", "error", "抓取失败");
      setError(collect.stderr || collect.stdout || "抖音收藏抓取失败");
      return;
    }
    const stats = extractDouyinCollectStats(collect.stdout);
    const queued = stats.queued;
    updateProgressStep("collect", "done", `下载器返回 ${stats.returned ?? "若干"} 条`);
    updateProgressStep("queue", "done", `去重入队 ${queued ?? "若干"} 条`);
    updateProgressStep("process", "active");
    setMessage(`抖音请求 ${stats.requested ?? count} 条，下载器返回 ${stats.returned ?? "若干"} 条，去重入队 ${queued ?? "若干"} 条，轮数 ${stats.attempts ?? "未知"}。正在生成笔记...`);
    render();
    const process = await processQueue(queued && queued > 0 ? queued : count);
    if (!process.ok) {
      updateProgressStep("process", "error", "处理失败");
      setError(readableCommandError("抖音收藏处理", process));
    } else {
      updateProgressStep("process", "done", "笔记已生成");
      updateProgressStep("refresh", "active");
      const collectedText = queued === null ? "" : `请求 ${stats.requested ?? count} 条，返回 ${stats.returned ?? "未知"} 条，入队 ${queued} 条，轮数 ${stats.attempts ?? "未知"}；`;
      setMessage(`${collectedText}处理完成。生成结果可到队列页和输出目录查看。`);
    }
    await reloadData();
    updateProgressStep("refresh", "done", "界面已刷新");
  } catch (error) {
    updateProgressStep("process", "error", readableError(error));
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    clearProgressSoon();
    render();
  }
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
  await runSimpleProgress(
    "扫描目录",
    [
      { id: "scan", label: "扫描文件", detail: "文本、PDF、音视频、图片", status: "active" },
      { id: "queue", label: "写入队列", detail: "自动去重", status: "pending" },
    ],
    () => scanDirectory(directory),
  );
}

async function handleRss(): Promise<void> {
  const limit = numberFromInput("rss-limit", 10, 1, 100);
  if (limit === null) return;
  await runSimpleProgress(
    "导入 RSS",
    [
      { id: "feeds", label: "读取订阅源", detail: `最多 ${limit} 条`, status: "active" },
      { id: "queue", label: "写入队列", detail: "等待统一处理", status: "pending" },
    ],
    () => collectRss(limit),
  );
}

async function handleWebpage(): Promise<void> {
  const url = stringFromInput("webpage-url");
  if (!url) {
    setError("请填写网页 URL。");
    render();
    return;
  }
  await runSimpleProgress(
    "网页剪藏",
    [
      { id: "fetch", label: "读取网页正文", detail: "提取标题和正文", status: "active" },
      { id: "queue", label: "写入队列", detail: "等待摘要处理", status: "pending" },
    ],
    () => clipWebpage(url),
  );
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
  await runSimpleProgress(
    "导入平台列表",
    [
      { id: "list", label: "解析列表", detail: `${platform} / ${limit} 条`, status: "active" },
      { id: "queue", label: "写入队列", detail: "使用当前账号 Cookie", status: "pending" },
    ],
    () => collectPlatformList(url, platform, limit),
  );
}

async function handleSaveSources(): Promise<void> {
  await runAction("保存来源文件", () => saveSourceFiles(stringFromInput("links-text"), stringFromInput("feeds-text")));
}

async function handleImportLinks(): Promise<void> {
  await runSimpleProgress(
    "导入链接",
    [
      { id: "save", label: "保存链接", detail: "写入 sources/links.txt", status: "active" },
      { id: "queue", label: "写入队列", detail: "自动识别平台", status: "pending" },
    ],
    async () => {
      const saved = await saveSourceFiles(stringFromInput("links-text"), stringFromInput("feeds-text"));
      if (!saved.ok) return saved;
      return importLinks();
    },
  );
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
  setProgressSteps([
    { id: "read", label: "读取队列", detail: `最多处理 ${limit} 条`, status: "active" },
    { id: "acquire", label: "采集内容", detail: "下载视频、读取网页/PDF/本地文件", status: "pending" },
    { id: "transcribe", label: "转写或提取正文", detail: "音视频转文字，文本直接读取", status: "pending" },
    { id: "summarize", label: "摘要分类", detail: "LLM 生成摘要、标签和目录", status: "pending" },
    { id: "write", label: "写出结果", detail: "Markdown/HTML/CSV/Notion 按配置输出", status: "pending" },
  ]);
  setBusy(true);
  setMessage(`正在处理 ${limit} 个待处理任务...`);
  render();
  try {
    updateProgressStep("read", "done");
    updateProgressStep("acquire", "active");
    updateProgressStep("transcribe", "active");
    updateProgressStep("summarize", "active");
    updateProgressStep("write", "active");
    const result = await processQueue(limit);
    if (!result.ok) {
      updateProgressStep("write", "error", "处理失败");
      setError(readableCommandError("处理队列", result));
      return;
    }
    for (const id of ["acquire", "transcribe", "summarize", "write"]) {
      updateProgressStep(id, "done");
    }
    setMessage(readableCommandSuccess("处理队列", result));
    await reloadData();
  } catch (error) {
    updateProgressStep("write", "error", readableError(error));
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    clearProgressSoon();
    render();
  }
}

async function handleCheckUpdates(): Promise<void> {
  if (isPrivateEdition) {
    setMessage(`${editionDisplayName()}只使用本机交付的安装包版本。`);
    render();
    return;
  }
  setBusy(true);
  setMessage("检查更新中...");
  render();
  try {
    const response = await fetch("https://api.github.com/repos/Jaychouhyl/Auto-Obsidian-md/releases/latest");
    if (!response.ok) {
      setMessage("当前没有可用发布版本。");
    } else {
      const payload = (await response.json()) as {
        tag_name?: string;
        html_url?: string;
        name?: string;
        assets?: Array<{ name?: string; browser_download_url?: string }>;
      };
      const latest = (payload.tag_name || payload.name || "").replace(/^v/i, "");
      const current = state.appVersion;
      const asset = payload.assets?.find((item) => item.name?.endsWith(".exe"));
      state.latestRelease = latest
        ? {
            tag: payload.tag_name || payload.name || latest,
            version: latest,
            url: payload.html_url || "",
            assetName: asset?.name || "",
            assetUrl: asset?.browser_download_url || payload.html_url || "",
            isNewer: current ? compareVersions(current, latest) < 0 : false,
          }
        : null;
      if (!latest) {
        setMessage("未能识别最新版本号。");
      } else if (!current) {
        setMessage(`最新版本：${latest}`);
      } else if (compareVersions(current, latest) >= 0) {
        setMessage(`已是最新版本（当前 ${current}，最新 ${latest}）。`);
      } else {
        setMessage(`有新版本可更新：当前 ${current} → 最新 ${latest}`);
      }
    }
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    render();
  }
}

async function handleOpenLatestRelease(): Promise<void> {
  const url = state.latestRelease?.assetUrl || state.latestRelease?.url;
  if (!url) {
    setError("请先检查更新。");
    render();
    return;
  }
  await runAction("打开下载页", () => openUrl(url));
}

function handleSaveTemplateToLibrary(): void {
  const name = stringFromInput("template-library-name") || "未命名模板";
  const structure = stringFromInput("cfg-note-custom-structure") || defaultCustomStructure();
  const now = new Date().toISOString();
  const existingId = stringFromInput("template-library-select");
  const id = existingId || `tpl-${Date.now().toString(36)}`;
  const next = state.savedTemplates.filter((template) => template.id !== id);
  const previous = state.savedTemplates.find((template) => template.id === id);
  next.unshift({
    id,
    name,
    structure,
    createdAt: previous?.createdAt ?? now,
    updatedAt: now,
  });
  state.savedTemplates = next;
  writeJson(STORAGE_KEYS.templates, state.savedTemplates);
  setMessage(`模板已保存：${name}`);
  render();
}

function handleLoadTemplateFromLibrary(): void {
  const id = stringFromInput("template-library-select");
  const template = state.savedTemplates.find((item) => item.id === id);
  if (!template) {
    setError("请先选择一个已保存模板。");
    render();
    return;
  }
  const structure = document.querySelector<HTMLTextAreaElement>("#cfg-note-custom-structure");
  const name = document.querySelector<HTMLInputElement>("#template-library-name");
  if (structure) structure.value = template.structure;
  if (name) name.value = template.name;
  if (state.configDraft) {
    state.configDraft = {
      ...state.configDraft,
      note_template: {
        ...state.configDraft.note_template,
        custom_structure: template.structure,
      },
    };
  }
  setMessage(`已加载模板：${template.name}`);
  render();
}

function handleDeleteTemplateFromLibrary(): void {
  const id = stringFromInput("template-library-select");
  const template = state.savedTemplates.find((item) => item.id === id);
  if (!template) return;
  if (!window.confirm(`删除模板“${template.name}”？`)) return;
  state.savedTemplates = state.savedTemplates.filter((item) => item.id !== id);
  writeJson(STORAGE_KEYS.templates, state.savedTemplates);
  setMessage(`已删除模板：${template.name}`);
  render();
}

function handleImportTemplateLibrary(): void {
  const raw = stringFromInput("template-library-json");
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw) as SavedNoteTemplate[];
    if (!Array.isArray(parsed)) throw new Error("JSON 必须是数组。");
    state.savedTemplates = parsed.filter((item) => item.id && item.name && item.structure);
    writeJson(STORAGE_KEYS.templates, state.savedTemplates);
    setMessage(`已导入 ${state.savedTemplates.length} 个模板。`);
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  }
  render();
}

function handleSaveSourcePlugin(): void {
  const name = stringFromInput("source-plugin-name");
  const mode = stringFromInput("source-plugin-mode") as CustomSourcePlugin["mode"];
  const sample = stringFromInput("source-plugin-sample");
  const description = stringFromInput("source-plugin-description");
  if (!name || !mode) {
    setError("请填写来源插件名称和类型。");
    render();
    return;
  }
  const id = `src-${Date.now().toString(36)}`;
  state.customSourcePlugins = [{ id, name, mode, sample, description }, ...state.customSourcePlugins];
  writeJson(STORAGE_KEYS.sourcePlugins, state.customSourcePlugins);
  setMessage(`来源插件已保存：${name}`);
  render();
}

function handleApplySourcePlugin(id: string): void {
  const plugin = state.customSourcePlugins.find((item) => item.id === id);
  if (!plugin) return;
  if (plugin.mode === "links") {
    if (plugin.sample) state.sourceFiles.links = `${state.sourceFiles.links.trim()}\n${plugin.sample}`.trim();
  } else if (plugin.mode === "rss") {
    if (plugin.sample) state.sourceFiles.feeds = `${state.sourceFiles.feeds.trim()}\n${plugin.sample}`.trim();
  } else if (plugin.mode === "webpage") {
    sourcePrefill.webpage = plugin.sample;
  } else if (plugin.mode === "directory") {
    sourcePrefill.directory = plugin.sample;
  }
  setMessage(`已应用来源插件：${plugin.name}`);
  render();
}

function handleDeleteSourcePlugin(id: string): void {
  const plugin = state.customSourcePlugins.find((item) => item.id === id);
  if (!plugin) return;
  if (!window.confirm(`删除来源插件“${plugin.name}”？`)) return;
  state.customSourcePlugins = state.customSourcePlugins.filter((item) => item.id !== id);
  writeJson(STORAGE_KEYS.sourcePlugins, state.customSourcePlugins);
  setMessage(`已删除来源插件：${plugin.name}`);
  render();
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
  const primary: Array<[typeof state.activeView, string, string]> = [
    ["run", "运行", "Play"],
    ["accounts", "账号", "User"],
    ["sources", "导入", "Inbox"],
    ["queue", "队列", "List"],
    ["templates", "模板", "FileText"],
    ["knowledge", "知识库", "Library"],
  ];
  const utilities: Array<[typeof state.activeView, string, string]> = [
    ["setup", "配置", "Gear"],
    ["dependencies", "依赖", "Wrench"],
    ["rules", "规则", "Route"],
    ["logs", "日志", "Terminal"],
    ...(isPrivateEdition ? [] : ([["updates", "更新", "Upload"]] as Array<[typeof state.activeView, string, string]>)),
    ["settings", "高级", "Sliders"],
  ];
  return `
    <nav class="nav-primary">
      ${primary.map(([key, label, iconName]) => renderNavButton(key, label, iconName)).join("")}
    </nav>
    <div class="nav-spacer"></div>
    <div class="nav-utilities" aria-label="系统设置">
      ${utilities.map(([key, label, iconName]) => renderIconButton(key, label, iconName)).join("")}
    </div>
  `;
}

function renderNavButton(view: typeof state.activeView, label: string, iconName: string): string {
  return `<button class="nav-item ${state.activeView === view ? "active" : ""}" data-view="${view}">${iconSvg(iconName)}<span>${label}</span></button>`;
}

function renderIconButton(view: typeof state.activeView, label: string, iconName: string): string {
  return `<button class="nav-icon ${state.activeView === view ? "active" : ""}" data-view="${view}" title="${escapeAttr(label)}" aria-label="${escapeAttr(label)}">${iconSvg(iconName)}</button>`;
}

function renderView(): string {
  if (state.activeView === "setup") return renderSetupView();
  if (state.activeView === "dependencies") return renderDependenciesView();
  if (state.activeView === "run") return renderRunView();
  if (state.activeView === "accounts") return renderAccountsView();
  if (state.activeView === "sources") return renderSourcesView();
  if (state.activeView === "queue") return renderQueueView();
  if (state.activeView === "templates") return renderTemplatesView();
  if (state.activeView === "rules") return renderRulesView();
  if (state.activeView === "logs") return renderLogsView();
  if (state.activeView === "knowledge") return renderKnowledgeView();
  if (state.activeView === "updates") return isPrivateEdition ? renderSettingsView() : renderUpdatesView();
  return renderSettingsView();
}

function renderSetupView(): string {
  const draft = state.configDraft;
  if (!draft) return renderLoadingView("配置");
  return `
    <section class="view">
      <div class="view-header">
        <div>
          <span class="eyebrow">First run</span>
          <h1>配置</h1>
        </div>
        <div class="toolbar">
          <button id="save-config" ${disabledAttr()}>保存</button>
          <button id="doctor-json" ${disabledAttr()}>健康检查</button>
        </div>
      </div>
      ${renderSetupStatus()}
      ${renderSetupWizard()}
      <div class="form-grid">
        ${selectField("输出模式", "cfg-obsidian-mode", [["local", "本地 Markdown / Obsidian 文件夹"], ["rest", "Obsidian Local REST API"]], draft.obsidian_mode)}
        ${pathField("输出目录", "cfg-vault", draft.obsidian_vault)}
        ${field("默认文件夹", "cfg-folder", draft.obsidian_folder)}
        ${field("队列数据库", "cfg-queue-db", draft.queue_db)}
        ${pathField("缓存目录", "cfg-cache-dir", draft.cache_dir)}
        ${checkbox("启用 LLM", "cfg-llm-enabled", draft.llm_enabled)}
        ${field("LLM Base URL", "cfg-llm-base", draft.llm_base_url)}
        ${field("LLM Model", "cfg-llm-model", draft.llm_model)}
        ${field("API Key", "cfg-llm-key", "", "password")}
      </div>
      ${renderOutputConfig(draft)}
      ${renderBackupPanel()}
      ${renderDoctorReport()}
      ${renderMessageArea()}
    </section>
  `;
}

function renderOutputConfig(draft: AppConfigDraft): string {
  return `
    <section class="panel output-panel">
      <div class="section-head">
        <div>
          <span class="eyebrow">Outputs</span>
          <h2>输出方式</h2>
        </div>
        <div class="row-actions">
          <button data-open-output="vault" ${disabledAttr()}>打开 Markdown</button>
          <button data-open-output="html" ${disabledAttr()}>打开 HTML</button>
          <button data-open-output="csv" ${disabledAttr()}>打开 CSV</button>
        </div>
      </div>
      <div class="output-toggles">
        ${checkbox("Markdown / Obsidian", "cfg-output-markdown", draft.outputs.formats.includes("markdown"))}
        ${checkbox("HTML", "cfg-output-html", draft.outputs.formats.includes("html"))}
        ${checkbox("Excel / CSV", "cfg-output-csv", draft.outputs.formats.includes("csv"))}
        ${checkbox("Notion", "cfg-output-notion", draft.outputs.formats.includes("notion"))}
      </div>
      <div class="form-grid">
        ${pathField("HTML 输出目录", "cfg-output-html-dir", draft.outputs.html_dir)}
        ${field("Excel/CSV 索引文件", "cfg-output-csv-path", draft.outputs.csv_path)}
        ${field("Notion Token", "cfg-output-notion-token", "", "password")}
        ${field("Notion Database ID", "cfg-output-notion-db", draft.outputs.notion_database_id)}
        ${field("Notion 标题属性", "cfg-output-notion-title", draft.outputs.notion_title_property)}
        ${field("Notion API Base", "cfg-output-notion-api", draft.outputs.notion_api_base)}
      </div>
    </section>
  `;
}

function renderBackupPanel(): string {
  return `
    <section class="panel backup-panel">
      <div class="section-head">
        <div>
          <span class="eyebrow">Backup</span>
          <h2>备份与恢复</h2>
        </div>
        <div class="row-actions">
          <button id="backup-project" ${disabledAttr()}>创建备份</button>
          <button data-open-output="project" ${disabledAttr()}>打开项目目录</button>
        </div>
      </div>
      <div class="inline-form">
        ${field("备份 zip 路径", "restore-backup-path", "")}
        <button id="choose-backup-file" ${disabledAttr()}>选择备份</button>
        <button id="restore-project" ${disabledAttr()}>恢复备份</button>
      </div>
      <p class="muted">备份包用于本机迁移和故障恢复，可能包含配置、账号登录态和本地来源文件，请勿公开分享或提交到 Git。</p>
    </section>
  `;
}

function renderSetupStatus(): string {
  const status = state.status;
  const accountCount = state.accounts.length;
  const llmState = status?.llm.enabled
    ? status.llm.api_key_configured
      ? "LLM 已启用，Key 已配置"
      : "LLM 已启用，缺少 Key"
    : "LLM 未启用";
  return `
    <div class="status-grid">
      ${renderStatusCard("项目目录", status?.paths.project_root ?? "未加载")}
      ${renderStatusCard("输出位置", status?.paths.obsidian_vault ?? "未配置")}
      ${renderStatusCard("LLM", llmState)}
      ${renderStatusCard("输出格式", status?.outputs?.formats?.join(", ") ?? "markdown")}
      ${renderStatusCard("账号", `${accountCount} 个账号`)}
    </div>
  `;
}

function renderSetupWizard(): string {
  const status = state.status;
  const requiredIssues = state.doctor?.checks.filter((check) => check.required && !check.ok).length ?? 0;
  const steps = [
    {
      label: "输出目录",
      status: status?.paths.obsidian_vault ? "done" : "todo",
      text: status?.paths.obsidian_vault || "选择 Markdown、Obsidian 或其它本地输出目录",
      action: "setup",
    },
    {
      label: "摘要/API",
      status: status?.llm.enabled && status.llm.api_key_configured ? "done" : "todo",
      text: status?.llm.enabled
        ? status.llm.api_key_configured
          ? "已启用，Key 已配置"
          : "已启用，等待 API Key"
        : "开启后可自动总结和打标签",
      action: "setup",
    },
    {
      label: "账号与来源",
      status: state.accounts.length || (status?.queue.pending ?? 0) > 0 || (status?.queue.done ?? 0) > 0 ? "done" : "todo",
      text: state.accounts.length ? `${state.accounts.length} 个账号可用，也可以导入链接/RSS/文件夹` : "添加账号，或直接导入链接/RSS/本地文件夹",
      action: state.accounts.length ? "sources" : "accounts",
    },
    {
      label: "检查并运行",
      status: requiredIssues === 0 ? "done" : "todo",
      text: requiredIssues === 0 ? `已就绪，输出 ${status?.outputs?.formats?.join(" / ") || "Markdown"}` : `${requiredIssues} 项必须处理`,
      action: requiredIssues === 0 ? "run" : "dependencies",
    },
  ];
  return `
    <section class="setup-wizard">
      ${steps
        .map(
          (step, index) => `
            <button class="wizard-step ${step.status}" data-view="${step.action}">
              <span>${String(index + 1).padStart(2, "0")}</span>
              <b>${escapeHtml(step.label)}</b>
              <small>${escapeHtml(step.text)}</small>
            </button>
          `,
        )
        .join("")}
    </section>
  `;
}

function renderStatusCard(label: string, value: string): string {
  return `<div class="status-card"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b></div>`;
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
        <div>
          <span class="eyebrow">Command center</span>
          <h1>运行</h1>
        </div>
        <button id="refresh" ${disabledAttr()}>刷新</button>
      </div>
      ${renderRuntimeStrip()}
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

function renderRuntimeStrip(): string {
  const status = state.status;
  const llm = status?.llm.enabled
    ? status.llm.api_key_configured
      ? "LLM: on"
      : "LLM: missing key"
    : "LLM: off";
  const douyin = state.accounts.find((account) => account.platform === "douyin" && account.is_current);
  return `
    <div class="runtime-strip">
      <span>${escapeHtml(status?.paths.project_root ?? "未加载项目目录")}</span>
      <span>${escapeHtml(status?.obsidian.mode === "rest" ? "REST 输出" : "本地 Markdown 输出")}</span>
      <span>${escapeHtml(`输出: ${status?.outputs?.formats?.join(", ") ?? "markdown"}`)}</span>
      <span>${escapeHtml(llm)}</span>
      <span>${escapeHtml(douyin ? `抖音: ${douyin.display_name}` : "抖音: 未登录")}</span>
    </div>
  `;
}

const PlatformDefinition: Record<AccountPlatform, { label: string; short: string }> = {
  douyin: { label: "抖音", short: "抖音收藏" },
  bilibili: { label: "哔哩哔哩", short: "B站列表" },
  youtube: { label: "YouTube", short: "YouTube 列表" },
  tiktok: { label: "TikTok", short: "TikTok 内容" },
  zhihu: { label: "知乎", short: "知乎网页" },
  xiaohongshu: { label: "小红书", short: "小红书网页" },
  wechat: { label: "微信公众号", short: "公众号网页" },
};

function renderAccountsView(): string {
  const platforms = Object.keys(PlatformDefinition) as AccountPlatform[];
  return `
    <section class="view">
      <div class="view-header">
        <div>
          <span class="eyebrow">Session profiles</span>
          <h1>账号</h1>
        </div>
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
        <div>
          <span class="eyebrow">Source collector</span>
          <h1>导入</h1>
        </div>
        <button id="save-sources" ${disabledAttr()}>保存来源</button>
      </div>
      ${renderAccountSummary(["douyin", "bilibili", "youtube", "tiktok", "zhihu", "xiaohongshu", "wechat"])}
      <div class="hint-panel">
        <b>平台来源说明</b>
        <p>抖音、B站、YouTube、TikTok 等平台导入依赖当前账号登录态和平台规则；遇到验证码、风控、接口变化时可能少量返回或失败。建议先小批量导入，普通网页、RSS、本地文件不受平台账号影响。</p>
      </div>
      ${renderSourceConnectorGrid()}
      ${renderSourcePluginManager()}
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
        ${field("网页 URL", "webpage-url", sourcePrefill.webpage || "https://example.com/article")}
        <button id="clip-webpage" ${disabledAttr()}>网页剪藏</button>
        ${pathField("目录路径", "directory-path", sourcePrefill.directory || "D:\\Downloads")}
        <button id="run-directory" ${disabledAttr()}>扫描目录</button>
        ${selectField("视频列表平台", "platform-kind", [["auto", "自动"], ["youtube", "YouTube"], ["bilibili", "B站"], ["tiktok", "TikTok"]])}
        ${field("列表链接", "platform-url", "")}
        ${field("列表数量", "platform-limit", "20", "number")}
        <button id="run-platform-list" ${disabledAttr()}>导入列表</button>
      </div>
      ${renderMessageArea()}
    </section>
  `;
}

function renderSourceConnectorGrid(): string {
  const connectors = [
    ["账号来源", "抖音、B站、YouTube、TikTok、知乎、小红书、公众号", "账号页统一登录、切换、校验。抖音收藏在运行页选择数量后抓取。"],
    ["视频列表", "B站收藏夹、YouTube 播放列表、TikTok 列表", "填写列表链接和数量，适合批量视频。"],
    ["网页文章", "普通网页、知乎、公众号、小红书网页、少数派、Medium", "单条剪藏，批量放进 links.txt。"],
    ["播客/RSS", "播客、博客、新闻源、专栏", "把 RSS / Atom 地址放入 RSS 文本框。"],
    ["本地资料", "PDF、字幕、音频、视频、图片、文本、Markdown、EPUB", "目录扫描支持图片入库；配置 OCR 后可识别图片文字。"],
    ["多输出", "Markdown、HTML、Excel/CSV、Notion", "在配置页开启输出格式，后续处理会同步写入。"],
  ];
  return `<div class="connector-grid compact">
    ${connectors
      .map(
        ([title, scope, action]) => `
          <div class="connector-card">
            <div class="connector-head"><b>${escapeHtml(title)}</b><span>${escapeHtml(scope)}</span></div>
            <p>${escapeHtml(action)}</p>
          </div>
        `,
      )
      .join("")}
  </div>`;
}

function renderSourcePluginManager(): string {
  return `
    <section class="panel source-plugins">
      <div class="section-head">
        <div>
          <span class="eyebrow">Source plugins</span>
          <h2>来源插件</h2>
        </div>
        <button id="save-source-plugin" ${disabledAttr()}>保存插件</button>
      </div>
      <div class="plugin-grid">
        ${state.customSourcePlugins
          .map(
            (plugin) => `
              <div class="plugin-card">
                <div>
                  <b>${escapeHtml(plugin.name)}</b>
                  <span>${escapeHtml(sourceModeLabel(plugin.mode))}</span>
                </div>
                <p>${escapeHtml(plugin.description || plugin.sample || "自定义来源入口")}</p>
                <div class="row-actions">
                  <button data-apply-source-plugin="${escapeAttr(plugin.id)}" ${disabledAttr()}>应用</button>
                  <button data-delete-source-plugin="${escapeAttr(plugin.id)}" ${disabledAttr()}>删除</button>
                </div>
              </div>
            `,
          )
          .join("")}
      </div>
      <div class="form-grid">
        ${field("插件名称", "source-plugin-name", "")}
        ${selectField("类型", "source-plugin-mode", [["links", "链接批量"], ["rss", "RSS"], ["webpage", "网页"], ["directory", "本地目录"]])}
        ${field("示例链接或路径", "source-plugin-sample", "")}
        ${field("说明", "source-plugin-description", "")}
      </div>
    </section>
  `;
}

function sourceModeLabel(mode: CustomSourcePlugin["mode"]): string {
  const labels: Record<CustomSourcePlugin["mode"], string> = {
    links: "链接批量",
    rss: "RSS",
    webpage: "网页",
    directory: "本地目录",
  };
  return labels[mode];
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
  const advice = queueAdvice(item);
  return `<tr>
    <td>${item.id}</td>
    <td><span class="badge ${escapeAttr(item.status)}">${escapeHtml(item.status)}</span></td>
    <td>${escapeHtml(item.title ?? item.url)}</td>
    <td>${escapeHtml(item.platform)}</td>
    <td>
      <div class="queue-detail">
        <b>${escapeHtml(item.error ? "需要处理" : item.note_path ? "已输出" : "等待处理")}</b>
        <span>${escapeHtml(item.error ?? item.note_path ?? item.url)}</span>
        ${advice ? `<small>${escapeHtml(advice)}</small>` : ""}
      </div>
    </td>
    <td class="row-actions">
      <button data-retry-id="${item.id}" ${disabledAttr()}>重试</button>
      <button data-skip-id="${item.id}" ${disabledAttr()}>跳过</button>
    </td>
  </tr>`;
}

function queueAdvice(item: { status: string; error: string | null; platform: string }): string {
  const error = (item.error ?? "").toLowerCase();
  if (!item.error) return item.status === "done" ? "笔记已生成，可在输出目录查看。" : "";
  if (error.includes("api") || error.includes("key")) return "检查 LLM API Key、Base URL 和模型名称。";
  if (error.includes("cookie") || error.includes("login") || error.includes("account")) return "账号登录态可能失效，请到账号页校验或重新登录。";
  if (error.includes("yt-dlp") || error.includes("ffmpeg") || error.includes("whisper")) return "依赖缺失或路径错误，请到依赖页重新检测并安装。";
  if (error.includes("notion")) return "Notion 输出失败，请检查 Token、Database ID 和标题字段。";
  return "可先重试；重复失败时打开日志页查看详细信息。";
}

function renderTemplatesView(): string {
  const draft = state.configDraft;
  if (!draft) return renderLoadingView("模板");
  return `
    <section class="view">
      <div class="view-header">
        <div>
          <span class="eyebrow">Prompt & note templates</span>
          <h1>模板</h1>
        </div>
        <button id="save-config" ${disabledAttr()}>保存模板</button>
      </div>
      <div class="split">
        <section class="panel">
          <div class="section-head">
            <div>
              <span class="eyebrow">LLM</span>
              <h2>提示词模板</h2>
            </div>
          </div>
          ${selectField("摘要用途", "cfg-prompt-template", promptTemplateOptions(), draft.prompt.active_template)}
          <label class="field wide">
            <span>补充规则</span>
            <textarea id="cfg-prompt-custom" rows="9">${escapeHtml(draft.prompt.custom_instruction)}</textarea>
          </label>
          <div class="template-preview">
            ${promptTemplateCards(draft.prompt.active_template)}
          </div>
        </section>
        <section class="panel">
          <div class="section-head">
            <div>
              <span class="eyebrow">Markdown</span>
              <h2>输出模板</h2>
            </div>
          </div>
          ${selectField("笔记结构", "cfg-note-template", noteTemplateOptions(), draft.note_template.active_template)}
          ${checkbox("写入原始转写", "cfg-note-include-transcript", draft.note_template.include_transcript)}
          ${checkbox("写入处理备注", "cfg-note-include-source-notes", draft.note_template.include_source_notes)}
          ${field("署名", "cfg-note-attribution", draft.note_template.attribution_name)}
          <label class="field wide">
            <span>自定义 Markdown 结构</span>
            <textarea id="cfg-note-custom-structure" rows="13" placeholder="${escapeAttr(defaultCustomStructure())}">${escapeHtml(draft.note_template.custom_structure)}</textarea>
          </label>
          <div class="placeholder-grid">
            ${["title", "url", "summary", "key_points", "action_items", "source_notes", "transcript"]
              .map((name) => `<code>{{${name}}}</code>`)
              .join("")}
          </div>
          <div class="template-preview">
            <b>当前笔记结构</b>
            <span>留空使用预设结构；填写后会按自定义 Markdown 骨架输出，并自动保留 frontmatter 与署名。</span>
          </div>
          ${renderTemplateLibrary()}
        </section>
      </div>
      ${hiddenTemplateConfig(draft)}
      ${renderMessageArea()}
    </section>
  `;
}

function renderTemplateLibrary(): string {
  return `
    <section class="template-library">
      <div class="section-head">
        <div>
          <span class="eyebrow">Local library</span>
          <h3>模板库</h3>
        </div>
      </div>
      <div class="inline-form">
        ${selectField(
          "已保存模板",
          "template-library-select",
          [["", "选择模板"], ...state.savedTemplates.map((template) => [template.id, template.name] as [string, string])],
        )}
        ${field("模板名", "template-library-name", "")}
      </div>
      <div class="toolbar">
        <button id="template-save-library" ${disabledAttr()}>保存到模板库</button>
        <button id="template-load-library" ${disabledAttr()} ${state.savedTemplates.length ? "" : "disabled"}>加载</button>
        <button id="template-delete-library" ${disabledAttr()} ${state.savedTemplates.length ? "" : "disabled"}>删除</button>
        <button id="template-import-library" ${disabledAttr()}>导入 JSON</button>
      </div>
      <label class="field wide">
        <span>模板库 JSON</span>
        <textarea id="template-library-json" rows="4">${escapeHtml(JSON.stringify(state.savedTemplates, null, 2))}</textarea>
      </label>
    </section>
  `;
}

function promptTemplateOptions(): Array<[string, string]> {
  return [
    ["learning", "通用学习总结"],
    ["exam", "考研/考试资料"],
    ["quant", "炒股/量化学习"],
    ["podcast", "播客/访谈"],
    ["web", "网页文章"],
    ["paper", "论文/研究"],
  ];
}

function noteTemplateOptions(): Array<[string, string]> {
  return [
    ["study_note", "学习笔记"],
    ["review_card", "复习卡片"],
    ["research_note", "研究笔记"],
    ["action_note", "行动清单"],
  ];
}

function defaultCustomStructure(): string {
  return [
    "## 一句话总结",
    "{{summary}}",
    "",
    "## 核心知识点",
    "{{key_points}}",
    "",
    "## 可执行清单",
    "{{action_items}}",
    "",
    "## 处理备注",
    "{{source_notes}}",
    "",
    "## 原始转写",
    "{{transcript}}",
  ].join("\n");
}

function promptTemplateCards(active: string): string {
  const descriptions: Record<string, string> = {
    learning: "适合课程、教程、短视频知识点，强调概念、例子和复习动作。",
    exam: "适合考研和考试资料，强调考点、易错点、背诵线索和复习优先级。",
    quant: "适合炒股与量化学习，强调策略逻辑、风险、参数和验证方法。",
    podcast: "适合长音频，强调观点、时间线、金句和后续行动。",
    web: "适合网页文章，强调主旨、证据、可引用内容和个人解读。",
    paper: "适合论文，强调问题、方法、数据、结论、局限和复现。",
  };
  return `<b>${escapeHtml(promptTemplateOptions().find(([value]) => value === active)?.[1] ?? "通用学习总结")}</b><span>${escapeHtml(descriptions[active] ?? descriptions.learning)}</span>`;
}

function renderRulesView(): string {
  const draft = state.configDraft;
  if (!draft) return renderLoadingView("规则");
  return `
    <section class="view">
      <div class="view-header">
        <div>
          <span class="eyebrow">Routing rules</span>
          <h1>规则</h1>
        </div>
        <button id="save-config" ${disabledAttr()}>保存</button>
      </div>
      <div class="rule-grid">
        ${draft.allowed_folders.map((folder) => renderRuleCard(folder)).join("")}
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

function renderRuleCard(folder: string): string {
  const hints: Record<string, string> = {
    "AI学习": "大模型、提示词、智能体、AI 工具",
    "考研资料汇总": "考研、复试、调剂、备考材料",
    "炒股与量化学习": "股票、量化、交易、回测、风控",
    "研后/英语学习": "英语、单词、听力、长难句",
    "工作": "项目、简历、面试、职场、会议",
    "Life": "健康、生活、运动、睡眠",
    "Inbox/Learning Inbox": "不确定内容的默认入口",
  };
  return `<div class="rule-card"><b>${escapeHtml(folder)}</b><span>${escapeHtml(hints[folder] ?? "自定义分类目录")}</span></div>`;
}

function renderLogsView(): string {
  const issues = diagnosticIssues();
  const rows = state.logs
    .map(
      (log) => `<div class="log-row">
        <b>${escapeHtml(readableLogLabel(log.name))}</b>
        <span>
          ${escapeHtml(readableLogTime(log.modified_unix))}
          <small>${escapeHtml(log.name)} · ${escapeHtml(log.path)}</small>
        </span>
      </div>`,
    )
    .join("");
  return `
    <section class="view">
      <div class="view-header">
        <div>
          <span class="eyebrow">Diagnostics</span>
          <h1>诊断与日志</h1>
        </div>
        <div class="toolbar">
          <button id="doctor-json" ${disabledAttr()}>重新检查</button>
          <button id="export-diagnostics" ${disabledAttr()}>导出诊断包</button>
          <button data-open-output="project" ${disabledAttr()}>打开项目目录</button>
        </div>
      </div>
      <div class="diagnostic-grid">
        ${
          issues.length
            ? issues.map(renderDiagnosticIssue).join("")
            : '<div class="diagnostic-card ok"><b>当前没有发现需要处理的问题</b><span>如果任务失败，先刷新一次，再查看下方日志文件。</span></div>'
        }
      </div>
      <section class="panel">
        <div class="section-head">
          <div>
            <span class="eyebrow">Troubleshooting files</span>
            <h2>排障文件</h2>
          </div>
        </div>
        <p class="muted">普通使用先看上面的处理建议；只有反复失败时，再把这些文件发给维护者排查。</p>
        <p class="muted">诊断包只保存在本机，会脱敏常见 Key/Token，不包含账号浏览器缓存；分享前仍建议自己检查一遍。</p>
        ${rows || '<p class="muted">暂无日志文件。</p>'}
      </section>
      ${renderMessageArea()}
    </section>
  `;
}

function readableLogLabel(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes("doctor")) return "环境检查记录";
  if (lower.includes("dependency")) return "依赖安装/检测记录";
  if (lower.includes("douyin")) return "抖音收藏抓取记录";
  if (lower.includes("queue") || lower.includes("run")) return "队列处理记录";
  if (lower.includes("account")) return "账号登录/切换记录";
  if (lower.includes("backup") || lower.includes("restore")) return "备份恢复记录";
  return "运行记录";
}

function readableLogTime(modifiedUnix: number): string {
  if (!modifiedUnix) return "时间未知";
  const timestamp = modifiedUnix > 1000000000000 ? modifiedUnix : modifiedUnix * 1000;
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(timestamp));
  } catch {
    return new Date(timestamp).toLocaleString();
  }
}

function diagnosticIssues(): Array<{ severity: "bad" | "warn"; title: string; impact: string; action: string }> {
  const issues: Array<{ severity: "bad" | "warn"; title: string; impact: string; action: string }> = [];
  for (const check of state.doctor?.checks ?? []) {
    if (check.ok) continue;
    issues.push({
      severity: check.required ? "bad" : "warn",
      title: readableCheckName(check.name),
      impact: check.required ? "会阻止核心流程继续运行。" : "只影响部分来源或可选能力。",
      action: readableCheckAction(check.name, check.detail),
    });
  }
  for (const item of state.dependencies?.items ?? []) {
    if (item.status === "ready") continue;
    const label = item.label.toLowerCase();
    if (issues.some((issue) => issue.title.toLowerCase().includes(label) || label.includes(issue.title.toLowerCase()))) {
      continue;
    }
    issues.push({
      severity: "warn",
      title: `${item.label} 不可用`,
      impact: item.purpose,
      action: item.installable ? "可在依赖页点击安装缺失工具。" : item.manual_action,
    });
  }
  const failedCount = state.status?.queue.failed ?? 0;
  if (failedCount > 0) {
    issues.push({
      severity: "warn",
      title: `${failedCount} 个任务失败`,
      impact: "这些资料还没有生成最终笔记。",
      action: "到队列页筛选失败项，先重试；重复失败再看错误建议。",
    });
  }
  return dedupeDiagnostics(issues);
}

function renderDiagnosticIssue(issue: { severity: "bad" | "warn"; title: string; impact: string; action: string }): string {
  return `<div class="diagnostic-card ${issue.severity}">
    <b>${escapeHtml(issue.title)}</b>
    <span>${escapeHtml(issue.impact)}</span>
    <small>${escapeHtml(issue.action)}</small>
  </div>`;
}

function readableCheckName(name: string): string {
  const names: Record<string, string> = {
    config: "配置文件",
    queue_db_parent: "队列数据库目录",
    cache_dir: "缓存目录",
    obsidian_mode: "输出模式",
    obsidian_vault: "Markdown/Obsidian 输出目录",
    "yt-dlp": "yt-dlp",
    ffmpeg: "ffmpeg",
    "douyin-downloader": "抖音下载器",
    whisper: "Whisper 转写",
    funasr: "FunASR 转写",
    ocr: "OCR 图片识别",
    llm_api_key: "LLM API Key",
    obsidian_rest_key: "Obsidian REST Key",
    output_formats: "输出格式",
    notion_credentials: "Notion 配置",
  };
  return names[name] ?? name;
}

function readableCheckAction(name: string, detail: string): string {
  if (name === "llm_api_key") return "到配置页填写 DeepSeek API Key，或关闭 LLM。";
  if (name === "obsidian_vault") return "到配置页选择真实存在的输出目录。";
  if (name === "notion_credentials") return "如果开启 Notion 输出，请填写 Token 和 Database ID。";
  if (name === "ocr") return "需要图片识别时，在高级页填写可用的 OCR 命令；不处理图片可忽略。";
  if (["yt-dlp", "ffmpeg", "whisper", "funasr", "douyin-downloader"].includes(name)) return "到依赖页重新检测，并按提示安装或填写路径。";
  return detail || "按配置页提示修正后重新检查。";
}

function dedupeDiagnostics<T extends { title: string }>(items: T[]): T[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.title)) return false;
    seen.add(item.title);
    return true;
  });
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
  const release = state.latestRelease;
  return `
    <section class="view">
      <div class="view-header">
        <div>
          <span class="eyebrow">Release</span>
          <h1>更新</h1>
        </div>
        <div class="toolbar">
          <button id="check-updates" ${disabledAttr()}>检查更新</button>
          <button id="open-latest-release" ${disabledAttr()} ${release ? "" : "disabled"}>打开下载</button>
        </div>
      </div>
      <div class="update-grid">
        <div class="update-card">
          <span>当前版本</span>
          <b>${escapeHtml(state.appVersion || "未知")}</b>
        </div>
        <div class="update-card ${release?.isNewer ? "warn" : "ok"}">
          <span>最新版本</span>
          <b>${escapeHtml(release?.version || "未检查")}</b>
        </div>
        <div class="update-card">
          <span>安装包</span>
          <b>${escapeHtml(release?.assetName || "检查后显示")}</b>
        </div>
      </div>
      <div class="settings">
        <p><b>仓库：</b>Jaychouhyl/Auto-Obsidian-md</p>
        <p><b>升级方式：</b>检查到新版后，打开下载页下载安装包覆盖安装。</p>
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
        ${field("OCR command", "cfg-ocr", draft.tools.ocr)}
      </div>
      <div class="split">
        <section class="panel">
          <span class="eyebrow">Local LLM</span>
          <h2>本地模型</h2>
          <div class="connector-grid compact">
            <div class="connector-card"><div class="connector-head"><b>Ollama</b><span>本地</span></div><p>Base URL 可填 http://127.0.0.1:11434/v1，模型填本机模型名。</p></div>
            <div class="connector-card"><div class="connector-head"><b>LM Studio</b><span>本地</span></div><p>启动本地 OpenAI-compatible server 后，把 Base URL 和模型名填到配置页。</p></div>
          </div>
        </section>
        <section class="panel">
          <span class="eyebrow">Privacy</span>
          <h2>隐私与备份</h2>
          ${renderSecurityPanel()}
        </section>
      </div>
      ${renderEditionPanel()}
      <section class="panel">
        <div class="section-head">
          <div>
            <span class="eyebrow">Install experience</span>
            <h2>软件级安装体验</h2>
          </div>
          <div class="row-actions">
            <button id="write-launcher" ${disabledAttr()}>生成启动器</button>
            <button id="export-diagnostics" ${disabledAttr()}>导出诊断包</button>
          </div>
        </div>
        <div class="installer-steps">
          <span>当前版本：${escapeHtml(state.appVersion || "未知")}</span>
          <span>当前形态：${escapeHtml(editionInstallShape())}</span>
          <span>桌面快捷方式：启动器和安装包均支持</span>
          <span>开始菜单/卸载：安装包提供</span>
          <span>首次使用：引导页完成输出目录、LLM、依赖、账号</span>
          <span>诊断支持：本地导出脱敏诊断包，不自动上传</span>
          <span>版本策略：${escapeHtml(editionVersionStrategy())}</span>
        </div>
      </section>
      ${hiddenCoreConfig(draft)}
      ${renderMessageArea()}
    </section>
  `;
}

function renderSecurityPanel(): string {
  const status = state.status;
  const apiState = status?.llm.api_key_configured ? "已配置，不在界面回显" : "未配置";
  const notionState = status?.outputs?.notion_configured ? "已配置" : "未配置";
  const accountsState = state.accounts.length ? `${state.accounts.length} 个本机账号资料` : "未保存账号资料";
  return `
    <div class="privacy-list">
      <span>LLM API Key：${escapeHtml(apiState)}</span>
      <span>Notion：${escapeHtml(notionState)}</span>
      <span>账号登录态：${escapeHtml(accountsState)}</span>
      <span>备份包可能包含配置和登录态，不要公开分享。</span>
      <span>开源版不要提交 config.toml、accounts、cache、data 和本机导出内容。</span>
    </div>
  `;
}

function renderEditionPanel(): string {
  if (!isPrivateEdition) {
    return `
      <section class="panel">
        <div class="section-head">
          <div>
            <span class="eyebrow">Edition</span>
            <h2>开源完整版</h2>
          </div>
          <button data-view="updates">GitHub 更新</button>
        </div>
        <p class="muted">保留 GitHub Release、源码、Docker 和完整功能，适合自己部署或二次开发。</p>
      </section>
    `;
  }
  return `
    <section class="panel">
      <div class="section-head">
        <div>
          <span class="eyebrow">Edition</span>
          <h2>${escapeHtml(editionDisplayName())}</h2>
        </div>
      </div>
      <div class="update-grid">
        <div class="update-card"><span>当前版本</span><b>${escapeHtml(state.appVersion || "未知")}</b></div>
        <div class="update-card ok"><span>升级策略</span><b>固定交付</b></div>
        <div class="update-card"><span>说明</span><b>${escapeHtml(isPersonalEdition ? "个人版只使用本机交付版本。" : "商业版只使用当前交付版本。")}</b></div>
      </div>
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
    ${hidden("cfg-ocr", draft.tools.ocr)}
    ${hiddenOutputConfig(draft)}
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
    ${hiddenOutputConfig(draft)}
  `;
}

function hiddenOutputConfig(draft: AppConfigDraft): string {
  return `
    ${hidden("cfg-output-markdown", draft.outputs.formats.includes("markdown") ? "on" : "")}
    ${hidden("cfg-output-html", draft.outputs.formats.includes("html") ? "on" : "")}
    ${hidden("cfg-output-csv", draft.outputs.formats.includes("csv") ? "on" : "")}
    ${hidden("cfg-output-notion", draft.outputs.formats.includes("notion") ? "on" : "")}
    ${hidden("cfg-output-html-dir", draft.outputs.html_dir)}
    ${hidden("cfg-output-csv-path", draft.outputs.csv_path)}
    ${hidden("cfg-output-notion-token", "")}
    ${hidden("cfg-output-notion-db", draft.outputs.notion_database_id)}
    ${hidden("cfg-output-notion-title", draft.outputs.notion_title_property)}
    ${hidden("cfg-output-notion-api", draft.outputs.notion_api_base)}
  `;
}

function hiddenTemplateConfig(draft: AppConfigDraft): string {
  return `
    ${hiddenAdvancedConfig(draft)}
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
  const progress = state.progressSteps.length
    ? `<div class="progress-steps">
        ${state.progressSteps
          .map(
            (step) => `
              <div class="progress-step ${step.status}">
                <span class="progress-dot"></span>
                <div><b>${escapeHtml(step.label)}</b><small>${escapeHtml(step.detail)}</small></div>
              </div>
            `,
          )
          .join("")}
      </div>`
    : "";
  return `
    ${
      state.busy
        ? `<div class="progress-card"><div class="progress-track"><div class="progress-bar"></div></div><span>${escapeHtml(state.message || "正在运行...")}</span></div>`
        : ""
    }
    ${progress}
    ${state.message && !state.busy ? `<pre class="message">${escapeHtml(state.message)}</pre>` : ""}
    ${state.error ? `<pre class="error">${escapeHtml(state.error)}</pre>` : ""}
  `;
}

function renderBanner(): string {
  if (state.bannerDismissed || !state.doctor) return "";
  const issues = state.doctor.checks.filter((check) => !check.ok && check.required);
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
        <b>环境检查发现 ${issues.length} 项必须处理</b>
        <span class="banner-actions">
          <button data-view="dependencies">去依赖</button>
          <button data-view="setup">去配置</button>
          <button id="dismiss-banner">关闭</button>
        </span>
      </div>
      <ul class="banner-list">${items}</ul>
    </div>
  `;
}

function renderOnboarding(): string {
  if (localStorage.getItem(STORAGE_KEYS.onboardingDone) === "1") return "";
  const status = state.status;
  const requiredMissing = state.dependencies?.items.filter((item) => item.status !== "ready" && item.installable).length ?? 0;
  const steps = [
    {
      label: "选择输出",
      done: Boolean(status?.paths.obsidian_vault),
      view: "setup",
      text: status?.paths.obsidian_vault || "选一个本地输出目录；不用 Obsidian 也能生成 Markdown/HTML/CSV。",
    },
    {
      label: "摘要与 Key",
      done: Boolean(status?.llm.enabled && status.llm.api_key_configured),
      view: "setup",
      text: status?.llm.enabled ? "补 API Key 后可自动摘要和打标签。" : "不开启也能生成基础 Markdown。",
    },
    {
      label: "账号与来源",
      done: state.accounts.length > 0 || (status?.queue.pending ?? 0) > 0 || (status?.queue.done ?? 0) > 0,
      view: state.accounts.length ? "sources" : "accounts",
      text: state.accounts.length ? `${state.accounts.length} 个账号已保存，也可以继续导入链接/RSS/本地目录。` : "账号来源先登录；普通链接、RSS、本地文件可直接导入。",
    },
    {
      label: "检查并运行",
      done: requiredMissing === 0,
      view: requiredMissing === 0 ? "run" : "dependencies",
      text: requiredMissing === 0 ? "环境已就绪，开始抓取或处理队列。" : "安装 yt-dlp / ffmpeg 等工具后可自动处理视频。",
    },
  ];
  return `
    <section class="onboarding">
      <div class="onboarding-head">
        <div>
          <span class="eyebrow">First run</span>
          <h2>${escapeHtml(appBrandName)} 初次使用</h2>
        </div>
        <button id="dismiss-onboarding">完成/稍后再看</button>
      </div>
      <div class="onboarding-steps">
        ${steps
          .map(
            (step, index) => `
              <button class="onboarding-step ${step.done ? "done" : "todo"}" data-view="${step.view}">
                <span>${index + 1}</span>
                <b>${escapeHtml(step.label)}</b>
                <small>${escapeHtml(step.text)}</small>
              </button>
            `,
          )
          .join("")}
      </div>
    </section>
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
  document.querySelectorAll<HTMLButtonElement>("[data-open-output]").forEach((button) => {
    button.addEventListener("click", () => void handleOpenOutput(button.dataset.openOutput ?? ""));
  });
  document.querySelectorAll<HTMLButtonElement>("[data-choose-directory]").forEach((button) => {
    button.addEventListener("click", () => void handleChooseDirectory(button.dataset.chooseDirectory ?? ""));
  });
  document.querySelector<HTMLButtonElement>("#backup-project")?.addEventListener("click", () => void handleBackupProject());
  document.querySelector<HTMLButtonElement>("#choose-backup-file")?.addEventListener("click", () => void handleChooseBackupFile());
  document.querySelector<HTMLButtonElement>("#restore-project")?.addEventListener("click", () => void handleRestoreProject());
  document.querySelector<HTMLButtonElement>("#doctor-json")?.addEventListener("click", () => void handleDoctorJson());
  document.querySelector<HTMLButtonElement>("#export-diagnostics")?.addEventListener("click", () => void handleExportDiagnostics());
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
  document.querySelector<HTMLButtonElement>("#open-latest-release")?.addEventListener("click", () => void handleOpenLatestRelease());
  document.querySelector<HTMLButtonElement>("#template-save-library")?.addEventListener("click", handleSaveTemplateToLibrary);
  document.querySelector<HTMLButtonElement>("#template-load-library")?.addEventListener("click", handleLoadTemplateFromLibrary);
  document.querySelector<HTMLButtonElement>("#template-delete-library")?.addEventListener("click", handleDeleteTemplateFromLibrary);
  document.querySelector<HTMLButtonElement>("#template-import-library")?.addEventListener("click", handleImportTemplateLibrary);
  document.querySelector<HTMLButtonElement>("#save-source-plugin")?.addEventListener("click", handleSaveSourcePlugin);
  document.querySelectorAll<HTMLButtonElement>("[data-apply-source-plugin]").forEach((button) => {
    button.addEventListener("click", () => handleApplySourcePlugin(button.dataset.applySourcePlugin ?? ""));
  });
  document.querySelectorAll<HTMLButtonElement>("[data-delete-source-plugin]").forEach((button) => {
    button.addEventListener("click", () => handleDeleteSourcePlugin(button.dataset.deleteSourcePlugin ?? ""));
  });
  document.querySelector<HTMLButtonElement>("#dismiss-banner")?.addEventListener("click", () => {
    state.bannerDismissed = true;
    render();
  });
  document.querySelector<HTMLButtonElement>("#dismiss-onboarding")?.addEventListener("click", () => {
    localStorage.setItem(STORAGE_KEYS.onboardingDone, "1");
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
  app.innerHTML = `<div class="shell ${editionShellClass()}"><aside><div class="brand"><b>${escapeHtml(appBrandName)}</b><span>${escapeHtml(appBrandSubtitle)}</span></div>${renderNav()}</aside><main>${renderBanner()}${renderOnboarding()}${renderView()}</main></div>`;
  bindEvents();
}

function disabledAttr(): string {
  return state.busy ? "disabled" : "";
}

function pathField(label: string, id: string, value: string): string {
  return renderPathField(label, id, value, state.busy);
}

render();
void init();
