use serde::Serialize;
use std::fs;

use crate::project::logs_dir;

#[derive(Debug, Serialize)]
pub struct LogFile {
    pub name: String,
    pub path: String,
    pub modified_unix: u64,
}

pub fn recent_logs(limit: usize) -> Vec<LogFile> {
    let mut files: Vec<LogFile> = fs::read_dir(logs_dir())
        .ok()
        .into_iter()
        .flat_map(|entries| entries.filter_map(Result::ok))
        .filter_map(|entry| {
            let metadata = entry.metadata().ok()?;
            if !metadata.is_file() {
                return None;
            }
            let modified = metadata.modified().ok()?;
            let unix = modified
                .duration_since(std::time::UNIX_EPOCH)
                .ok()?
                .as_secs();
            Some(LogFile {
                name: entry.file_name().to_string_lossy().to_string(),
                path: entry.path().to_string_lossy().to_string(),
                modified_unix: unix,
            })
        })
        .collect();
    files.sort_by(|a, b| b.modified_unix.cmp(&a.modified_unix));
    files.truncate(limit);
    files
}
