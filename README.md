# Auto Obsidian MD

本地优先的学习资料入库工具。它把视频链接、网页、RSS、本地 PDF、字幕、音频、下载目录等资料加入队列，经过下载、转写、摘要和分类后写成 Obsidian Markdown。

## 主要能力

- 单链接入队：抖音、B站、YouTube、TikTok、网页、本地文件。
- 批量入口：`links.txt`、`inbox`、任意目录扫描。
- 来源采集：RSS / Atom、网页剪藏、YouTube 播放列表 / 频道、B站公开合集 / 收藏链接。
- 内容处理：PDF 文本抽取、字幕清洗、音视频转写、OpenAI-compatible LLM 摘要。
- 知识组织：写入主题标签，按配置里的真实 Obsidian 文件夹路由。
- 写入方式：直接写入本地 Obsidian vault，或接 Obsidian Local REST API。
- 队列维护：查看状态、重试失败项、跳过条目。
- 桌面控制台：Tauri 本机应用，调用同一套 Python pipeline。
- Docker：提供可选的 CLI 容器运行方式。

## 目录结构

```text
src/obsidian_ingest      Python 入库引擎
desktop                  Tauri 桌面控制台
packaging                Windows sidecar 打包脚本
automation               Windows 批处理脚本
tests                    Python 回归测试
Dockerfile               CLI 容器镜像
docker-compose.yml       Docker Compose 入口
config.example.toml      本机配置模板
config.docker.toml       Docker 配置模板
INSTALL.md               安装说明
RELEASE.md               发布清单
```

## 本机快速开始

```powershell
cd <项目目录>
py -3 -m unittest discover -s tests -v
.\run.ps1 doctor --config .\config.toml
```

添加并处理一条资料：

```powershell
.\run.ps1 add "https://www.bilibili.com/video/BVxxxx" --title "学习视频" --config .\config.toml
.\run.ps1 run --once --limit 1 --config .\config.toml
```

## 常用命令

```powershell
# 批量导入 links.txt
.\run.ps1 import-links .\links.txt --config .\config.toml

# 扫描 inbox
.\run.ps1 scan-inbox --config .\config.toml

# 扫描任意目录
.\run.ps1 scan-directory --dir <资料目录> --json --config .\config.toml

# RSS / Atom
.\run.ps1 collect-rss --feeds .\feeds.txt --limit 20 --json --config .\config.toml

# 网页剪藏
.\run.ps1 clip-webpage "https://example.com/article" --json --config .\config.toml

# YouTube / B站列表
.\run.ps1 collect-list "https://www.youtube.com/playlist?list=xxxx" --platform youtube --limit 20 --json --config .\config.toml
.\run.ps1 collect-list "https://www.bilibili.com/..." --platform bilibili --limit 20 --json --config .\config.toml

# 队列维护
.\run.ps1 queue --status failed --json --config .\config.toml
.\run.ps1 retry-failed --limit 20 --json --config .\config.toml
.\run.ps1 skip 123 --reason "不再需要" --json --config .\config.toml

# 机器可读健康检查
.\run.ps1 doctor --json --config .\config.toml
```

## 桌面控制台

普通用户直接下载 Release 里的 Windows 安装包即可，不需要安装 Python、Node.js 或 Rust。安装后，桌面端会在当前 Windows 用户的 AppData 目录创建工作区，并把配置、队列、缓存和导入文件放在那里。

开发运行：

```powershell
cd <项目目录>
py -3 -m pip install pyinstaller
.\packaging\build-sidecar.ps1
```

```powershell
cd <项目目录>\desktop
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
npm run tauri dev
```

打包 Windows 安装包：

```powershell
cd <项目目录>
.\packaging\build-sidecar.ps1

cd .\desktop
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
npm run tauri build
```

构建产物会在：

```text
desktop/src-tauri/target/release/bundle/nsis/
```

如果当前 PowerShell 找不到 `cargo`，先临时加入 PATH：

```powershell
$env:Path="$env:USERPROFILE\.cargo\bin;$env:Path"
```

## Docker

Docker 配置文件位于：

```text
Dockerfile
docker-compose.yml
config.docker.toml
.env.example
```

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

启动 Docker Desktop 后，如果想在 Containers 页面看到一个常驻容器，运行：

```powershell
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' compose up -d --build console
```

只做一次性检查或批处理时，运行：

```powershell
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' compose run --rm ingest doctor --config /app/config.docker.toml
```

`compose run --rm` 会在命令结束后删除临时容器，所以它不会长期显示在 Docker Desktop 的 Containers 页面。

默认镜像不安装 Whisper，避免第一次构建过大。需要容器内转写时，把 `.env` 里的 `INSTALL_WHISPER=false` 改成：

```text
INSTALL_WHISPER=true
```

再重新构建：

```powershell
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' compose build --no-cache ingest
```

## 配置注意

- `config.toml` 是本机私有配置，不提交。
- `douyin-config.yml` 可能包含 Cookie，不提交。
- `links.txt`、`feeds.txt` 可能包含个人资料来源，不提交。
- DeepSeek 或其他 LLM Key 通过环境变量提供。
- 私有 B站/YouTube 收藏需要有效登录态或先导出链接。

## 验证

```powershell
cd <项目目录>
$env:PYTHONPATH = "$PWD\src"
py -3 -m unittest discover -s tests -v

cd .\desktop
npm run build

cd .\src-tauri
$env:Path="$env:USERPROFILE\.cargo\bin;$env:Path"
cargo check
```
