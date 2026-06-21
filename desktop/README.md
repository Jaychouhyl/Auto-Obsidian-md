# Obsidian Ingest Studio

桌面控制台基于 Tauri + TypeScript，调用项目根目录的 `run.ps1` 和同一套 Python 入库流程。

## 本地运行

```powershell
cd D:\obsidian-ingest-pipeline\desktop
$env:PATH = "D:\Nodejs;$env:USERPROFILE\.cargo\bin;$env:PATH"
& 'D:\Nodejs\npm.cmd' run tauri dev
```

## 构建前端

```powershell
cd D:\obsidian-ingest-pipeline\desktop
$env:PATH = "D:\Nodejs;$env:PATH"
& 'D:\Nodejs\npm.cmd' run build
```

## 打包安装程序

```powershell
cd D:\obsidian-ingest-pipeline\desktop
$env:PATH = "D:\Nodejs;$env:USERPROFILE\.cargo\bin;$env:PATH"
& 'D:\Nodejs\npm.cmd' run tauri build -- --no-sign
```

安装包输出目录：

```text
desktop/src-tauri/target/release/bundle/nsis/
```
