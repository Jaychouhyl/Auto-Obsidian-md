use serde::{Deserialize, Serialize};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use crate::project::{backend_exe, config_toml, project_root, run_ps1};

#[derive(Debug, Serialize, Deserialize)]
pub struct CommandResult {
    pub ok: bool,
    pub code: i32,
    pub stdout: String,
    pub stderr: String,
}

const COMMAND_TIMEOUT: Duration = Duration::from_secs(180);

pub fn run_ingest(args: &[String]) -> Result<CommandResult, String> {
    let workspace = project_root();
    let mut command = if let Some(backend) = backend_exe() {
        Command::new(backend)
    } else if run_ps1().is_file() {
        let mut command = Command::new("powershell.exe");
        command
            .arg("-NoProfile")
            .arg("-NonInteractive")
            .arg("-ExecutionPolicy")
            .arg("Bypass")
            .arg("-File")
            .arg(run_ps1());
        command
    } else {
        return Ok(CommandResult {
            ok: false,
            code: -1,
            stdout: String::new(),
            stderr: "obsidian ingest backend is missing; reinstall the app or rebuild the sidecar"
                .into(),
        });
    };

    for arg in args {
        command.arg(arg);
    }
    command
        .current_dir(&workspace)
        .env("OBSIDIAN_INGEST_HOME", &workspace)
        .env("PYTHONIOENCODING", "utf-8");

    let mut child = command
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("failed to run ingest command: {error}"))?;

    let started_at = Instant::now();
    loop {
        match child
            .try_wait()
            .map_err(|error| format!("failed to poll ingest command: {error}"))?
        {
            Some(_) => break,
            None if started_at.elapsed() >= COMMAND_TIMEOUT => {
                let _ = child.kill();
                let _ = child.wait();
                return Ok(CommandResult {
                    ok: false,
                    code: -1,
                    stdout: String::new(),
                    stderr: format!(
                        "ingest command timed out after {} seconds",
                        COMMAND_TIMEOUT.as_secs()
                    ),
                });
            }
            None => thread::sleep(Duration::from_millis(100)),
        }
    }

    let output = child
        .wait_with_output()
        .map_err(|error| format!("failed to collect ingest command output: {error}"))?;
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
