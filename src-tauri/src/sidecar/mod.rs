use serde_json::Value;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::thread;
use tauri::{AppHandle, Emitter};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

pub struct SidecarManager {
    child: Option<Child>,
    stdin_tx: Option<mpsc::Sender<String>>,
    app_handle: Option<AppHandle>,
}

impl SidecarManager {
    pub fn new() -> Self {
        SidecarManager {
            child: None,
            stdin_tx: None,
            app_handle: None,
        }
    }

    pub fn set_app_handle(&mut self, handle: AppHandle) {
        self.app_handle = Some(handle);
    }

    pub fn is_running(&self) -> bool {
        self.child.is_some()
    }

    pub fn ensure_running(&self) -> Result<(), String> {
        if self.child.is_some() {
            return Ok(());
        }
        Err("Sidecar not running. Call start() first.".to_string())
    }

    pub fn start(&mut self) -> Result<(), String> {
        if self.child.is_some() {
            return Ok(());
        }

        // Find the Python sidecar script
        let sidecar_path = self.find_sidecar_path()?;

        // Find Python executable
        let python = self.find_python()?;

        let mut cmd = Command::new(&python);
        cmd.arg(&sidecar_path)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        #[cfg(windows)]
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW on Windows

        let mut child = cmd
            .spawn()
            .map_err(|e| format!("Failed to start Python sidecar: {}", e))?;

        // Set up stdin writer channel
        let stdin = child.stdin.take().ok_or("Failed to get stdin")?;
        let (tx, rx) = mpsc::channel::<String>();

        // Stdin writer thread
        thread::spawn(move || {
            let mut stdin = stdin;
            while let Ok(line) = rx.recv() {
                if writeln!(stdin, "{}", line).is_err() {
                    break;
                }
                if stdin.flush().is_err() {
                    break;
                }
            }
        });

        // Stdout reader thread - forwards messages to Tauri events
        let stdout = child.stdout.take().ok_or("Failed to get stdout")?;
        let app_handle = self.app_handle.clone();

        thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines() {
                match line {
                    Ok(line) => {
                        if line.trim().is_empty() {
                            continue;
                        }
                        // Try to parse as JSON
                        match serde_json::from_str::<Value>(&line) {
                            Ok(msg) => {
                                if let Some(ref handle) = app_handle {
                                    let msg_type = msg
                                        .get("type")
                                        .and_then(|t| t.as_str())
                                        .unwrap_or("unknown");

                                    // Emit as Tauri event based on message type
                                    let event_name = match msg_type {
                                        "progress" => "scrape-progress",
                                        "complete" => "scrape-complete",
                                        "tweet_update" => "tweet-update",
                                        "error" => "scrape-error",
                                        "login_status" => "login-status",
                                        "login_waiting" => "login-waiting",
                                        "status" => "scrape-status",
                                        "export_complete" => "export-complete",
                                        "analysis_result" => "analysis-result",
                                        "log" => "sidecar-log",
                                        "ready" => "sidecar-ready",
                                        "settings" => "settings-update",
                                        _ => "sidecar-message",
                                    };

                                    let _ = handle.emit(event_name, msg);
                                }
                            }
                            Err(_) => {
                                // Non-JSON output, emit as log
                                if let Some(ref handle) = app_handle {
                                    let _ = handle.emit(
                                        "sidecar-log",
                                        serde_json::json!({
                                            "type": "log",
                                            "level": "debug",
                                            "message": line
                                        }),
                                    );
                                }
                            }
                        }
                    }
                    Err(_) => break,
                }
            }
        });

        // Stderr reader thread - only log errors, don't duplicate stdout logs
        let stderr = child.stderr.take();
        if let Some(stderr) = stderr {
            let app_handle_err = self.app_handle.clone();
            thread::spawn(move || {
                let reader = BufReader::new(stderr);
                for line in reader.lines() {
                    if let Ok(line) = line {
                        // Skip empty lines and lines that look like JSON (to avoid duplicates)
                        if line.trim().is_empty() || line.trim().starts_with('{') {
                            continue;
                        }
                        if let Some(ref handle) = app_handle_err {
                            let _ = handle.emit(
                                "sidecar-log",
                                serde_json::json!({
                                    "type": "log",
                                    "level": "error",
                                    "message": line
                                }),
                            );
                        }
                    }
                }
            });
        }

        self.child = Some(child);
        self.stdin_tx = Some(tx);

        Ok(())
    }

    pub fn send_command(&self, cmd: &Value) -> Result<(), String> {
        let tx = self.stdin_tx.as_ref().ok_or("Sidecar not running")?;
        let json_str =
            serde_json::to_string(cmd).map_err(|e| format!("JSON serialization error: {}", e))?;
        tx.send(json_str)
            .map_err(|e| format!("Failed to send command: {}", e))
    }

    pub fn stop(&mut self) {
        // Send stop command
        if let Some(ref tx) = self.stdin_tx {
            let _ = tx.send(r#"{"command":"stop"}"#.to_string());
        }
        self.stdin_tx = None;

        // Kill process if still running
        if let Some(ref mut child) = self.child {
            let _ = child.kill();
            let _ = child.wait();
        }
        self.child = None;
    }

    fn find_sidecar_path(&self) -> Result<String, String> {
        let cwd = std::env::current_dir().unwrap_or_default();

        let candidates = vec![
            // cwd is project root (e.g. running from project dir)
            cwd.join("python_sidecar").join("service.py"),
            // cwd is src-tauri (Tauri dev runs cargo from src-tauri)
            cwd.parent()
                .unwrap_or(std::path::Path::new("."))
                .join("python_sidecar")
                .join("service.py"),
            // Relative to executable (bundled app)
            std::env::current_exe()
                .unwrap_or_default()
                .parent()
                .unwrap_or(std::path::Path::new("."))
                .join("python_sidecar")
                .join("service.py"),
            // Exe parent's parent (common in bundled Tauri)
            std::env::current_exe()
                .unwrap_or_default()
                .parent()
                .unwrap_or(std::path::Path::new("."))
                .parent()
                .unwrap_or(std::path::Path::new("."))
                .join("python_sidecar")
                .join("service.py"),
        ];

        for path in &candidates {
            if path.exists() {
                return Ok(path.to_string_lossy().to_string());
            }
        }

        Err(format!(
            "Python sidecar not found. Searched: {:?}",
            candidates
                .iter()
                .map(|p| p.to_string_lossy().to_string())
                .collect::<Vec<_>>()
        ))
    }

    fn find_python(&self) -> Result<String, String> {
        // Try common Python executable names
        for name in &["python", "python3", "py"] {
            if Command::new(name)
                .arg("--version")
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .and_then(|mut c| c.wait())
                .is_ok()
            {
                return Ok(name.to_string());
            }
        }
        Err("Python not found. Please install Python 3.8+.".to_string())
    }
}

impl Drop for SidecarManager {
    fn drop(&mut self) {
        self.stop();
    }
}
