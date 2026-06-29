# 发布清单

## 发布前

- `python -m unittest discover -s tests -v`
- `python -m pip install . pyinstaller`
- `.\packaging\build-sidecar.ps1`
- `npm run build` in `desktop`
- `cargo check` in `desktop/src-tauri`
- 商业版不提供应用内更新入口；交付什么安装包就是什么版本。
- `docker compose config --quiet`
- `docker compose run --rm ingest doctor --json --config /app/config.docker.toml`
- 确认 `config.toml`、`douyin-config.yml`、`links.txt`、`feeds.txt` 未被提交。

## 打包

```powershell
cd <项目目录>
.\packaging\build-desktop-edition.ps1 -Edition community
.\packaging\build-desktop-edition.ps1 -Edition commercial
```

如果 Node.js、npm、Rust 或 PyInstaller 不在 PATH，先把对应安装目录加入当前终端 PATH，或者通过 `python -m pip install pyinstaller` 安装打包器。

安装包目录：

```text
build/open-source-full-v<version>/
build/commercial-v<version>/
```

开源完整版使用 `Ingest Studio` 的产品名、窗口标题和安装包名；商业版使用 `Knowledge Studio` 的产品名、窗口标题和安装包名。

## 签名

可信商用分发需要真实代码签名证书。配置其一后执行：

```powershell
$env:WINDOWS_SIGN_CERT_PATH = "D:\certs\publisher.pfx"
$env:WINDOWS_SIGN_CERT_PASSWORD = "<证书密码>"
.\packaging\sign-windows.ps1 -Path "build\commercial-v0.4.4\Knowledge Studio 商业版_0.4.4_x64-setup.exe"
```

或：

```powershell
$env:WINDOWS_SIGN_CERT_THUMBPRINT = "<证书指纹>"
.\packaging\sign-windows.ps1 -Path "build\commercial-v0.4.4\Knowledge Studio 商业版_0.4.4_x64-setup.exe"
```

没有真实证书时不要伪造已签名状态。

## 验收

```powershell
.\packaging\verify-release.ps1
```

脚本会检查两版产物、sidecar、配置解析、OCR 配置和签名状态。真实安装后还需要手工确认：

需要把未签名视为发布失败时使用：

```powershell
.\packaging\verify-release.ps1 -RequireSignature
```

- 安装商业版后开始菜单 / 桌面快捷方式显示 `Knowledge Studio`。
- 安装开源完整版后显示 `Ingest Studio`。
- 商业版界面没有 GitHub、更新、私有更新或下载入口。
- 开源完整版保留 GitHub Release 更新页。
- 登录至少一个账号，导入一条网页或本地文件，确认输出目录生成 Markdown。

## GitHub Release

```powershell
git tag -a v0.04 -m "发布 v0.04"
git push origin main
git push origin v0.04
```

推送 `v*` tag 后，GitHub Actions 会构建 Windows 安装包并发布到 Releases。

## 发布后

- 下载 Release 里的安装包。
- 在干净目录安装并启动桌面端。
- 完成配置保存和健康检查。
- 导入 1 条网页链接并确认 Obsidian vault 生成 Markdown。
- 在“账号”页确认抖音旧账号迁移、校验和当前账号显示正常。

---

自动化写的
署名：小黄狗
