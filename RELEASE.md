# 发布清单

## 发布前

- `python -m unittest discover -s tests -v`
- `npm run build` in `desktop`
- `cargo check` in `desktop/src-tauri`
- `docker compose config --quiet`
- `docker compose run --rm ingest doctor --json --config /app/config.docker.toml`
- 确认 `config.toml`、`douyin-config.yml`、`links.txt`、`feeds.txt` 未被提交。

## 打包

```powershell
cd <项目目录>\desktop
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
npm run tauri build -- --no-sign
```

如果 Node.js、npm 或 Rust 不在 PATH，先把对应安装目录加入当前终端 PATH。

安装包目录：

```text
desktop/src-tauri/target/release/bundle/nsis/
```

## GitHub Release

```powershell
git tag -a v0.1.1 -m "发布 v0.1.1"
git push origin main
git push origin v0.1.1
```

推送 `v*` tag 后，GitHub Actions 会构建 Windows 安装包并发布到 Releases。

## 发布后

- 下载 Release 里的安装包。
- 在干净目录安装并启动桌面端。
- 完成配置保存和健康检查。
- 导入 1 条网页链接并确认 Obsidian vault 生成 Markdown。
