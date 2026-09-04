use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Sender};
use std::sync::Arc;
use std::time::Duration;
use std::thread;

use notify_debouncer_mini::{new_debouncer, notify::RecursiveMode, DebounceEventResult};
use parking_lot::RwLock;
use ignore::gitignore::GitignoreBuilder;
use tauri::Emitter;
use walkdir::WalkDir;

use crate::db::Database;
use crate::storage::Storage;

pub enum WatcherCommand {
    AddFolder(PathBuf),
    RemoveFolder(PathBuf),
    #[allow(dead_code)]
    Reload,
}

pub struct WatcherManager {
    db: Arc<Database>,
    storage: Arc<Storage>,
    app_handle: tauri::AppHandle,
    is_paused: Arc<RwLock<bool>>,
    cmd_sender: Arc<RwLock<Option<Sender<WatcherCommand>>>>,
}

impl WatcherManager {
    pub fn new(
        db: Arc<Database>,
        storage: Arc<Storage>,
        app_handle: tauri::AppHandle,
    ) -> Self {
        Self {
            db,
            storage,
            app_handle,
            is_paused: Arc::new(RwLock::new(false)),
            cmd_sender: Arc::new(RwLock::new(None)),
        }
    }

    pub fn set_paused(&self, paused: bool) {
        *self.is_paused.write() = paused;
    }

    pub fn is_paused(&self) -> bool {
        *self.is_paused.read()
    }

    pub fn add_folder(&self, path: PathBuf) {
        if let Some(tx) = self.cmd_sender.read().as_ref() {
            let _ = tx.send(WatcherCommand::AddFolder(path));
        }
    }

    pub fn remove_folder(&self, path: PathBuf) {
        if let Some(tx) = self.cmd_sender.read().as_ref() {
            let _ = tx.send(WatcherCommand::RemoveFolder(path));
        }
    }

    #[allow(dead_code)]
    pub fn reload(&self) {
        if let Some(tx) = self.cmd_sender.read().as_ref() {
            let _ = tx.send(WatcherCommand::Reload);
        }
    }

    pub fn start(&self) {
        let db = Arc::clone(&self.db);
        let storage = Arc::clone(&self.storage);
        let app_handle = self.app_handle.clone();
        let is_paused = Arc::clone(&self.is_paused);

        let (cmd_tx, cmd_rx) = channel::<WatcherCommand>();
        *self.cmd_sender.write() = Some(cmd_tx);

        thread::spawn(move || {
            let (event_tx, event_rx) = channel::<DebounceEventResult>();

            let mut debouncer = match new_debouncer(Duration::from_millis(500), event_tx) {
                Ok(d) => d,
                Err(e) => {
                    eprintln!("Failed to initialize file debouncer: {}", e);
                    return;
                }
            };

            // Initial load of watched folders
            if let Ok(folders) = db.get_watched_folders() {
                for folder in folders {
                    let path = PathBuf::from(&folder.path);
                    if path.exists() {
                        let _ = debouncer.watcher().watch(&path, RecursiveMode::Recursive);
                    }
                }
            }

            loop {
                // Check for commands (non-blocking / timed)
                while let Ok(cmd) = cmd_rx.try_recv() {
                    match cmd {
                        WatcherCommand::AddFolder(path) => {
                            if path.exists() {
                                let _ = debouncer.watcher().watch(&path, RecursiveMode::Recursive);
                                // Initial scan for this folder in background
                                let db_clone = Arc::clone(&db);
                                let storage_clone = Arc::clone(&storage);
                                let app_clone = app_handle.clone();
                                let path_clone = path.clone();
                                thread::spawn(move || {
                                    Self::scan_folder(&db_clone, &storage_clone, &app_clone, &path_clone);
                                });
                            }
                        }
                        WatcherCommand::RemoveFolder(path) => {
                            let _ = debouncer.watcher().unwatch(&path);
                        }
                        WatcherCommand::Reload => {
                            if let Ok(folders) = db.get_watched_folders() {
                                for folder in folders {
                                    let p = PathBuf::from(&folder.path);
                                    if p.exists() {
                                        let _ = debouncer.watcher().watch(&p, RecursiveMode::Recursive);
                                    }
                                }
                            }
                        }
                    }
                }

                // Process file change events
                match event_rx.recv_timeout(Duration::from_millis(250)) {
                    Ok(Ok(events)) => {
                        if *is_paused.read() {
                            continue;
                        }

                        let custom_ignores = db
                            .get_settings()
                            .map(|s| s.ignore_patterns)
                            .unwrap_or_default();

                        for event in events {
                            let path = event.path;
                            if !path.is_file() {
                                continue;
                            }

                            if Self::should_ignore(&path, &custom_ignores) {
                                continue;
                            }

                            Self::process_file_change(&db, &storage, &app_handle, &path);
                        }
                    }
                    Ok(Err(e)) => {
                        eprintln!("Watcher error: {:?}", e);
                    }
                    Err(std::sync::mpsc::RecvTimeoutError::Timeout) => {
                        // Regular timeout to re-check command channel
                    }
                    Err(std::sync::mpsc::RecvTimeoutError::Disconnected) => {
                        break;
                    }
                }
            }
        });
    }

