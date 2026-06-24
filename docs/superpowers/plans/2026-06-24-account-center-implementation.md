# 统一账号中心与 v0.04 完整交付实施计划

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 本次按用户要求由当前会话直接连续执行，不创建 subagent。

**目标：** 将抖音、哔哩哔哩、YouTube、TikTok 的账号登录、切换、校验和采集统一集成到桌面软件，完成独立安装包、真实回归、GitHub `v0.04` 发布及全项目复查。

**架构：** Python 后端新增账号领域层、平台适配层和 Playwright Edge 持久化登录层；账号元数据写入应用工作区，浏览器登录态保存在每个账号独立的 Edge profile 中。采集任务只在运行期间导出临时 Cookie，并在任务结束后删除。Tauri 负责长时登录命令和桌面端桥接，前端提供独立一级“账号”页面并在采集页面显示当前账号。

**技术栈：** Python 3.11、Playwright、yt-dlp、Tauri 2、Rust、TypeScript、Vite、unittest、PyInstaller、GitHub Actions。

---

## Task 1：固化现有抖音采集修复

- [x] 复核 `src/obsidian_ingest/acquire.py`、`src/obsidian_ingest/collectors/douyin.py` 和 `tests/test_collectors.py` 的未提交修改。
- [x] 运行采集器与获取层相关测试，确认 UTF-8 输出、文本优先和视频回退行为。
- [x] 删除不再需要的根目录 `切换抖音账号.cmd`，避免形成软件外的第二套入口。
- [x] 提交为独立中文提交，保留后续账号中心接线的清晰基线。

## Task 2：建立账号领域模型与持久化

**Files:**
- Create: `src/obsidian_ingest/accounts/__init__.py`
- Create: `src/obsidian_ingest/accounts/models.py`
- Create: `src/obsidian_ingest/accounts/store.py`
- Test: `tests/test_accounts_store.py`

- [x] 先写失败测试，覆盖四个平台枚举、账号增删切换、单平台唯一当前账号、原子写入和损坏文件恢复。
- [x] 实现不含明文 Cookie 的 `accounts.json` 元数据结构。
- [x] 为每个账号创建独立 `accounts/profiles/<platform>/<account-id>/` 浏览器目录。
- [x] 运行账号存储测试并提交。

## Task 3：实现平台身份识别适配器

**Files:**
- Create: `src/obsidian_ingest/accounts/providers/base.py`
- Create: `src/obsidian_ingest/accounts/providers/douyin.py`
- Create: `src/obsidian_ingest/accounts/providers/bilibili.py`
- Create: `src/obsidian_ingest/accounts/providers/youtube.py`
- Create: `src/obsidian_ingest/accounts/providers/tiktok.py`
- Test: `tests/test_account_providers.py`

- [x] 先写失败测试，覆盖登录 URL、登录成功判定、昵称与平台 ID 清洗、未登录与页面结构异常。
- [x] 为抖音解析昵称和抖音号，为哔哩哔哩解析 `nav` 接口，为 YouTube/TikTok 提供页面身份识别。
- [x] 所有适配器返回统一候选账号结构和明确错误码。
- [x] 运行适配器测试并提交。

## Task 4：实现 Edge 隔离登录与临时 Cookie

**Files:**
- Create: `src/obsidian_ingest/accounts/browser.py`
- Test: `tests/test_account_browser.py`
- Modify: `pyproject.toml`

- [x] 先写失败测试，覆盖 Edge 定位、持久 profile 参数、Netscape Cookie 导出和临时文件清理。
- [x] 使用系统 Microsoft Edge，不下载 Chromium。
- [x] 使用 Playwright persistent context 打开每个账号独立 profile。
- [x] 密码和二次验证只在平台网页输入，不进入应用日志或元数据。
- [x] 任务运行时导出临时 Cookie 文件，`finally` 中删除。
- [x] 增加 Playwright 运行依赖并运行测试。

## Task 5：实现账号服务、旧账号迁移与 CLI

**Files:**
- Create: `src/obsidian_ingest/accounts/service.py`
- Create: `src/obsidian_ingest/accounts/migration.py`
- Modify: `src/obsidian_ingest/cli.py`
- Test: `tests/test_account_service.py`
- Test: `tests/test_cli_accounts.py`

- [x] 先写失败测试，覆盖列表、开始登录、候选确认、取消、切换、校验、重新登录和删除。
- [x] 登录命令等待浏览器登录成功后只保存候选，不直接替换当前账号。
- [x] 确认命令写入账号并按用户选择切换；取消命令清理候选 profile。
- [x] 自动迁移现有抖音登录态，识别为“忆霖 / 60185413619”，迁移前保留原配置备份。
- [x] CLI 所有结果使用稳定 JSON，错误包含平台、错误码和可执行修复提示。
- [x] 运行服务与 CLI 测试并提交。

## Task 6：将账号接入四平台采集

