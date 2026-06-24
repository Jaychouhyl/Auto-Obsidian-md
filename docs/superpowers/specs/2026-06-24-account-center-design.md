# Obsidian Ingest Studio 账号中心设计

日期：2026-06-24
目标版本：v0.04 / 0.4.0

## 1. 目标

把所有需要平台登录态的能力统一放进 Obsidian Ingest Studio，不再要求用户寻找脚本、手工复制 Cookie 或编辑配置文件。

首版支持：

- 抖音
- B站
- YouTube
- TikTok

DeepSeek API Key 和 Obsidian REST Key 仍属于应用配置，不放入账号中心。

## 2. 已确认的产品决策

- 使用独立的一级导航“账号”。
- 每个平台可以保存多个账号档案。
- 每个平台有且只有一个当前使用账号。
- 登录和换号通过系统 Microsoft Edge 独立登录窗口完成。
- 检测到新账号后先展示昵称和平台 ID，用户确认后才生效。
- 旧账号不会被覆盖；切换失败不影响当前账号。
- 凭证只保存在当前 Windows 用户本机。
- 抓取页面显示当前使用账号。

## 3. 页面设计

账号页面按平台显示四张卡片。每张卡片包含：

- 平台名称和图标
- 当前账号昵称
- 平台账号 ID
- 登录状态
- 最近验证时间
- 当前账号支持的采集能力
- 已保存账号数量
- 添加账号、切换、验证、重新登录、删除操作

统一状态：

- `未登录`
- `需要验证`
- `已登录`
- `已失效`
- `受风控限制`
- `工具缺失`
- `平台暂不支持`

“运行”和“导入”页面的账号相关操作必须显示当前账号。没有登录时，公开内容仍然可以采集；遇到必须登录的来源时，软件跳转账号页面，不得静默生成假成功笔记。

## 4. 登录与换号流程

### 4.1 添加账号

1. 用户点击平台卡片中的“添加账号”。
2. 软件创建独立账号资料目录并启动 Microsoft Edge 登录窗口。
3. 用户只在平台官网输入密码、扫码或验证码。
4. 软件轮询登录状态，识别昵称和平台 ID。
5. 软件显示待确认账号。
6. 用户确认后保存账号档案并设为当前账号。
7. 用户取消或登录失败时删除未完成的临时资料，不改变现有账号。

### 4.2 切换账号

1. 用户从已保存账号列表选择目标账号。
2. 软件先验证目标登录态。
3. 验证成功后切换当前账号。
4. 登录态失效时引导重新登录。
5. 重新登录失败时继续使用原当前账号。

### 4.3 删除账号

- 删除前二次确认。
- 删除该账号的浏览器资料目录和临时 Cookie。
- 删除当前账号后，优先选择同平台其他有效账号。
- 没有其他有效账号时，平台状态变为未登录。

## 5. 本地数据结构

账号数据位于应用工作区：

```text
accounts/
  accounts.json
  douyin/
    <account-id>/
      profile/
  bilibili/
    <account-id>/
      profile/
  youtube/
    <account-id>/
      profile/
  tiktok/
    <account-id>/
      profile/
  backups/
```

`accounts.json` 只保存非敏感元数据：

- 内部账号 ID
- 平台
- 昵称
- 平台账号 ID
- 当前账号标记
- 状态
- 创建时间
- 最近验证时间
- 资料目录相对路径

Edge 登录资料由 Chromium/Windows DPAPI 管理。软件不保存密码。需要向下载器传递 Cookie 时，只生成任务级临时 Cookie 文件，并在任务结束后删除。

账号档案、备份、Cookie 和浏览器资料必须被 Git 忽略，不得进入安装包或日志。

## 6. 后端边界

新增独立账号模块，避免把平台登录逻辑塞进采集器：

```text
src/obsidian_ingest/accounts/
  models.py
  store.py
  browser.py
  service.py
  providers/
    douyin.py
    bilibili.py
    youtube.py
    tiktok.py
```

职责：

- `models.py`：账号、状态和验证结果数据模型。
- `store.py`：账号元数据的原子读写、当前账号切换和目录管理。
- `browser.py`：启动 Edge 持久化资料、等待登录、导出任务级 Cookie。
- `service.py`：添加、验证、切换、删除、迁移等用例。
- `providers/*`：平台网址、账号识别和登录状态判断。

CLI 增加机器可读命令：

```text
accounts list --json
accounts begin-login --platform <platform> --json
accounts confirm-login --session <id> --json
accounts verify --platform <platform> --account <id> --json
accounts switch --platform <platform> --account <id> --json
accounts delete --platform <platform> --account <id> --json
accounts migrate-douyin --json
```

