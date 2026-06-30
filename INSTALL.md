# 安装与首次配置

## Windows 安装

1. 从 GitHub Releases 下载开源完整版 Windows 安装包，或使用本机打出的个人版安装包。
2. 安装后启动 `Ingest Studio`（开源完整版）或 `Knowledge Studio`（个人版）。
3. 在“配置”页填写 Obsidian vault 路径。
4. 填写 DeepSeek / OpenAI-compatible 服务地址、模型和 API Key。
5. 点击“保存”。
6. 打开“依赖”页，点击“安装缺失工具”，让软件自动准备 `yt-dlp` 和 `ffmpeg`。
7. 点击“健康检查”或“重新检测”，确认核心项为 OK。
8. 打开“账号”页，按需添加抖音、哔哩哔哩、YouTube 或 TikTok 账号。

## 普通用户依赖

只使用 Windows 安装包时，不需要安装 Python、Node.js 或 Rust。

账号登录会打开系统 Microsoft Edge。软件不会读取或保存密码；登录态由 Edge profile 保护。

软件内“依赖”页可自动安装：

```text
ffmpeg
yt-dlp
```

这些用于 B站、YouTube、TikTok 等视频下载和媒体处理。

仍需要手动配置：

```text
douyin-dl
whisper 或 FunASR
DeepSeek API Key
平台账号登录态
```

只做网页、RSS、本地文本/PDF 入库时，可以先不处理媒体工具。

## 配置文件

默认本机配置：

```text
%LOCALAPPDATA%\Obsidian Ingest Studio\config.toml
```

个人版/商业版同样是本地工作区优先；备份包可在“配置”页创建，可能包含账号登录态和本机来源列表，不要公开上传。

不会提交到 Git：

```text
config.toml
douyin-config.yml
links.txt
feeds.txt
data/
cache/
logs/
accounts/
```

## 常用入口

桌面端：

```text
Ingest Studio / Knowledge Studio
```

命令行：

```powershell
cd <项目目录>
.\run.ps1 doctor --config .\config.toml
.\run.ps1 dependencies report --json --config .\config.toml
.\run.ps1 dependencies install --json --config .\config.toml
.\run.ps1 queue --json --config .\config.toml
.\run.ps1 backup --json --config .\config.toml
```

---

自动化写的
署名：小黄狗
