use serde_json::Value;

use crate::logs::{recent_logs, LogFile};
use crate::project::{feeds_txt, links_txt};
use crate::python_bridge::{config_arg, run_ingest, CommandResult};

fn command_error(result: &CommandResult) -> String {
    let stderr = result.stderr.trim();
    if !stderr.is_empty() {
        return stderr.to_string();
    }
    let stdout = result.stdout.trim();
    if !stdout.is_empty() {
        return stdout.to_string();
    }
    format!("command failed with code {}", result.code)
}

#[tauri::command]
pub fn get_status() -> Result<Value, String> {
    let result = run_ingest(&[
        "status".into(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])?;
    if !result.ok {
        return Err(command_error(&result));
    }
    serde_json::from_str(&result.stdout).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn get_queue(limit: u32, status: Option<String>) -> Result<Value, String> {
    let mut args = vec![
        "queue".into(),
        "--json".into(),
        "--limit".into(),
        limit.to_string(),
    ];
    if let Some(status) = status {
        args.push("--status".into());
        args.push(status);
    }
    args.push("--config".into());
    args.push(config_arg());

    let result = run_ingest(&args)?;
    if !result.ok {
        return Err(command_error(&result));
    }
    serde_json::from_str(&result.stdout).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn run_doctor() -> Result<CommandResult, String> {
    run_ingest(&["doctor".into(), "--config".into(), config_arg()])
}

#[tauri::command]
pub fn collect_douyin(count: u32) -> Result<CommandResult, String> {
    run_ingest(&[
        "collect-douyin".into(),
        "--json".into(),
        "--count".into(),
        count.to_string(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn scan_inbox() -> Result<CommandResult, String> {
    run_ingest(&["scan-inbox".into(), "--json".into(), "--config".into(), config_arg()])
}

#[tauri::command]
pub fn scan_directory(directory: String) -> Result<CommandResult, String> {
    run_ingest(&[
        "scan-directory".into(),
        "--json".into(),
        "--dir".into(),
        directory,
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn collect_rss(limit: u32) -> Result<CommandResult, String> {
    run_ingest(&[
        "collect-rss".into(),
        "--json".into(),
        "--feeds".into(),
        feeds_txt().to_string_lossy().to_string(),
        "--limit".into(),
        limit.to_string(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn clip_webpage(url: String) -> Result<CommandResult, String> {
    run_ingest(&[
        "clip-webpage".into(),
        url,
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn collect_platform_list(url: String, platform: String, limit: u32) -> Result<CommandResult, String> {
    run_ingest(&[
        "collect-list".into(),
        url,
        "--platform".into(),
        platform,
        "--limit".into(),
        limit.to_string(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn import_links() -> Result<CommandResult, String> {
    run_ingest(&[
        "import-links".into(),
        links_txt().to_string_lossy().to_string(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn process_queue(limit: u32) -> Result<CommandResult, String> {
    run_ingest(&[
        "run".into(),
        "--once".into(),
        "--limit".into(),
        limit.to_string(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn retry_item(id: u32) -> Result<CommandResult, String> {
    run_ingest(&[
        "retry".into(),
        id.to_string(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn retry_failed(limit: u32) -> Result<CommandResult, String> {
    run_ingest(&[
        "retry-failed".into(),
        "--limit".into(),
        limit.to_string(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn skip_item(id: u32, reason: String) -> Result<CommandResult, String> {
    run_ingest(&[
        "skip".into(),
        id.to_string(),
        "--reason".into(),
        reason,
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn knowledge_maintenance() -> Result<CommandResult, String> {
    run_ingest(&[
        "knowledge-maintenance".into(),
        "--write".into(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn write_launcher() -> Result<CommandResult, String> {
    run_ingest(&[
        "write-launcher".into(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn list_recent_logs(limit: u32) -> Result<Vec<LogFile>, String> {
    Ok(recent_logs(limit as usize))
}
