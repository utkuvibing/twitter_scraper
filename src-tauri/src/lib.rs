mod commands;
mod db;
mod sidecar;

use db::Database;
use sidecar::SidecarManager;
use std::sync::Mutex;
use tauri::Manager;
use tauri::menu::{MenuBuilder, MenuItemBuilder};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};

pub struct AppState {
    pub db: Mutex<Database>,
    pub sidecar: Mutex<SidecarManager>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let db = Database::new().expect("Failed to initialize database");
    db.run_migrations().expect("Failed to run database migrations");

    let sidecar = SidecarManager::new();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(AppState {
            db: Mutex::new(db),
            sidecar: Mutex::new(sidecar),
        })
        .invoke_handler(tauri::generate_handler![
            commands::scraper::start_scrape,
            commands::scraper::pause_scrape,
            commands::scraper::resume_scrape,
            commands::scraper::cancel_scrape,
            commands::scraper::get_scrape_status,
            commands::auth::login,
            commands::auth::login_manual,
            commands::auth::check_session,
            commands::license::validate_license,
            commands::license::get_license_status,
            commands::export::export_results,
            commands::settings::get_settings,
            commands::settings::save_settings,
            commands::settings::load_settings,
            commands::settings::check_chrome,
            commands::analytics::get_analytics,
            commands::analytics::get_scrape_history,
            commands::analytics::get_tweets_for_scrape,
            commands::analytics::analyze_with_ai,
            commands::analytics::save_scrape_tweets,
            commands::analytics::delete_scrape,
        ])
        .setup(|app| {
            // Initialize sidecar with app handle for event emission
            let handle = app.handle().clone();
            let state = app.state::<AppState>();
            let mut sidecar = state.sidecar.lock().unwrap();
            sidecar.set_app_handle(handle.clone());

            // System tray with right-click menu
            let show = MenuItemBuilder::with_id("show", "Show").build(app)?;
            let quit = MenuItemBuilder::with_id("quit", "Quit").build(app)?;
            let tray_menu = MenuBuilder::new(app)
                .item(&show)
                .separator()
                .item(&quit)
                .build()?;

            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().cloned().unwrap())
                .tooltip("Twitter/X Scraper")
                .menu(&tray_menu)
                .on_menu_event(|app, event| {
                    match event.id().as_ref() {
                        "show" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.unminimize();
                                let _ = window.set_focus();
                            }
                        }
                        "quit" => {
                            app.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(move |tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.unminimize();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
