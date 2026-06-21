import "./styles.css";
import {
  clipWebpage,
  collectPlatformList,
  collectRss,
  collectDouyin,
  getQueue,
  getStatus,
  importLinks,
  knowledgeMaintenance,
  listRecentLogs,
  processQueue,
  retryFailed,
  retryItem,
  runDoctor,
  scanDirectory,
  scanInbox,
  skipItem,
  writeLauncher,
} from "./api";
import { state, setBusy, setError, setMessage } from "./state";

const appRoot = document.querySelector<HTMLDivElement>("#app");

if (!appRoot) {
  throw new Error("missing #app root");
}

const app = appRoot;

async function refresh(): Promise<void> {
  try {
    state.status = await getStatus();
    state.queue = await getQueue(50);
    state.logs = await listRecentLogs(20);
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  }
  render();
}

async function runAction(label: string, action: () => Promise<{ ok: boolean; stdout: string; stderr: string }>): Promise<void> {
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
    state.status = await getStatus();
    state.queue = await getQueue(50);
    state.logs = await listRecentLogs(20);
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    setBusy(false);
    render();
  }
}

async function handleDouyin(): Promise<void> {
  const raw = window.prompt("本次要转化多少个抖音收藏？", "5");
  if (raw === null) return;
  const count = Number.parseInt(raw, 10);
  if (!Number.isFinite(count) || count < 1 || count > 100) {
    setError("请输入 1 到 100 之间的整数。");
    render();
    return;
  }
  await runAction(`处理 ${count} 个抖音收藏`, async () => {
    const collect = await collectDouyin(count);
    if (!collect.ok) return collect;
    return processQueue(count);
  });
}

async function handleDirectoryScan(): Promise<void> {
  const raw = window.prompt("要扫描哪个本地文件夹？", "D:\\Downloads");
  const directory = raw?.trim();
  if (!directory) return;
  await runAction("扫描下载目录", () => scanDirectory(directory));
}

async function handleRss(): Promise<void> {
  const raw = window.prompt("本次每个 RSS 源最多导入多少条？", "10");
  if (raw === null) return;
  const limit = Number.parseInt(raw, 10);
  if (!Number.isFinite(limit) || limit < 1 || limit > 100) {
    setError("请输入 1 到 100 之间的整数。");
    render();
    return;
  }
  await runAction("导入 RSS", () => collectRss(limit));
}

async function handleWebpage(): Promise<void> {
  const raw = window.prompt("要剪藏哪个网页 URL 或本地 HTML 文件？", "https://example.com");
  const url = raw?.trim();
  if (!url) return;
  await runAction("网页剪藏", () => clipWebpage(url));
}

async function handlePlatformList(platform: "youtube" | "bilibili" | "auto"): Promise<void> {
  const label = platform === "youtube" ? "YouTube playlist / channel" : platform === "bilibili" ? "B站收藏夹 / 合集" : "平台列表";
  const rawUrl = window.prompt(`粘贴 ${label} 链接`, platform === "youtube" ? "https://www.youtube.com/playlist?list=" : "https://www.bilibili.com/");
  const url = rawUrl?.trim();
  if (!url) return;
  const rawLimit = window.prompt("本次最多导入多少条？", "20");
  if (rawLimit === null) return;
  const limit = Number.parseInt(rawLimit, 10);
  if (!Number.isFinite(limit) || limit < 1 || limit > 200) {
    setError("请输入 1 到 200 之间的整数。");
    render();
    return;
  }
  await runAction(`导入 ${label}`, () => collectPlatformList(url, platform, limit));
}

