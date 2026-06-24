use std::env;
use std::fs;
use std::path::{Path, PathBuf};

pub fn project_root() -> PathBuf {
    let root = workspace_dir();
    let _ = ensure_workspace(&root);
    root
}

pub fn backend_exe() -> Option<PathBuf> {
    if cfg!(debug_assertions) {
        return None;
    }
    let names = [
        "obsidian-ingest-backend.exe",
        "obsidian-ingest-backend-x86_64-pc-windows-msvc.exe",
    ];

    if let Ok(current_exe) = env::current_exe() {
        if let Some(app_dir) = current_exe.parent() {
            if let Some(path) = first_existing(app_dir, &names) {
                return Some(path);
            }
        }
    }

    let source_binaries = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("binaries");
    first_existing(&source_binaries, &names)
}

pub fn run_ps1() -> PathBuf {
    repo_root().join("run.ps1")
}

pub fn config_toml() -> PathBuf {
    project_root().join("config.toml")
}

pub fn logs_dir() -> PathBuf {
    project_root().join("logs")
}

pub fn links_txt() -> PathBuf {
    project_root().join("links.txt")
}

pub fn feeds_txt() -> PathBuf {
    project_root().join("feeds.txt")
}

fn workspace_dir() -> PathBuf {
    if let Some(value) = env::var_os("OBSIDIAN_INGEST_HOME") {
        return PathBuf::from(value);
    }
    if let Some(value) = env::var_os("LOCALAPPDATA") {
        return PathBuf::from(value).join("Obsidian Ingest Studio");
    }
    repo_root().join(".local-workspace")
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .map(Path::to_path_buf)
        .unwrap_or_else(|| env::current_dir().unwrap_or_else(|_| PathBuf::from(".")))
}

fn first_existing(dir: &Path, names: &[&str]) -> Option<PathBuf> {
    names
        .iter()
        .map(|name| dir.join(name))
        .find(|path| path.is_file())
}

fn ensure_workspace(root: &Path) -> std::io::Result<()> {
    fs::create_dir_all(root)?;
    fs::create_dir_all(root.join("data"))?;
    fs::create_dir_all(root.join("cache"))?;
    fs::create_dir_all(root.join("logs"))?;
    fs::create_dir_all(root.join("inbox"))?;
    fs::create_dir_all(root.join("vault"))?;
    write_if_missing(&root.join("links.txt"), "")?;
    write_if_missing(&root.join("feeds.txt"), "")?;
    write_if_missing(&root.join("config.toml"), &default_config(root))?;
    Ok(())
}

fn write_if_missing(path: &Path, text: &str) -> std::io::Result<()> {
    if !path.exists() {
        fs::write(path, text)?;
    }
    Ok(())
}

fn default_config(root: &Path) -> String {
    let queue_db = root
        .join("data")
        .join("queue.sqlite")
        .to_string_lossy()
        .replace('\\', "\\\\");
    let cache_dir = root.join("cache").to_string_lossy().replace('\\', "\\\\");
    let vault_path = root.join("vault").to_string_lossy().replace('\\', "\\\\");
    format!(
        "[paths]\nqueue_db = \"{}\"\ncache_dir = \"{}\"\n\n[obsidian]\nmode = \"local\"\nvault_path = \"{}\"\nfolder = \"Inbox/Learning Inbox\"\nrest_base_url = \"http://127.0.0.1:27123\"\nrest_api_key = \"\"\n\n[tools]\nyt_dlp = \"yt-dlp\"\nffmpeg = \"ffmpeg\"\ndouyin_downloader = \"douyin-dl\"\ndouyin_config = \"\"\nwhisper = \"whisper\"\nfunasr = \"funasr\"\n\n[llm]\nenabled = false\nprovider = \"openai-compatible\"\nbase_url = \"https://api.deepseek.com/v1\"\napi_key = \"\"\nmodel = \"deepseek-chat\"\nlanguage = \"zh-CN\"\n\n[routing]\nenabled = true\nfallback_folder = \"Inbox/Learning Inbox\"\nallowed_folders = [\n    \"AI学习\",\n    \"考研资料汇总\",\n    \"炒股与量化学习\",\n    \"研后/英语学习\",\n    \"工作\",\n    \"Life\",\n    \"Inbox/Learning Inbox\",\n]\n",
        queue_db, cache_dir, vault_path
    )
}
