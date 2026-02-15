use crate::AppState;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tauri::State;

#[derive(Debug, Serialize, Deserialize)]
pub struct AppSettings {
    pub language: String,
    pub chrome_path: String,
    pub scroll_pause_min: f64,
    pub scroll_pause_max: f64,
    pub output_dir: String,
    pub license_key: String,
    pub license_status: String,
    pub theme: String,
}

#[tauri::command]
pub async fn load_settings(
    state: State<'_, AppState>,
) -> Result<AppSettings, String> {
    let db = state.db.lock().map_err(|e| e.to_string())?;
    let settings = db.get_all_settings().map_err(|e| e.to_string())?;

    Ok(AppSettings {
        language: settings.get("language").cloned().unwrap_or_else(|| "en".to_string()),
        chrome_path: settings.get("chrome_path").cloned().unwrap_or_default(),
        scroll_pause_min: settings
            .get("scroll_pause_min")
            .and_then(|v| v.parse().ok())
            .unwrap_or(2.0),
        scroll_pause_max: settings
            .get("scroll_pause_max")
            .and_then(|v| v.parse().ok())
            .unwrap_or(4.0),
        output_dir: settings.get("output_dir").cloned().unwrap_or_default(),
        license_key: settings.get("license_key").cloned().unwrap_or_default(),
        license_status: settings
            .get("license_tier")
            .cloned()
            .unwrap_or_else(|| "free".to_string()),
        theme: settings.get("theme").cloned().unwrap_or_else(|| "dark".to_string()),
    })
}

#[tauri::command]
pub async fn get_settings(
    state: State<'_, AppState>,
) -> Result<HashMap<String, String>, String> {
    let db = state.db.lock().map_err(|e| e.to_string())?;
    db.get_all_settings().map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn save_settings(
    state: State<'_, AppState>,
    settings: AppSettings,
) -> Result<(), String> {
    let db = state.db.lock().map_err(|e| e.to_string())?;

    db.set_setting("language", &settings.language).map_err(|e| e.to_string())?;
    db.set_setting("chrome_path", &settings.chrome_path).map_err(|e| e.to_string())?;
    db.set_setting("scroll_pause_min", &settings.scroll_pause_min.to_string()).map_err(|e| e.to_string())?;
    db.set_setting("scroll_pause_max", &settings.scroll_pause_max.to_string()).map_err(|e| e.to_string())?;
    db.set_setting("output_dir", &settings.output_dir).map_err(|e| e.to_string())?;
    db.set_setting("license_key", &settings.license_key).map_err(|e| e.to_string())?;
    db.set_setting("license_tier", &settings.license_status).map_err(|e| e.to_string())?;
    db.set_setting("theme", &settings.theme).map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
pub async fn check_chrome() -> Result<serde_json::Value, String> {
    let candidates = if cfg!(windows) {
        vec![
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    } else if cfg!(target_os = "macos") {
        vec!["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    } else {
        vec!["/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium"]
    };

    for path in &candidates {
        if std::path::Path::new(path).exists() {
            return Ok(serde_json::json!({
                "installed": true,
                "path": path,
            }));
        }
    }

    // Also try `where` / `which`
    let check_cmd = if cfg!(windows) { "where" } else { "which" };
    if let Ok(output) = std::process::Command::new(check_cmd)
        .arg("chrome")
        .output()
    {
        if output.status.success() {
            let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
            return Ok(serde_json::json!({
                "installed": true,
                "path": path,
            }));
        }
    }

    Ok(serde_json::json!({
        "installed": false,
        "path": null,
    }))
}
