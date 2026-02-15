use crate::AppState;
use serde::Deserialize;
use tauri::State;
use std::path::PathBuf;
use base64::Engine as _;

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

/// Direct file export - no sidecar needed, no events, just writes content to disk
#[tauri::command]
pub async fn save_export_file(
    filename: String,
    target: String,
    format: String,
    content: String,
    output_dir: Option<String>,
) -> Result<String, String> {
    // Determine extension
    let ext = match format.as_str() {
        "json" => ".json",
        "md" => ".md",
        "docx" => ".docx",
        _ => ".txt",
    };

    // Build filename with extension
    let mut fname = filename;
    if !fname.ends_with(ext) {
        fname.push_str(ext);
    }

    // Determine base output directory
    let base_dir = if let Some(ref dir) = output_dir {
        let p = PathBuf::from(dir);
        if p.is_dir() { p } else { default_output_dir() }
    } else {
        default_output_dir()
    };

    // Create user subdirectory
    let user_dir = base_dir.join(&target);
    std::fs::create_dir_all(&user_dir)
        .map_err(|e| format!("Failed to create directory: {}", e))?;

    let full_path = user_dir.join(&fname);

    // Write content
    std::fs::write(&full_path, content.as_bytes())
        .map_err(|e| format!("Failed to write file: {}", e))?;

    Ok(full_path.to_string_lossy().to_string())
}

/// Binary file export (for docx) - accepts base64-encoded content
#[tauri::command]
pub async fn save_binary_export_file(
    filename: String,
    target: String,
    format: String,
    content_base64: String,
    output_dir: Option<String>,
) -> Result<String, String> {
    let ext = match format.as_str() {
        "docx" => ".docx",
        _ => ".bin",
    };

    let mut fname = filename;
    if !fname.ends_with(ext) {
        fname.push_str(ext);
    }

    let base_dir = if let Some(ref dir) = output_dir {
        let p = PathBuf::from(dir);
        if p.is_dir() { p } else { default_output_dir() }
    } else {
        default_output_dir()
    };

    let user_dir = base_dir.join(&target);
    std::fs::create_dir_all(&user_dir)
        .map_err(|e| format!("Failed to create directory: {}", e))?;

    let full_path = user_dir.join(&fname);

    let bytes = base64::engine::general_purpose::STANDARD
        .decode(&content_base64)
        .map_err(|e| format!("Failed to decode base64: {}", e))?;

    std::fs::write(&full_path, &bytes)
        .map_err(|e| format!("Failed to write file: {}", e))?;

    Ok(full_path.to_string_lossy().to_string())
}

fn default_output_dir() -> PathBuf {
    // Try exe directory first, then current dir
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            return parent.join("output");
        }
    }
    PathBuf::from("output")
}
