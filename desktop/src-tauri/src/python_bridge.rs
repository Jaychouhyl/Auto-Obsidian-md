use serde::{Deserialize, Serialize};
use std::process::Command;

use crate::project::{config_toml, run_ps1};

#[derive(Debug, Serialize, Deserialize)]
pub struct CommandResult {
    pub ok: bool,
    pub code: i32,
    pub stdout: String,
    pub stderr: String,
}

pub fn run_ingest(args: &[String]) -> Result<CommandResult, String> {
    let mut command = Command::new("powershell.exe");
    command
        .arg("-NoProfile")
        .arg("-NonInteractive")
        .arg("-ExecutionPolicy")
        .arg("Bypass")
        .arg("-File")
        .arg(run_ps1());

    for arg in args {
        command.arg(arg);
    }

    let output = command
        .output()
        .map_err(|error| format!("failed to run ingest command: {error}"))?;
    let code = output.status.code().unwrap_or(-1);
    Ok(CommandResult {
        ok: output.status.success(),
        code,
        stdout: String::from_utf8_lossy(&output.stdout).to_string(),
        stderr: String::from_utf8_lossy(&output.stderr).to_string(),
    })
}

pub fn config_arg() -> String {
    config_toml().to_string_lossy().to_string()
}
