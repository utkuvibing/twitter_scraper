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

    // Build safe filename with extension
    let mut fname = safe_filename(&filename);
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
    let user_dir = base_dir.join(safe_path_segment(&target, "export"));
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

    let mut fname = safe_filename(&filename);
    if !fname.ends_with(ext) {
        fname.push_str(ext);
    }

    let base_dir = if let Some(ref dir) = output_dir {
        let p = PathBuf::from(dir);
        if p.is_dir() { p } else { default_output_dir() }
    } else {
        default_output_dir()
    };

    let user_dir = base_dir.join(safe_path_segment(&target, "export"));
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

fn safe_filename(filename: &str) -> String {
    let name = PathBuf::from(filename)
        .file_name()
        .and_then(|v| v.to_str())
        .unwrap_or("export")
        .to_string();

    let name_path = PathBuf::from(&name);
    let stem = name_path
        .file_stem()
        .and_then(|v| v.to_str())
        .unwrap_or("export");

    safe_path_segment(stem, "export")
}

fn safe_path_segment(value: &str, default: &str) -> String {
    let mut cleaned = String::new();
    for ch in value.trim().trim_start_matches('@').chars() {
        let is_forbidden = matches!(
            ch,
            '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*'
        ) || ch.is_control();

        if is_forbidden || ch.is_whitespace() {
            cleaned.push('_');
        } else {
            cleaned.push(ch);
        }
    }

    let cleaned = cleaned.trim_matches(|c| c == ' ' || c == '.' || c == '_' || c == '@');
    let mut result = if cleaned.is_empty() {
        default.to_string()
    } else {
        cleaned.to_string()
    };

    let upper = result.to_ascii_uppercase();
    let reserved = upper == "CON"
        || upper == "PRN"
        || upper == "AUX"
        || upper == "NUL"
        || (upper.len() == 4
            && (upper.starts_with("COM") || upper.starts_with("LPT"))
            && upper[3..].chars().all(|c| ('1'..='9').contains(&c)));

    if reserved {
        result.insert(0, '_');
    }

    result.chars().take(120).collect()
}
