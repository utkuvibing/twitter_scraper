use crate::AppState;
use serde::{Deserialize, Serialize};
use tauri::State;

#[derive(Debug, Deserialize)]
pub struct ScrapeConfig {
    #[serde(rename = "type")]
    pub scrape_type: String,
    pub target: String,
    pub mode: String,
    pub count: Option<i64>,
    pub days: Option<i64>,
    pub start_date: Option<String>,
    pub end_date: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ScrapeResponse {
    pub success: bool,
    pub message: String,
    pub scrape_id: Option<String>,
}

#[tauri::command]
pub async fn start_scrape(
    state: State<'_, AppState>,
    config: ScrapeConfig,
) -> Result<ScrapeResponse, String> {
    let scrape_id = uuid::Uuid::new_v4().to_string()[..8].to_string();

    // Store scrape in database
    {
        let db = state.db.lock().map_err(|e| e.to_string())?;
        db.insert_scrape(
            &scrape_id,
            &config.target,
            &config.scrape_type,
            &config.mode,
        )
        .map_err(|e| e.to_string())?;
    }

    // Build command for Python sidecar
    let mut cmd = serde_json::json!({
        "command": "scrape",
        "type": config.scrape_type,
        "target": config.target,
        "mode": config.mode,
    });

    if let Some(count) = config.count {
        cmd["count"] = serde_json::json!(count);
    }
    if let Some(days) = config.days {
        cmd["days"] = serde_json::json!(days);
    }
    if let Some(ref start) = config.start_date {
        cmd["start_date"] = serde_json::json!(start);
    }
    if let Some(ref end) = config.end_date {
        cmd["end_date"] = serde_json::json!(end);
    }

    // Start sidecar if not running, then send command
    {
        let mut sidecar = state.sidecar.lock().map_err(|e| e.to_string())?;
        if !sidecar.is_running() {
            sidecar.start().map_err(|e| format!("Failed to start sidecar: {}", e))?;
        }
        sidecar
            .send_command(&cmd)
            .map_err(|e| format!("Failed to send scrape command: {}", e))?;
    }

    Ok(ScrapeResponse {
        success: true,
        message: "Scrape started".to_string(),
        scrape_id: Some(scrape_id),
    })
}

#[tauri::command]
pub async fn pause_scrape(state: State<'_, AppState>) -> Result<(), String> {
    let sidecar = state.sidecar.lock().map_err(|e| e.to_string())?;
    if !sidecar.is_running() {
        return Err("Sidecar not running".to_string());
    }
    let cmd = serde_json::json!({"command": "pause"});
    sidecar
        .send_command(&cmd)
        .map_err(|e| format!("Failed to pause: {}", e))
}

#[tauri::command]
pub async fn resume_scrape(state: State<'_, AppState>) -> Result<(), String> {
    let sidecar = state.sidecar.lock().map_err(|e| e.to_string())?;
    if !sidecar.is_running() {
        return Err("Sidecar not running".to_string());
    }
    let cmd = serde_json::json!({"command": "resume"});
    sidecar
        .send_command(&cmd)
        .map_err(|e| format!("Failed to resume: {}", e))
}

#[tauri::command]
pub async fn cancel_scrape(state: State<'_, AppState>) -> Result<(), String> {
    let sidecar = state.sidecar.lock().map_err(|e| e.to_string())?;
    if !sidecar.is_running() {
        return Err("Sidecar not running".to_string());
    }
    let cmd = serde_json::json!({"command": "cancel"});
    sidecar
        .send_command(&cmd)
        .map_err(|e| format!("Failed to cancel: {}", e))
}

#[tauri::command]
pub async fn get_scrape_status(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let sidecar = state.sidecar.lock().map_err(|e| e.to_string())?;
    let cmd = serde_json::json!({"command": "status"});
    sidecar
        .send_command(&cmd)
        .map_err(|e| format!("Failed to get status: {}", e))?;
    Ok(serde_json::json!({"status": "requested"}))
}
