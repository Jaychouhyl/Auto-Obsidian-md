# 安装与首次配置

## Windows 安装

1. 从 GitHub Releases 下载 Windows 安装包。
2. 安装后启动 `Obsidian Ingest Studio`。
3. 在“配置”页填写 Obsidian vault 路径。
4. 填写 DeepSeek / OpenAI-compatible 服务地址、模型和 API Key。
5. 点击“保存”，再点击“健康检查”。

## 本机依赖

推荐安装：

```text
Python 3.11+
Node.js 22+
Rust stable
Docker Desktop
ffmpeg
yt-dlp
```

如果只使用安装包运行桌面端，普通用户不需要直接操作 Rust 和 Node.js。

## 配置文件

默认本机配置：

```text
<项目目录>\config.toml
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
