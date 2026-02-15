use crate::AppState;
use serde::Deserialize;
use tauri::State;

#[derive(Debug, Deserialize)]
pub struct ExportConfig {
    pub format: String,
    pub scrape_id: Option<String>,
    pub target: Option<String>,
    pub filename: Option<String>,
    pub output_dir: Option<String>,
}

#[tauri::command]
pub async fn export_results(
    state: State<'_, AppState>,
    config: ExportConfig,
) -> Result<serde_json::Value, String> {
    let sidecar = state.sidecar.lock().map_err(|e| e.to_string())?;

    let mut cmd = serde_json::json!({
        "command": "export",
        "format": config.format,
    });

    if let Some(ref scrape_id) = config.scrape_id {
        cmd["scrape_id"] = serde_json::json!(scrape_id);
    }
    if let Some(ref target) = config.target {
        cmd["target"] = serde_json::json!(target);
    }
    if let Some(ref filename) = config.filename {
        cmd["filename"] = serde_json::json!(filename);
    }
    if let Some(ref output_dir) = config.output_dir {
        cmd["output_dir"] = serde_json::json!(output_dir);
    }

    sidecar
        .send_command(&cmd)
        .map_err(|e| format!("Failed to export: {}", e))?;

    Ok(serde_json::json!({"status": "export_initiated"}))
}
