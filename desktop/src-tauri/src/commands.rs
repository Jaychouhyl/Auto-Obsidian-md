use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

use crate::logs::{recent_logs, LogFile};
use crate::project::{feeds_txt, links_txt};
use crate::python_bridge::{
    config_arg, run_ingest, run_ingest_with_timeout, CommandResult, ACCOUNT_LOGIN_TIMEOUT,
};

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

fn json_result(result: CommandResult) -> Result<Value, String> {
    if !result.ok {
        return Err(command_error(&result));
    }
    serde_json::from_str(&result.stdout).map_err(|error| error.to_string())
}

fn run_account_json(args: &[String], long_running: bool) -> Result<Value, String> {
    let result = if long_running {
        run_ingest_with_timeout(args, ACCOUNT_LOGIN_TIMEOUT)?
    } else {
        run_ingest(args)?
    };
    json_result(result)
}

fn open_os_path(path: PathBuf) -> Result<(), String> {
    let target = if path.exists() {
        path
    } else {
        path.parent()
            .map(PathBuf::from)
            .ok_or_else(|| "Path does not exist and has no parent directory".to_string())?
    };
    if !target.exists() {
        return Err(format!("Path does not exist: {}", target.display()));
    }

    #[cfg(windows)]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        Command::new("explorer.exe")
            .arg(target)
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()
            .map_err(|error| error.to_string())?;
        return Ok(());
    }

    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(target)
            .spawn()
            .map_err(|error| error.to_string())?;
        return Ok(());
    }

    #[cfg(all(unix, not(target_os = "macos")))]
    {
        Command::new("xdg-open")
            .arg(target)
            .spawn()
            .map_err(|error| error.to_string())?;
        return Ok(());
    }
}

#[derive(Debug, Deserialize)]
pub struct ToolConfigDraft {
    yt_dlp: String,
    ffmpeg: String,
    douyin_downloader: String,
    douyin_config: String,
    whisper: String,
    funasr: String,
    ocr: String,
}

#[derive(Debug, Deserialize)]
pub struct OutputsConfigDraft {
    formats: Vec<String>,
    html_dir: String,
    csv_path: String,
    notion_token: String,
    notion_database_id: String,
    notion_title_property: String,
    notion_api_base: String,
}

#[derive(Debug, Deserialize)]
pub struct PromptConfigDraft {
    active_template: String,
    custom_instruction: String,
}

#[derive(Debug, Deserialize)]
pub struct NoteTemplateConfigDraft {
    active_template: String,
    include_transcript: bool,
    include_source_notes: bool,
    attribution_name: String,
    custom_structure: String,
}

#[derive(Debug, Deserialize)]
pub struct AppConfigDraft {
    queue_db: String,
    cache_dir: String,
    obsidian_mode: String,
    obsidian_vault: String,
    obsidian_folder: String,
    rest_base_url: String,
    rest_api_key: String,
    llm_enabled: bool,
    llm_provider: String,
    llm_base_url: String,
    llm_api_key: String,
    llm_model: String,
    llm_language: String,
    routing_enabled: bool,
    fallback_folder: String,
    allowed_folders: Vec<String>,
    tools: ToolConfigDraft,
    outputs: OutputsConfigDraft,
    prompt: PromptConfigDraft,
    note_template: NoteTemplateConfigDraft,
}

#[derive(Debug, Serialize)]
pub struct SourceFiles {
    links: String,
    feeds: String,
}

fn toml_string(value: &str) -> String {
    let escaped = value
        .replace('\\', "\\\\")
        .replace('\n', "\\n")
        .replace('\r', "\\r")
        .replace('\t', "\\t")
        .replace('"', "\\\"");
    format!("\"{}\"", escaped)
}

fn toml_bool(value: bool) -> &'static str {
    if value {
        "true"
    } else {
        "false"
    }
}

fn existing_toml_value(text: &str, key: &str) -> Option<String> {
    for line in text.lines() {
        let trimmed = line.trim();
        if !trimmed.starts_with(key) {
            continue;
        }
        let (_, raw_value) = trimmed.split_once('=')?;
        let value = raw_value
            .trim()
            .trim_matches('"')
            .replace("\\\"", "\"")
            .replace("\\\\", "\\");
        return Some(value);
    }
    None
}

