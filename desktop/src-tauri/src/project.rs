use std::path::PathBuf;

pub fn project_root() -> PathBuf {
    PathBuf::from(r"D:\obsidian-ingest-pipeline")
}

pub fn run_ps1() -> PathBuf {
    project_root().join("run.ps1")
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
