use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::Arc;
use tauri::{Emitter, State};

use crate::db::{AppSettings, Database, FileVersion, StorageStats, TrackedFile, WatchedFolder};
use crate::storage::{DiffResult, Storage};
use crate::watcher::WatcherManager;

pub struct AppState {
    pub db: Arc<Database>,
    pub storage: Arc<Storage>,
    pub watcher: Arc<WatcherManager>,
}

#[tauri::command]
pub fn get_tracked_files(state: State<AppState>) -> Result<Vec<TrackedFile>, String> {
    state.db.get_tracked_files().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_tracked_file(file_id: i64, state: State<AppState>) -> Result<(), String> {
    state.db.delete_tracked_file(file_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_versions(file_id: i64, state: State<AppState>) -> Result<Vec<FileVersion>, String> {
    state.db.get_versions_for_file(file_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_version_text(hash: String, state: State<AppState>) -> Result<String, String> {
    let bytes = state.storage.read_version_bytes(&hash).map_err(|e| e.to_string())?;
    if let Some(docx_txt) = crate::storage::extract_docx_text(&bytes) {
        return Ok(docx_txt);
    }
    state.storage.read_version_text(&hash).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_version_diff(
    version_id: i64,
    compare_with_current: bool,
    state: State<AppState>,
) -> Result<DiffResult, String> {
    let (version, original_path) = match state.db.get_version_by_id(version_id).map_err(|e| e.to_string())? {
        Some(res) => res,
        None => return Err("Version not found".into()),
    };

    if crate::storage::is_visual_document_path(&original_path) {
        return Ok(DiffResult {
            lines: Vec::new(),
            additions: 0,
            deletions: 0,
            is_binary: true,
        });
    }

    let version_bytes = state.storage.read_version_bytes(&version.hash).map_err(|e| e.to_string())?;
    let is_docx = crate::storage::is_docx_path(&original_path) || version_bytes.starts_with(b"PK\x03\x04");

    let version_text = if is_docx {
        match crate::storage::extract_docx_text(&version_bytes) {
            Some(t) => t,
            None => {
                return Ok(DiffResult {
                    lines: Vec::new(),
                    additions: 0,
                    deletions: 0,
                    is_binary: true,
                });
            }
        }
    } else if crate::storage::is_binary_buffer(&version_bytes) {
        return Ok(DiffResult {
            lines: Vec::new(),
            additions: 0,
            deletions: 0,
            is_binary: true,
        });
    } else {
        match String::from_utf8(version_bytes.clone()) {
            Ok(t) => t,
            Err(_) => String::from_utf8_lossy(&version_bytes).to_string(),
        }
    };

    let other_text = if compare_with_current {
        let path = Path::new(&original_path);
        if path.exists() {
            if is_docx {
                if let Ok(cur_bytes) = std::fs::read(path) {
                    crate::storage::extract_docx_text(&cur_bytes).unwrap_or_default()
                } else {
                    String::new()
                }
            } else {
                std::fs::read_to_string(path).unwrap_or_else(|_| String::new())
            }
        } else {
            String::new()
        }
    } else {
        let all_versions = state.db.get_versions_for_file(version.file_id).map_err(|e| e.to_string())?;
        let current_idx = all_versions.iter().position(|v| v.id == version_id);

        if let Some(idx) = current_idx {
            if idx + 1 < all_versions.len() {
                let prev_hash = &all_versions[idx + 1].hash;
                if is_docx {
                    if let Ok(prev_bytes) = state.storage.read_version_bytes(prev_hash) {
                        crate::storage::extract_docx_text(&prev_bytes).unwrap_or_default()
                    } else {
                        String::new()
                    }
                } else {
                    state.storage.read_version_text(prev_hash).unwrap_or_default()
                }
            } else {
                String::new()
            }
        } else {
            String::new()
        }
    };

    let diff = state.storage.compare_diff(&other_text, &version_text);
    Ok(diff)
}

#[tauri::command]
pub fn get_version_data_url(
    hash: String,
    original_path: String,
    state: State<AppState>,
) -> Result<String, String> {
    let ext = Path::new(&original_path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("png");
    state.storage.read_version_data_url(&hash, ext).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_current_file_data_url(path: String) -> Result<Option<String>, String> {
    let p = Path::new(&path);
    if !p.exists() {
        return Ok(None);
    }
    let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("png");
    let bytes = std::fs::read(p).map_err(|e| e.to_string())?;
    let mime = crate::storage::guess_mime(ext);
    let b64 = crate::storage::to_base64(&bytes);
    Ok(Some(format!("data:{};base64,{}", mime, b64)))
}

#[tauri::command]
pub fn get_prev_version_data_url(
    file_id: i64,
    current_version_id: i64,
    original_path: String,
    state: State<AppState>,
) -> Result<Option<String>, String> {
    let all_versions = state.db.get_versions_for_file(file_id).map_err(|e| e.to_string())?;
    let current_idx = all_versions.iter().position(|v| v.id == current_version_id);
    if let Some(idx) = current_idx {
        if idx + 1 < all_versions.len() {
            let prev_hash = &all_versions[idx + 1].hash;
            let ext = Path::new(&original_path)
                .extension()
                .and_then(|e| e.to_str())
                .unwrap_or("png");
            let data_url = state.storage.read_version_data_url(prev_hash, ext).map_err(|e| e.to_string())?;
            return Ok(Some(data_url));
        }
    }
    Ok(None)
}

#[tauri::command]
pub fn restore_version(version_id: i64, state: State<AppState>) -> Result<(), String> {
    let (version, original_path) = match state.db.get_version_by_id(version_id).map_err(|e| e.to_string())? {
        Some(res) => res,
        None => return Err("Version not found".into()),
    };

    let path = Path::new(&original_path);

    // Safety: take a backup of current file before overwriting
    if path.exists() {
        let _ = state.storage.save_file(path);
    }

    state.storage.restore_file(&version.hash, path).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn save_version_as(version_id: i64, target_path: String, state: State<AppState>) -> Result<(), String> {
    let (version, _) = match state.db.get_version_by_id(version_id).map_err(|e| e.to_string())? {
        Some(res) => res,
        None => return Err("Version not found".into()),
    };

    let target = Path::new(&target_path);
    state.storage.restore_file(&version.hash, target).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn get_storage_stats(state: State<AppState>) -> Result<StorageStats, String> {
    state.db.get_storage_stats().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_watched_folders(state: State<AppState>) -> Result<Vec<WatchedFolder>, String> {
    state.db.get_watched_folders().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn add_watched_folder(path: String, state: State<AppState>) -> Result<i64, String> {
    let folder_path = PathBuf::from(&path);
    let id = state.db.add_watched_folder(&path).map_err(|e| e.to_string())?;
    state.watcher.add_folder(folder_path);
    Ok(id)
}

#[tauri::command]
pub fn remove_watched_folder(id: i64, path: String, state: State<AppState>) -> Result<(), String> {
    state.db.remove_watched_folder(id).map_err(|e| e.to_string())?;
    state.watcher.remove_folder(PathBuf::from(path));
    Ok(())
}

#[tauri::command]
pub fn toggle_pause_monitoring(app: tauri::AppHandle, state: State<AppState>) -> Result<bool, String> {
    let is_paused = state.watcher.is_paused();
    let new_paused = !is_paused;
    state.watcher.set_paused(new_paused);
    crate::update_tray_state(&app, "normal");
    let _ = app.emit("monitoring-status-changed", new_paused);
    Ok(new_paused)
}

#[tauri::command]
pub fn get_monitoring_status(state: State<AppState>) -> Result<bool, String> {
    Ok(!state.watcher.is_paused())
}

#[tauri::command]
pub fn get_settings(state: State<AppState>) -> Result<AppSettings, String> {
    state.db.get_settings().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn save_settings(settings: AppSettings, state: State<AppState>) -> Result<(), String> {
    state.db.save_settings(&settings).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn prune_storage(state: State<AppState>) -> Result<serde_json::Value, String> {
    let settings = state.db.get_settings().unwrap_or_default();
    let deleted_versions = state
        .db
        .prune_old_versions(settings.retention_days, settings.max_versions_per_file)
        .map_err(|e| e.to_string())?;

    let active_hashes = state.db.get_all_active_hashes().map_err(|e| e.to_string())?;
    let deleted_objects = state
        .storage
        .prune_unreferenced_objects(&active_hashes)
        .map_err(|e| e.to_string())?;

    Ok(serde_json::json!({
        "deleted_versions": deleted_versions,
        "deleted_objects": deleted_objects
    }))
}

#[tauri::command]
pub fn open_in_explorer(path: String) -> Result<(), String> {
    let p = Path::new(&path);
    if !p.exists() {
        return Err("Файл или папка не существует".into());
    }

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        let mut clean = path.replace('/', "\\");
        if clean.starts_with(r"\\?\") {
            clean = clean[4..].to_string();
        }

        let mut cmd = Command::new("explorer.exe");
        if p.is_dir() {
            cmd.raw_arg(format!("\"{}\"", clean));
        } else {
            cmd.raw_arg(format!("/select,\"{}\"", clean));
        }
        cmd.spawn().map_err(|e| e.to_string())?;
    }

    #[cfg(not(target_os = "windows"))]
    {
        if let Some(parent) = p.parent() {
            let _ = Command::new("open").arg(parent).spawn();
        }
    }

    Ok(())
}

#[tauri::command]
pub fn get_explorer_context_menu_status() -> Result<bool, String> {
    Ok(crate::explorer_integration::is_context_menu_enabled())
}

#[tauri::command]
pub fn set_explorer_context_menu(enabled: bool) -> Result<bool, String> {
    crate::explorer_integration::set_context_menu_enabled(enabled)?;
    Ok(enabled)
}

#[tauri::command]
pub fn get_version_raw_bytes(hash: String, state: State<AppState>) -> Result<Vec<u8>, String> {
    state.storage.read_version_bytes(&hash).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_current_file_raw_bytes(path: String) -> Result<Option<Vec<u8>>, String> {
    let p = Path::new(&path);
    if !p.exists() {
        return Ok(None);
    }
    let bytes = std::fs::read(p).map_err(|e| e.to_string())?;
    Ok(Some(bytes))
}

#[tauri::command]
pub fn open_version_in_external_app(
    version_id: i64,
    state: State<AppState>,
) -> Result<String, String> {
    let (version, original_path) = match state.db.get_version_by_id(version_id).map_err(|e| e.to_string())? {
        Some(res) => res,
        None => return Err("Версия не найдена".into()),
    };

    let filename = Path::new(&original_path)
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("document");

    let temp_path = state
        .storage
        .export_version_to_temp(&version.hash, filename)
        .map_err(|e| e.to_string())?;

    let path_str = temp_path.to_string_lossy().to_string();

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        Command::new("cmd")
            .raw_arg(format!("/c start \"\" \"{}\"", path_str))
            .spawn()
            .map_err(|e| format!("Не удалось открыть внешнее приложение: {}", e))?;
    }

    #[cfg(not(target_os = "windows"))]
    {
        Command::new("open")
            .arg(&path_str)
            .spawn()
            .map_err(|e| format!("Не удалось открыть внешнее приложение: {}", e))?;
    }

    Ok(path_str)
}