fn render_config(draft: &AppConfigDraft) -> String {
    let folders = draft
        .allowed_folders
        .iter()
        .map(|folder| {
            folder
                .trim()
                .replace('\\', "/")
                .trim_matches('/')
                .to_string()
        })
        .filter(|folder| !folder.is_empty())
        .fold(Vec::<String>::new(), |mut acc, folder| {
            if !acc.contains(&folder) {
                acc.push(folder);
            }
            acc
        });
    let folder_lines = folders
        .iter()
        .map(|folder| format!("    {},", toml_string(folder)))
        .collect::<Vec<_>>()
        .join("\n");
    let output_formats = draft
        .outputs
        .formats
        .iter()
        .map(|format| format.trim().to_lowercase())
        .filter(|format| matches!(format.as_str(), "markdown" | "html" | "csv" | "notion"))
        .fold(Vec::<String>::new(), |mut acc, format| {
            if !acc.contains(&format) {
                acc.push(format);
            }
            acc
        });
    let output_formats = if output_formats.is_empty() {
        vec!["markdown".to_string()]
    } else {
        output_formats
    };
    let output_format_lines = output_formats
        .iter()
        .map(|format| toml_string(format))
        .collect::<Vec<_>>()
        .join(", ");

    format!(
        "[paths]\nqueue_db = {}\ncache_dir = {}\n\n[obsidian]\nmode = {}\nvault_path = {}\nfolder = {}\nrest_base_url = {}\nrest_api_key = {}\n\n[tools]\nyt_dlp = {}\nffmpeg = {}\ndouyin_downloader = {}\ndouyin_config = {}\nwhisper = {}\nfunasr = {}\nocr = {}\n\n[llm]\nenabled = {}\nprovider = {}\nbase_url = {}\napi_key = {}\nmodel = {}\nlanguage = {}\n\n[outputs]\nformats = [{}]\nhtml_dir = {}\ncsv_path = {}\nnotion_token = {}\nnotion_database_id = {}\nnotion_title_property = {}\nnotion_api_base = {}\n\n[prompt]\nactive_template = {}\ncustom_instruction = {}\n\n[note_template]\nactive_template = {}\ninclude_transcript = {}\ninclude_source_notes = {}\nattribution_name = {}\ncustom_structure = {}\n\n[routing]\nenabled = {}\nfallback_folder = {}\nallowed_folders = [\n{}\n]\n",
        toml_string(&draft.queue_db),
        toml_string(&draft.cache_dir),
        toml_string(&draft.obsidian_mode),
        toml_string(&draft.obsidian_vault),
        toml_string(&draft.obsidian_folder),
        toml_string(&draft.rest_base_url),
        toml_string(&draft.rest_api_key),
        toml_string(&draft.tools.yt_dlp),
        toml_string(&draft.tools.ffmpeg),
        toml_string(&draft.tools.douyin_downloader),
        toml_string(&draft.tools.douyin_config),
        toml_string(&draft.tools.whisper),
        toml_string(&draft.tools.funasr),
        toml_string(&draft.tools.ocr),
        toml_bool(draft.llm_enabled),
        toml_string(&draft.llm_provider),
        toml_string(&draft.llm_base_url),
        toml_string(&draft.llm_api_key),
        toml_string(&draft.llm_model),
        toml_string(&draft.llm_language),
        output_format_lines,
        toml_string(&draft.outputs.html_dir),
        toml_string(&draft.outputs.csv_path),
        toml_string(&draft.outputs.notion_token),
        toml_string(&draft.outputs.notion_database_id),
        toml_string(&draft.outputs.notion_title_property),
        toml_string(&draft.outputs.notion_api_base),
        toml_string(&draft.prompt.active_template),
        toml_string(&draft.prompt.custom_instruction),
        toml_string(&draft.note_template.active_template),
        toml_bool(draft.note_template.include_transcript),
        toml_bool(draft.note_template.include_source_notes),
        toml_string(&draft.note_template.attribution_name),
        toml_string(&draft.note_template.custom_structure),
        toml_bool(draft.routing_enabled),
        toml_string(&draft.fallback_folder),
        folder_lines,
    )
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
pub fn run_doctor_json() -> Result<Value, String> {
    let result = run_ingest(&[
        "doctor".into(),
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
pub fn get_dependencies() -> Result<Value, String> {
    let result = run_ingest(&[
        "dependencies".into(),
        "report".into(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])?;
    json_result(result)
}

#[tauri::command]
pub fn install_dependencies(tools: Vec<String>) -> Result<Value, String> {
    let mut args = vec![
        "dependencies".into(),
        "install".into(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ];
    for tool in tools {
        args.push("--tool".into());
        args.push(tool);
    }
    let result = run_ingest_with_timeout(&args, ACCOUNT_LOGIN_TIMEOUT)?;
    json_result(result)
}

#[tauri::command]
pub fn get_app_config() -> Result<Value, String> {
    get_status()
}

#[tauri::command]
pub fn save_app_config(draft: AppConfigDraft) -> Result<CommandResult, String> {
    let config_path = crate::project::config_toml();
    let existing = fs::read_to_string(&config_path).unwrap_or_default();
    let mut draft = draft;
    if draft.llm_api_key.trim().is_empty() {
        draft.llm_api_key = existing_toml_value(&existing, "api_key").unwrap_or_default();
    }
    if draft.rest_api_key.trim().is_empty() {
        draft.rest_api_key = existing_toml_value(&existing, "rest_api_key").unwrap_or_default();
    }
    if draft.outputs.notion_token.trim().is_empty() {
        draft.outputs.notion_token = existing_toml_value(&existing, "notion_token").unwrap_or_default();
    }
    if draft.outputs.notion_database_id.trim().is_empty()
        || draft.outputs.notion_database_id.trim() == "configured"
    {
        draft.outputs.notion_database_id =
            existing_toml_value(&existing, "notion_database_id").unwrap_or_default();
    }
    fs::write(&config_path, render_config(&draft)).map_err(|error| error.to_string())?;
    Ok(CommandResult {
        ok: true,
        code: 0,
        stdout: format!("Saved config: {}", config_path.display()),
        stderr: String::new(),
    })
}

#[tauri::command]
pub fn open_path(path: String) -> Result<CommandResult, String> {
    open_os_path(PathBuf::from(path.clone()))?;
    Ok(CommandResult {
        ok: true,
        code: 0,
        stdout: format!("Opened: {}", path),
        stderr: String::new(),
    })
}

#[tauri::command]
pub fn choose_directory(current: String) -> Result<Option<String>, String> {
    #[cfg(windows)]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        let selected = current.replace('\'', "''");
        let script = format!(
            r#"
Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = '选择输出目录'
$dialog.ShowNewFolderButton = $true
$selected = '{selected}'
if ($selected -and (Test-Path -LiteralPath $selected)) {{
    $dialog.SelectedPath = $selected
}}
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
    Write-Output $dialog.SelectedPath
}}
"#
        );
        let output = Command::new("powershell.exe")
            .args([
                "-NoProfile",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                &script,
            ])
            .creation_flags(CREATE_NO_WINDOW)
            .output()
            .map_err(|error| error.to_string())?;
        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            return Err(if stderr.is_empty() {
                "Directory picker failed".to_string()
            } else {
                stderr
            });
        }
        let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
        return Ok(if path.is_empty() { None } else { Some(path) });
    }

    #[cfg(not(windows))]
    {
        let _ = current;
        Ok(None)
    }
}

#[tauri::command]
pub fn open_url(url: String) -> Result<CommandResult, String> {
    if !(url.starts_with("https://") || url.starts_with("http://")) {
        return Err("Only http/https URLs are supported.".to_string());
    }

    #[cfg(windows)]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        Command::new("rundll32.exe")
            .arg("url.dll,FileProtocolHandler")
            .arg(&url)
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()
            .map_err(|error| error.to_string())?;
    }

    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&url)
            .spawn()
            .map_err(|error| error.to_string())?;
    }

    #[cfg(all(unix, not(target_os = "macos")))]
    {
        Command::new("xdg-open")
            .arg(&url)
            .spawn()
            .map_err(|error| error.to_string())?;
    }

    Ok(CommandResult {
        ok: true,
        code: 0,
        stdout: format!("Opened: {}", url),
        stderr: String::new(),
    })
}

