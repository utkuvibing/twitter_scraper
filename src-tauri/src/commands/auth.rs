use crate::AppState;
use serde::Deserialize;
use tauri::State;

#[derive(Debug, Deserialize)]
pub struct LoginCredentials {
    pub method: String,
    pub username: Option<String>,
    pub password: Option<String>,
    pub chrome_path: Option<String>,
}

#[tauri::command]
pub async fn login(
    state: State<'_, AppState>,
    credentials: LoginCredentials,
) -> Result<serde_json::Value, String> {
    let mut sidecar = state.sidecar.lock().map_err(|e| e.to_string())?;

    // Auto-start sidecar if not running
    if !sidecar.is_running() {
        sidecar.start().map_err(|e| format!("Failed to start sidecar: {}", e))?;
    }

    let mut cmd = serde_json::json!({
        "command": "login",
        "method": credentials.method,
    });

    if let Some(ref username) = credentials.username {
        cmd["username"] = serde_json::json!(username);
    }
    if let Some(ref password) = credentials.password {
        cmd["password"] = serde_json::json!(password);
    }
    if let Some(ref chrome_path) = credentials.chrome_path {
        cmd["chrome_path"] = serde_json::json!(chrome_path);
    }

    sidecar
        .send_command(&cmd)
        .map_err(|e| format!("Failed to send login command: {}", e))?;

    Ok(serde_json::json!({"status": "login_initiated"}))
}

#[tauri::command]
pub async fn login_manual(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let mut sidecar = state.sidecar.lock().map_err(|e| e.to_string())?;

    if !sidecar.is_running() {
        sidecar.start().map_err(|e| format!("Failed to start sidecar: {}", e))?;
    }

    let cmd = serde_json::json!({
        "command": "login",
        "method": "manual",
    });

    sidecar
        .send_command(&cmd)
        .map_err(|e| format!("Failed to send login command: {}", e))?;

    Ok(serde_json::json!({"status": "manual_login_initiated"}))
}

#[tauri::command]
pub async fn check_session(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let sidecar = state.sidecar.lock().map_err(|e| e.to_string())?;
    Ok(serde_json::json!({
        "has_session": sidecar.is_running(),
    }))
}