桌面端通过 Tauri command 调用同一套后端，不维护第二套账号逻辑。

## 7. 平台适配

### 7.1 抖音

- 识别昵称和抖音号。
- 当前账号用于收藏视频抓取。
- 每次抓取前把当前账号 Cookie 写入本次运行的临时 `douyin-config.yml`。
- 现有“忆霖”登录态自动迁移为第一个账号档案。
- 迁移验证成功后备份旧 `.cookies.json` 和 `douyin-config.yml`，原文件在 v0.04 兼容期内保留。

### 7.2 B站

- 识别昵称和 UID。
- 当前账号 Cookie 传给 `yt-dlp`。
- 支持单视频、合集以及 `yt-dlp` 能解析的公开/私有收藏来源。
- 平台不允许或工具不支持时返回明确错误。

### 7.3 YouTube

- 识别 YouTube/Google 页面显示名称。
- 当前账号用于需要登录、年龄限制、稍后观看和私有播放列表等来源。
- 独立 Edge 登录被 Google 风控阻止时，允许连接用户指定的现有 Chrome/Edge 浏览器资料。

### 7.4 TikTok

- 识别昵称和用户名。
- 当前账号用于受限视频和 `yt-dlp` 可解析的私有来源。
- 不承诺平台或工具本身不支持的私有 API。

## 8. 采集流程接线

账号能力必须接入真实采集命令：

- `acquire_source` 根据平台取得当前账号的任务级 Cookie 参数。
- `collect_platform_list` 对 B站、YouTube、TikTok 使用当前账号。
- `collect_douyin_favorites` 使用当前抖音账号生成临时运行配置。
- 临时 Cookie 和临时配置使用 `try/finally` 清理。
- 没有账号但来源公开时继续运行。
- 来源要求登录但没有有效账号时返回结构化错误和账号页跳转提示。

## 9. 桌面端命令

新增 Tauri commands：

- `list_accounts`
- `begin_account_login`
- `confirm_account_login`
- `verify_account`
- `switch_account`
- `delete_account`
- `migrate_douyin_account`

登录属于长操作，不使用普通 180 秒命令超时。登录会话必须支持取消，并向前端报告：

- 等待浏览器
- 等待登录
- 已识别账号
- 等待确认
- 完成
- 失败

## 10. 错误处理

- Edge 不存在：提示安装或选择现有浏览器。
- 登录窗口被关闭：取消会话，不修改账号。
- 验证码/风控：状态标为受风控限制，保留资料以便重试。
- Cookie 失效：标为已失效，不删除账号。
- 账号识别失败：不允许确认保存。
- 临时 Cookie 写入失败：停止采集，不回退到其他账号。
- 平台不支持：显示平台暂不支持，不生成占位成功笔记。
- 日志只记录平台、内部账号 ID 和状态，不记录 Cookie、Token、密码或完整请求头。

## 11. 测试策略

### 自动化测试

- 账号元数据创建、更新、切换、删除和原子写入。
- 每个平台账号状态解析。
- 未登录、失效、风控和识别失败。
- 当前账号选择规则。
- 抖音旧配置迁移。
- Cookie 临时文件创建与清理。
- `yt-dlp` 和 `douyin-dl` 命令参数接线。
- Tauri command 参数和前端账号状态渲染。
- 安装包中账号模块和浏览器依赖完整。

新行为按红、绿、重构流程实现。

### 真实回归

- 抖音：现有账号迁移、验证、抓取指定数量、转写、DeepSeek 总结、写入真实 Obsidian。
- B站：真实登录验证和带账号的单视频/列表命令。
- YouTube：真实登录验证和带账号的列表命令；无法登录时验证现有浏览器资料兜底。
- TikTok：真实登录验证和带账号的视频命令。
- 账号切换失败不得影响原账号。
- 临时 Cookie 文件在任务结束后不存在。

真实平台测试需要用户在登录窗口完成扫码或验证码。

## 12. 发布验收

发布版本为 `v0.04`，应用版本为 `0.4.0`。

发布前必须满足：

- Python 全量测试通过。
- 前端生产构建通过。
- Rust 格式与编译检查通过。
- sidecar 独立构建通过。
- Tauri NSIS 安装包构建通过。
- 干净临时工作区首次启动通过。
- 账号中心可以添加、验证、切换和删除账号。
- Git 工作区干净。
- 私有配置、Cookie 和账号目录未提交。
- GitHub Actions 成功并发布可下载安装包。

---

> 自动化写的
> 署名：小黄狗
