use crate::AppState;
use serde::Serialize;
use tauri::State;

#[derive(Debug, Serialize)]
pub struct LicenseInfo {
    pub valid: bool,
    pub status: String,
    pub message: String,
}

#[tauri::command]
pub async fn validate_license(
    state: State<'_, AppState>,
    key: String,
) -> Result<LicenseInfo, String> {
    if key.is_empty() {
        return Ok(LicenseInfo {
            valid: true,
            status: "free".to_string(),
            message: "Free tier active".to_string(),
        });
    }

    // Store key in settings
    {
        let db = state.db.lock().map_err(|e| e.to_string())?;
        db.set_setting("license_key", &key)
            .map_err(|e| e.to_string())?;
    }

    if key.starts_with("PRO-") {
        let db = state.db.lock().map_err(|e| e.to_string())?;
        db.set_setting("license_tier", "pro")
            .map_err(|e| e.to_string())?;
        Ok(LicenseInfo {
            valid: true,
            status: "pro".to_string(),
            message: "Pro license activated".to_string(),
        })
    } else if key.starts_with("PLUS-") {
        let db = state.db.lock().map_err(|e| e.to_string())?;
        db.set_setting("license_tier", "pro_plus")
            .map_err(|e| e.to_string())?;
        Ok(LicenseInfo {
            valid: true,
            status: "pro_plus".to_string(),
            message: "Pro+ license activated".to_string(),
        })
    } else {
        Ok(LicenseInfo {
            valid: false,
            status: "free".to_string(),
            message: "Invalid license key. Keys should start with PRO- or PLUS-".to_string(),
        })
    }
}

#[tauri::command]
pub async fn get_license_status(state: State<'_, AppState>) -> Result<LicenseInfo, String> {
    let db = state.db.lock().map_err(|e| e.to_string())?;

    let status = db
        .get_setting("license_tier")
        .map_err(|e| e.to_string())?
        .unwrap_or_else(|| "free".to_string());

    let key = db
        .get_setting("license_key")
        .map_err(|e| e.to_string())?
        .unwrap_or_default();

    Ok(LicenseInfo {
        valid: !key.is_empty() || status == "free",
        status,
        message: "License status retrieved".to_string(),
    })
}
