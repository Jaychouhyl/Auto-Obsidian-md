use serde::{Deserialize, Serialize};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use crate::project::{config_toml, run_ps1};

#[derive(Debug, Serialize, Deserialize)]
pub struct CommandResult {
    pub ok: bool,
    pub code: i32,
    pub stdout: String,
    pub stderr: String,
}

const COMMAND_TIMEOUT: Duration = Duration::from_secs(180);

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