async function handleRetryFailed(): Promise<void> {
  const raw = window.prompt("本次最多重试多少个失败项？", "20");
  if (raw === null) return;
  const limit = Number.parseInt(raw, 10);
  if (!Number.isFinite(limit) || limit < 1 || limit > 200) {
    setError("请输入 1 到 200 之间的整数。");
    render();
    return;
  }
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

function setView(view: typeof state.activeView): void {
  state.activeView = view;
  render();
}

function renderNav(): string {
  const items: Array<[typeof state.activeView, string]> = [
    ["run", "运行"],
    ["sources", "来源"],
    ["queue", "队列"],
    ["logs", "日志"],
    ["knowledge", "知识库"],
    ["settings", "设置"],
  ];
  return items
    .map(
      ([key, label]) =>
        `<button class="nav-item ${state.activeView === key ? "active" : ""}" data-view="${key}">${label}</button>`,
    )
    .join("");
}

function renderView(): string {
  if (state.activeView === "run") return renderRunView();
  if (state.activeView === "sources") return renderSourcesView();
  if (state.activeView === "queue") return renderQueueView();
  if (state.activeView === "logs") return renderLogsView();
  if (state.activeView === "knowledge") return renderKnowledgeView();
  return renderSettingsView();
}

function renderRunView(): string {
  const counts = state.status?.queue ?? {};
  const disabled = state.busy ? "disabled" : "";
  return `
    <section class="view">
      <div class="view-header">
        <h1>学习资料入库</h1>
        <button id="refresh" ${disabled}>刷新</button>
      </div>
      <div class="stats">
        <div class="stat"><b>${counts.pending ?? 0}</b><span>待处理</span></div>
        <div class="stat"><b>${counts.done ?? 0}</b><span>已完成</span></div>
        <div class="stat"><b>${counts.failed ?? 0}</b><span>失败</span></div>
      </div>
      <div class="actions">
        <button id="run-douyin" ${disabled}>处理抖音收藏</button>
        <button id="run-links" ${disabled}>导入 links.txt</button>
        <button id="run-inbox" ${disabled}>扫描 inbox</button>
        <button id="run-directory" ${disabled}>扫描下载目录</button>
        <button id="run-rss" ${disabled}>导入 RSS</button>
        <button id="clip-webpage" ${disabled}>网页剪藏</button>
        <button id="run-youtube" ${disabled}>导入 YouTube 列表</button>
        <button id="run-bilibili" ${disabled}>导入 B站列表</button>
        <button id="process-queue" ${disabled}>处理队列</button>
        <button id="retry-failed" ${disabled}>重试失败项</button>
        <button id="doctor" ${disabled}>运行 doctor</button>
        <button id="write-launcher" ${disabled}>生成启动器</button>
      </div>
      ${state.message ? `<pre class="message">${escapeHtml(state.message)}</pre>` : ""}
      ${state.error ? `<pre class="error">${escapeHtml(state.error)}</pre>` : ""}
    </section>
  `;
}

function renderSourcesView(): string {
  const cards = [
    ["抖音收藏", "可用", "点击运行页按钮后输入数量"],
    ["links.txt", "可用", "从项目 links.txt 导入"],
    ["inbox", "可用", "扫描本地资料文件夹"],
    ["下载目录扫描", "可用", "手动输入目录后扫描"],
    ["RSS", "可用", "读取项目 feeds.txt"],
    ["网页剪藏", "可用", "输入网页 URL 或本地 HTML"],
    ["YouTube 播放列表 / 频道", "可用", "通过 yt-dlp 平铺列表后入队"],
    ["B站收藏 / 合集", "可用", "公开列表直接导入，私有收藏需要 Cookie"],
  ];
  return `
    <section class="view">
      <h1>来源</h1>
      <div class="cards">
        ${cards
          .map(
            ([name, status, desc]) =>
              `<article class="card"><h2>${name}</h2><b>${status}</b><p>${desc}</p></article>`,
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderQueueView(): string {
  return `
    <section class="view">
      <h1>队列</h1>
      <table>
        <thead><tr><th>ID</th><th>状态</th><th>标题</th><th>平台</th><th>输出</th><th>操作</th></tr></thead>
        <tbody>
          ${state.queue
            .map(
              (item) =>
                `<tr>
                  <td>${item.id}</td>
                  <td>${item.status}</td>
                  <td>${escapeHtml(item.title ?? item.url)}</td>
                  <td>${item.platform}</td>
                  <td>${escapeHtml(item.note_path ?? "")}</td>
                  <td class="row-actions">
                    <button data-retry-id="${item.id}" ${state.busy ? "disabled" : ""}>重试</button>
                    <button data-skip-id="${item.id}" ${state.busy ? "disabled" : ""}>跳过</button>
                  </td>
                </tr>`,
            )
            .join("")}
        </tbody>
      </table>
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
  const disabled = state.busy ? "disabled" : "";
  return `
    <section class="view">
      <div class="view-header">
        <h1>知识库</h1>
        <button id="knowledge-maintenance" ${disabled}>生成知识库报告</button>
      </div>
      <div class="settings">
        <p><b>输出目录：</b>${escapeHtml(state.status?.paths.obsidian_vault ?? "")}\\Obsidian Ingest Pipeline</p>
        <p>会生成入库总览、每周入库报告、重复内容检查、双链建议。</p>
      </div>
    </section>
  `;
}

function renderSettingsView(): string {
  const status = state.status;
  return `
    <section class="view">
      <h1>设置</h1>
      <div class="settings">
        <p><b>项目：</b>${escapeHtml(status?.paths.project_root ?? "")}</p>
        <p><b>Vault：</b>${escapeHtml(status?.paths.obsidian_vault ?? "")}</p>
        <p><b>队列数据库：</b>${escapeHtml(status?.paths.queue_db ?? "")}</p>
        <p><b>LLM：</b>${escapeHtml(status?.llm.model ?? "")} / ${status?.llm.api_key_configured ? "configured" : "missing"}</p>
      </div>
    </section>
  `;
}

function bindEvents(): void {
  document.querySelectorAll<HTMLButtonElement>("[data-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view as typeof state.activeView));
  });
  document.querySelector<HTMLButtonElement>("#refresh")?.addEventListener("click", refresh);
  document.querySelector<HTMLButtonElement>("#run-douyin")?.addEventListener("click", handleDouyin);
  document.querySelector<HTMLButtonElement>("#run-links")?.addEventListener("click", () => runAction("导入 links.txt", importLinks));
  document.querySelector<HTMLButtonElement>("#run-inbox")?.addEventListener("click", () => runAction("扫描 inbox", scanInbox));
  document.querySelector<HTMLButtonElement>("#run-directory")?.addEventListener("click", handleDirectoryScan);
  document.querySelector<HTMLButtonElement>("#run-rss")?.addEventListener("click", handleRss);
  document.querySelector<HTMLButtonElement>("#clip-webpage")?.addEventListener("click", handleWebpage);
  document.querySelector<HTMLButtonElement>("#run-youtube")?.addEventListener("click", () => handlePlatformList("youtube"));
  document.querySelector<HTMLButtonElement>("#run-bilibili")?.addEventListener("click", () => handlePlatformList("bilibili"));
  document.querySelector<HTMLButtonElement>("#process-queue")?.addEventListener("click", () => runAction("处理队列", () => processQueue(10)));
  document.querySelector<HTMLButtonElement>("#retry-failed")?.addEventListener("click", handleRetryFailed);
  document.querySelector<HTMLButtonElement>("#doctor")?.addEventListener("click", () => runAction("doctor", runDoctor));
  document.querySelector<HTMLButtonElement>("#write-launcher")?.addEventListener("click", () => runAction("生成启动器", writeLauncher));
  document.querySelector<HTMLButtonElement>("#knowledge-maintenance")?.addEventListener("click", () => runAction("生成知识库报告", knowledgeMaintenance));
  document.querySelectorAll<HTMLButtonElement>("[data-retry-id]").forEach((button) => {
    button.addEventListener("click", () => handleRetryItem(Number.parseInt(button.dataset.retryId ?? "0", 10)));
  });
  document.querySelectorAll<HTMLButtonElement>("[data-skip-id]").forEach((button) => {
    button.addEventListener("click", () => handleSkipItem(Number.parseInt(button.dataset.skipId ?? "0", 10)));
  });
}

function render(): void {
  app.innerHTML = `<div class="shell"><aside><div class="brand">Obsidian Ingest</div>${renderNav()}</aside><main>${renderView()}</main></div>`;
  bindEvents();
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

render();
refresh();