**Files:**
- Modify: `src/obsidian_ingest/config.py`
- Modify: `src/obsidian_ingest/acquire.py`
- Modify: `src/obsidian_ingest/collectors/douyin.py`
- Modify: `src/obsidian_ingest/collectors/platform_lists.py`
- Modify: `src/obsidian_ingest/pipeline.py`
- Test: `tests/test_acquire.py`
- Test: `tests/test_collectors.py`
- Test: `tests/test_pipeline.py`

- [x] 先写失败测试，验证每个需要登录的平台都使用当前账号。
- [x] 抖音运行时从当前账号生成临时下载配置。
- [x] 哔哩哔哩、YouTube、TikTok 的 yt-dlp 列表与下载命令传入临时 Cookie。
- [x] 未配置账号、账号失效、导出失败时拒绝静默降级，并返回明确提示。
- [x] 无需登录的普通网页、PDF、播客和本地文件保持原有路径。
- [x] 运行采集和流水线测试并提交。

## Task 7：扩展 Tauri 后端命令

**Files:**
- Modify: `desktop/src-tauri/src/commands.rs`
- Modify: `desktop/src-tauri/src/python_bridge.rs`
- Modify: `desktop/src-tauri/src/lib.rs`
- Test: Rust unit tests where practical

- [ ] 新增账号列表、登录、确认、取消、切换、校验、重新登录和删除命令。
- [ ] 登录与校验使用独立长超时，普通命令保持当前短超时。
- [ ] Python JSON 错误完整映射到前端，不泄露 Cookie、路径中的密钥或网页凭据。
- [ ] 运行 `cargo fmt --check`、`cargo check` 和 Rust 测试。

## Task 8：实现桌面端统一账号页面

**Files:**
- Modify: `desktop/src/types.ts`
- Modify: `desktop/src/api.ts`
- Modify: `desktop/src/state.ts`
- Modify: `desktop/src/main.ts`
- Modify: `desktop/src/styles.css`

- [ ] 增加一级导航“账号”，四个平台用紧凑列表显示账号、状态和当前标记。
- [ ] 支持添加、候选确认、取消、快速切换、校验、重新登录和删除。
- [ ] 添加账号时说明将打开独立 Edge 登录窗口，候选身份必须二次确认。
- [ ] 在运行与来源页面显示任务将使用的平台和当前账号。
- [ ] 加载、空状态、超时、登录失效、冲突和删除当前账号均有完整交互。
- [ ] 使用现有图标库和现有桌面设计语言，不增加软件外入口。
- [ ] 运行前端类型检查和生产构建，并通过浏览器截图检查桌面与窄屏布局。

## Task 9：更新版本、打包和文档

**Files:**
- Modify: `desktop/package.json`
- Modify: `desktop/src-tauri/Cargo.toml`
- Modify: `desktop/src-tauri/tauri.conf.json`
- Modify: `desktop/src/main.ts`
- Modify: `packaging/build-sidecar.ps1`
- Modify: `.github/workflows/release-windows.yml`
- Modify: `README.md`
- Modify: user guide Markdown

- [ ] 将软件版本统一更新为 `0.4.0`。
- [ ] PyInstaller 收集 Playwright Python 运行文件，但继续使用系统 Edge。
- [ ] Windows 发布工作流安装完整项目依赖、构建 sidecar、Tauri 安装包并上传 Release。
- [ ] 更新安装、首次启动、账号切换、采集和故障排查说明。
- [ ] 所有新增说明文档加入 `自动化写的 / 署名：小黄狗`。

## Task 10：完整自动化与真实回归

- [ ] 运行全部 Python 单元测试。
- [ ] 运行 `doctor`、前端构建、Rust 格式/检查/测试。
- [ ] 迁移并验证现有抖音账号，执行一次真实收藏获取与完整入库回归。
- [ ] 验证哔哩哔哩、YouTube、TikTok 的登录入口、账号识别和采集鉴权路径；没有现成登录态时明确记录需要用户在平台页面完成登录，不伪造成功。
- [ ] 构建 Windows 独立安装包，并在干净工作目录验证启动和账号页面。
- [ ] 检查日志和临时目录，确认 Cookie 临时文件已清除、日志无凭据。

## Task 11：全项目复查、修复与发布

- [ ] 按代码审查标准检查账号安全、并发、错误恢复、升级兼容、UI 状态和测试盲区。
- [ ] 对发现的问题逐项补测试并修复，再重新执行全部验证。
- [ ] 更新最终合并说明，使用自然中文描述，不出现 AI 痕迹。
- [ ] 提交并推送全部变更。
- [ ] 创建并推送 `v0.04` 标签，发布 GitHub Release 与 Windows 安装包。
- [ ] 最终报告真实完成项、验证结果、安装包位置和仍需平台网页人工登录的客观边界。

---

自动化写的  
署名：小黄狗