    pub fn scan_folder(
        db: &Database,
        storage: &Storage,
        app_handle: &tauri::AppHandle,
        folder_path: &Path,
    ) {
        let custom_ignores = db
            .get_settings()
            .map(|s| s.ignore_patterns)
            .unwrap_or_default();

        for entry in WalkDir::new(folder_path).into_iter().filter_map(|e| e.ok()) {
            let path = entry.path();
            if path.is_file() && !Self::should_ignore(path, &custom_ignores) {
                Self::process_file_change(db, storage, app_handle, path);
            }
        }
    }

    fn should_ignore(path: &Path, custom_ignores: &[String]) -> bool {
        let path_str = path.to_string_lossy().to_lowercase();

        // Built-in critical ignores
        if path_str.contains(".git")
            || path_str.contains("node_modules")
            || path_str.contains("target")
            || path_str.contains("__pycache__")
            || path_str.contains(".venv")
            || path_str.contains(".svelte-kit")
            || path_str.contains("undoit_restore_tmp")
            || path_str.ends_with(".tmp")
            || path_str.ends_with(".crdownload")
        {
            return true;
        }

        if let Some(file_name) = path.file_name().and_then(|n| n.to_str()) {
            if file_name.starts_with("~$") || file_name.starts_with(".#") {
                return true;
            }
        }

        // Custom user ignore patterns
        for pattern in custom_ignores {
            let p_lower = pattern.to_lowercase();
            if p_lower.starts_with("*.") {
                let ext = &p_lower[1..];
                if path_str.ends_with(ext) {
                    return true;
                }
            } else if path_str.contains(&p_lower) {
                return true;
            }
        }

        // .gitignore check if in git repo
        if let Some(parent) = path.parent() {
            let mut builder = GitignoreBuilder::new(parent);
            builder.add(parent.join(".gitignore"));
            if let Ok(gitignore) = builder.build() {
                if gitignore.matched(path, false).is_ignore() {
                    return true;
                }
            }
        }

        false
    }

    fn process_file_change(
        db: &Database,
        storage: &Storage,
        app_handle: &tauri::AppHandle,
        path: &Path,
    ) {
        let canonical_str = match path.canonicalize() {
            Ok(p) => {
                let s = p.to_string_lossy().to_string();
                if s.starts_with(r"\\?\") {
                    s[4..].to_string()
                } else {
                    s
                }
            }
            Err(_) => path.to_string_lossy().to_string(),
        };

        // Retry logic for Windows file locking (Sharing violation / in-use)
        let mut attempts = 0;
        let mut save_result = None;

        while attempts < 3 {
            match storage.save_file(path) {
                Ok(res) => {
                    save_result = Some(res);
                    break;
                }
                Err(_) => {
                    attempts += 1;
                    thread::sleep(Duration::from_millis(100));
                }
            }
        }

        let (hash, raw_size, comp_size) = match save_result {
            Some(res) => res,
            None => return,
        };

        let file_id = match db.get_or_create_tracked_file(&canonical_str, None) {
            Ok(id) => id,
            Err(_) => return,
        };

        if let Ok(Some(last_hash)) = db.get_last_version_hash(file_id) {
            if last_hash == hash {
                return;
            }
        }

        if let Ok(version_id) = db.add_version(file_id, &hash, raw_size as i64, comp_size as i64) {
            crate::update_tray_state(app_handle, "saving");
            let _ = app_handle.emit("version-saved", serde_json::json!({
                "file_id": file_id,
                "version_id": version_id,
                "path": canonical_str,
                "file_size": raw_size,
                "compressed_size": comp_size,
            }));

            let handle_clone = app_handle.clone();
            thread::spawn(move || {
                thread::sleep(Duration::from_millis(500));
                crate::update_tray_state(&handle_clone, "normal");
            });
        }
    }
}
