# 安装与首次配置

## Windows 安装

1. 从 GitHub Releases 下载 Windows 安装包。
2. 安装后启动 `Obsidian Ingest Studio`。
3. 在“配置”页填写 Obsidian vault 路径。
4. 填写 DeepSeek / OpenAI-compatible 服务地址、模型和 API Key。
5. 点击“保存”，再点击“健康检查”。

## 普通用户依赖

只使用 Windows 安装包时，不需要安装 Python、Node.js 或 Rust。

可选依赖：

```text
ffmpeg
yt-dlp
whisper
```

这些用于视频下载、音频转写等高级能力。只做网页、RSS、本地文本/PDF 入库时，可以先不装。

## 配置文件

默认本机配置：

```text
%LOCALAPPDATA%\Obsidian Ingest Studio\config.toml
```

不会提交到 Git：

```text
config.toml
douyin-config.yml
links.txt
feeds.txt
data/
cache/
logs/
```

## 常用入口

桌面端：

```text
Obsidian Ingest Studio
```

命令行：

```powershell
cd <项目目录>
.\run.ps1 doctor --config .\config.toml
.\run.ps1 queue --json --config .\config.toml
```