#[tauri::command]
pub fn open_output(kind: String) -> Result<CommandResult, String> {
    let status = get_status()?;
    let path = match kind.as_str() {
        "project" => status
            .pointer("/paths/project_root")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        "vault" => status
            .pointer("/paths/obsidian_vault")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        "html" => status
            .pointer("/outputs/html_dir")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        "csv" => status
            .pointer("/outputs/csv_path")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        "cache" => status
            .pointer("/paths/cache_dir")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        "queue" => status
            .pointer("/paths/queue_db")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        _ => return Err(format!("Unsupported output kind: {}", kind)),
    };
    if path.trim().is_empty() {
        return Err(format!("No path configured for output kind: {}", kind));
    }
    let path_buf = PathBuf::from(path);
    if kind == "html" && !path_buf.exists() {
        fs::create_dir_all(&path_buf).map_err(|error| error.to_string())?;
    }
    if kind == "csv" && !path_buf.exists() {
        if let Some(parent) = path_buf.parent() {
            fs::create_dir_all(parent).map_err(|error| error.to_string())?;
        }
    }
    open_os_path(path_buf)?;
    Ok(CommandResult {
        ok: true,
        code: 0,
        stdout: format!("Opened {}", kind),
        stderr: String::new(),
    })
}

#[tauri::command]
pub fn backup_project() -> Result<CommandResult, String> {
    run_ingest(&[
        "backup".into(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn restore_project(backup_file: String) -> Result<CommandResult, String> {
    run_ingest(&[
        "restore".into(),
        backup_file,
        "--yes".into(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])
}

#[tauri::command]
pub fn get_source_files() -> Result<SourceFiles, String> {
    Ok(SourceFiles {
        links: fs::read_to_string(links_txt()).unwrap_or_default(),
        feeds: fs::read_to_string(feeds_txt()).unwrap_or_default(),
    })
}

#[tauri::command]
pub fn save_source_files(links: String, feeds: String) -> Result<CommandResult, String> {
    fs::write(links_txt(), links).map_err(|error| error.to_string())?;
    fs::write(feeds_txt(), feeds).map_err(|error| error.to_string())?;
    Ok(CommandResult {
        ok: true,
        code: 0,
        stdout: "Saved source files".into(),
        stderr: String::new(),
    })
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
    run_ingest(&[
        "scan-inbox".into(),
        "--json".into(),
        "--config".into(),
        config_arg(),
    ])
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
pub fn collect_platform_list(
    url: String,
    platform: String,
    limit: u32,
) -> Result<CommandResult, String> {
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

#[tauri::command]
pub fn get_accounts() -> Result<Value, String> {
    run_account_json(
        &[
            "accounts".into(),
            "list".into(),
            "--json".into(),
            "--config".into(),
            config_arg(),
        ],
        false,
    )
}

#[tauri::command]
pub fn start_account_login(platform: String) -> Result<Value, String> {
    run_account_json(
        &[
            "accounts".into(),
            "login".into(),
            "--platform".into(),
            platform,
            "--timeout".into(),
            "600".into(),
            "--json".into(),
            "--config".into(),
            config_arg(),
        ],
        true,
    )
}

#[tauri::command]
pub fn confirm_account_login(candidate_id: String, make_current: bool) -> Result<Value, String> {
    let mut args = vec![
        "accounts".into(),
        "confirm".into(),
        "--candidate-id".into(),
        candidate_id,
    ];
    if !make_current {
        args.push("--no-switch".into());
    }
    args.extend(["--json".into(), "--config".into(), config_arg()]);
    run_account_json(&args, false)
}

#[tauri::command]
pub fn cancel_account_login(candidate_id: String) -> Result<Value, String> {
    run_account_json(
        &[
            "accounts".into(),
            "cancel".into(),
            "--candidate-id".into(),
            candidate_id,
            "--json".into(),
            "--config".into(),
            config_arg(),
        ],
        false,
    )
}

#[tauri::command]
pub fn switch_account(platform: String, account_id: String) -> Result<Value, String> {
    run_account_json(
        &[
            "accounts".into(),
            "switch".into(),
            "--platform".into(),
            platform,
            "--account-id".into(),
            account_id,
            "--json".into(),
            "--config".into(),
            config_arg(),
        ],
        false,
    )
}

#[tauri::command]
pub fn verify_account(account_id: String) -> Result<Value, String> {
    run_account_json(
        &[
            "accounts".into(),
            "verify".into(),
            "--account-id".into(),
            account_id,
            "--json".into(),
            "--config".into(),
            config_arg(),
        ],
        false,
    )
}

#[tauri::command]
pub fn relogin_account(account_id: String) -> Result<Value, String> {
    run_account_json(
        &[
            "accounts".into(),
            "relogin".into(),
            "--account-id".into(),
            account_id,
            "--timeout".into(),
            "600".into(),
            "--json".into(),
            "--config".into(),
            config_arg(),
        ],
        true,
    )
}

#[tauri::command]
pub fn delete_account(account_id: String) -> Result<Value, String> {
    run_account_json(
        &[
            "accounts".into(),
            "delete".into(),
            "--account-id".into(),
            account_id,
            "--json".into(),
            "--config".into(),
            config_arg(),
        ],
        false,
    )
}
