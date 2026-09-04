mod db;
mod storage;
mod watcher;
mod commands;
pub mod explorer_integration;
pub mod icon_generator;
pub mod single_instance;

use std::sync::Arc;
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager,
};

use commands::AppState;
use db::Database;
use storage::Storage;
use watcher::WatcherManager;

pub struct TrayMenuItems {
    pub status: MenuItem<tauri::Wry>,
    pub toggle_pause: MenuItem<tauri::Wry>,
}

pub fn update_tray_state(app: &tauri::AppHandle, state_name: &str) {
    let is_paused = if let Some(app_state) = app.try_state::<AppState>() {
        app_state.watcher.is_paused()
    } else {
        false
    };

    if let Some(menu_items) = app.try_state::<TrayMenuItems>() {
        if is_paused {
            let _ = menu_items.status.set_text("⏸ Undoit: Мониторинг приостановлен");
            let _ = menu_items.toggle_pause.set_text("▶ Возобновить отслеживание");
        } else {
            let _ = menu_items.status.set_text("● Undoit: Мониторинг активен");
            let _ = menu_items.toggle_pause.set_text("⏸ Приостановить отслеживание");
        }
    }

    if let Some(tray) = app.tray_by_id("main_tray") {
        let (fill_pct, files_count, vers_count, comp_bytes, saved_ratio) = {
            if let Some(app_state) = app.try_state::<AppState>() {
                if let Ok(stats) = app_state.db.get_storage_stats() {
                    let settings = app_state.db.get_settings().unwrap_or_default();
                    let max_bytes = if settings.max_storage_mb > 0 {
                        settings.max_storage_mb as f64 * 1024.0 * 1024.0
                    } else {
                        1024.0 * 1024.0 * 1024.0 // 1 GB default
                    };
                    let pct = (stats.total_compressed_bytes as f64 / max_bytes).clamp(0.0, 1.0) as f32;
                    (pct, stats.total_files, stats.total_versions, stats.total_compressed_bytes, stats.saved_ratio)
                } else {
                    (0.0f32, 0, 0, 0, 0.0)
                }
            } else {
                (0.0f32, 0, 0, 0, 0.0)
            }
        };

        let effective_state = if state_name == "normal" {
            if is_paused {
                "paused"
            } else if files_count == 0 {
                "inactive"
            } else {
                "normal"
            }
        } else {
            state_name
        };

        let icon = icon_generator::generate_shield_icon(effective_state, fill_pct);
        let _ = tray.set_icon(Some(icon));

        let status_desc = match effective_state {
            "paused" => "Мониторинг приостановлен",
            "saving" => "Сохранение снимка...",
            "inactive" => "Нет элементов для отслеживания",
            _ => "Мониторинг активен (Zstd)",
        };

        let mb = comp_bytes as f64 / (1024.0 * 1024.0);
        let tooltip = format!(
            "Undoit: {}\nФайлов: {} | Снимков: {}\nХранилище: {:.1} MB (экономия {:.0}%)",
            status_desc, files_count, vers_count, mb, saved_ratio
        );
        let _ = tray.set_tooltip(Some(tooltip));
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    if single_instance::handle_potential_secondary_instance() {
        return;
    }

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--minimized"]),
        ))
        .setup(|app| {
            #[cfg(target_os = "windows")]
            if let Some(mutex) = single_instance::NamedMutex::try_acquire("Local\\Undoit_SingleInstance_Mutex_Kobalt") {
                app.manage(mutex);
            }

            single_instance::start_primary_ipc_listener(app.handle().clone());

            let app_data_dir = app
                .path()
                .app_data_dir()
                .unwrap_or_else(|_| std::path::PathBuf::from("UndoitData"));

            let db = Arc::new(Database::new(&app_data_dir).expect("Failed to initialize database"));
            let storage = Arc::new(Storage::new(&app_data_dir).expect("Failed to initialize storage"));

            let app_handle = app.handle().clone();
            let watcher = Arc::new(WatcherManager::new(
                Arc::clone(&db),
                Arc::clone(&storage),
                app_handle.clone(),
            ));

            watcher.start();

            app.manage(AppState {
                db,
                storage,
                watcher,
            });

            // Set main window icon explicitly
            if let Some(window) = app.get_webview_window("main") {
                if let Some(icon) = app.default_window_icon() {
                    let _ = window.set_icon(icon.clone());
                }
            }

            // Ensure explorer context menu has fresh icon if enabled
            if explorer_integration::is_context_menu_enabled() {
                let _ = explorer_integration::set_context_menu_enabled(true);
            }

            // System Tray setup with Rich Menu
            let status_i = MenuItem::with_id(app, "status", "● Undoit: Мониторинг активен", false, None::<&str>)?;
            let sep1 = PredefinedMenuItem::separator(app)?;
            let open_i = MenuItem::with_id(app, "open", "📂 Открыть окно Undoit", true, None::<&str>)?;
            let settings_i = MenuItem::with_id(app, "settings", "⚙ Настройки...", true, None::<&str>)?;
            let add_folder_i = MenuItem::with_id(app, "add_folder", "➕ Добавить папку в мониторинг...", true, None::<&str>)?;
            let sep2 = PredefinedMenuItem::separator(app)?;
            let pause_i = MenuItem::with_id(app, "toggle_pause", "⏸ Приостановить отслеживание", true, None::<&str>)?;
            let prune_i = MenuItem::with_id(app, "prune", "🧹 Очистить устаревшие версии", true, None::<&str>)?;
            let sep3 = PredefinedMenuItem::separator(app)?;
            let quit_i = MenuItem::with_id(app, "quit", "❌ Выход", true, None::<&str>)?;

            let menu = Menu::with_items(
                app,
                &[
                    &status_i,
                    &sep1,
                    &open_i,
                    &settings_i,
                    &add_folder_i,
                    &sep2,
                    &pause_i,
                    &prune_i,
                    &sep3,
                    &quit_i,
                ],
            )?;

            app.manage(TrayMenuItems {
                status: status_i.clone(),
                toggle_pause: pause_i.clone(),
            });

            let initial_icon = icon_generator::generate_shield_icon("normal", 0.0);

            let _tray = TrayIconBuilder::with_id("main_tray")
                .icon(initial_icon)
                .menu(&menu)
                .tooltip("Undoit - Time Machine\nМониторинг активен")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "settings" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                            let _ = window.emit("tray-open-settings", ());
                        }
                    }
                    "add_folder" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                            let _ = window.emit("tray-open-add-folder", ());
                        }
                    }
                    "toggle_pause" => {
                        if let Some(state) = app.try_state::<AppState>() {
                            let is_paused = state.watcher.is_paused();
                            let new_paused = !is_paused;
                            state.watcher.set_paused(new_paused);
                            update_tray_state(app, "normal");
                            let _ = app.emit("monitoring-status-changed", new_paused);
                        }
                    }
                    "prune" => {
                        if let Some(state) = app.try_state::<AppState>() {
                            let settings = state.db.get_settings().unwrap_or_default();
                            let _ = state.db.prune_old_versions(settings.retention_days, settings.max_versions_per_file);
                            if let Ok(active_hashes) = state.db.get_all_active_hashes() {
                                let _ = state.storage.prune_unreferenced_objects(&active_hashes);
                            }
                            let _ = app.emit("storage-pruned", ());
                            update_tray_state(app, "normal");
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| match event {
                    TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } => {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            if let Ok(visible) = window.is_visible() {
                                if visible {
                                    let _ = window.hide();
                                } else {
                                    let _ = window.show();
                                    let _ = window.set_focus();
                                }
                            } else {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
                    TrayIconEvent::DoubleClick {
                        button: MouseButton::Left,
                        ..
                    } => {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                            let _ = window.emit("tray-open-settings", ());
                        }
                    }
                    _ => {}
                })
                .build(app)?;

            // Update initial tray state with stats
            let app_h = app.handle().clone();
            std::thread::spawn(move || {
                std::thread::sleep(std::time::Duration::from_millis(500));
                update_tray_state(&app_h, "normal");
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            // Hide to tray instead of quitting when close button is clicked
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_tracked_files,
            commands::delete_tracked_file,
            commands::get_versions,
            commands::get_version_text,
            commands::get_version_diff,
            commands::get_version_data_url,
            commands::get_current_file_data_url,
            commands::get_prev_version_data_url,
            commands::restore_version,
            commands::save_version_as,
            commands::get_storage_stats,
            commands::get_watched_folders,
            commands::add_watched_folder,
            commands::remove_watched_folder,
            commands::toggle_pause_monitoring,
            commands::get_monitoring_status,
            commands::get_settings,
            commands::save_settings,
            commands::prune_storage,
            commands::open_in_explorer,
            commands::get_explorer_context_menu_status,
            commands::set_explorer_context_menu,
            commands::get_version_raw_bytes,
            commands::get_current_file_raw_bytes,
            commands::open_version_in_external_app,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
