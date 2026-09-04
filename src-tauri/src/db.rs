use std::collections::HashSet;
use std::path::{Path, PathBuf};
use rusqlite::{params, Connection, Result};
use serde::{Deserialize, Serialize};
use chrono::{Duration, Utc};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct WatchedFolder {
    pub id: i64,
    pub path: String,
    pub created_at: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TrackedFile {
    pub id: i64,
    pub original_path: String,
    pub filename: String,
    pub folder_id: Option<i64>,
    pub is_active: bool,
    pub updated_at: String,
    pub version_count: i64,
    pub latest_size: i64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FileVersion {
    pub id: i64,
    pub file_id: i64,
    pub timestamp: String,
    pub hash: String,
    pub file_size: i64,
    pub compressed_size: i64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StorageStats {
    pub total_versions: i64,
    pub total_files: i64,
    pub total_original_bytes: i64,
    pub total_compressed_bytes: i64,
    pub saved_ratio: f64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AppSettings {
    pub retention_days: i64,
    pub max_versions_per_file: i64,
    pub max_storage_mb: i64,
    pub ignore_patterns: Vec<String>,
    pub theme: String,
    pub autostart: bool,
    pub minimize_to_tray: bool,
    pub language: String,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            retention_days: 30,
            max_versions_per_file: 50,
            max_storage_mb: 2048,
            ignore_patterns: vec![
                "*.tmp".to_string(),
                "*.log".to_string(),
                "*.crdownload".to_string(),
                "~$*".to_string(),
                ".#*".to_string(),
                ".git".to_string(),
                "node_modules".to_string(),
                "target".to_string(),
                ".venv".to_string(),
                "__pycache__".to_string(),
                "build".to_string(),
                "dist".to_string(),
                ".svelte-kit".to_string(),
            ],
            theme: "dark".to_string(),
            autostart: false,
            minimize_to_tray: true,
            language: "ru".to_string(),
        }
    }
}

pub struct Database {
    db_path: PathBuf,
}

impl Database {
    pub fn new(app_data_dir: &Path) -> Result<Self> {
        std::fs::create_dir_all(app_data_dir).ok();
        let db_path = app_data_dir.join("metadata.db");
        let db = Self { db_path };
        db.init_schema()?;
        Ok(db)
    }

    pub fn get_connection(&self) -> Result<Connection> {
        let conn = Connection::open(&self.db_path)?;
        conn.execute_batch(
            "PRAGMA journal_mode = WAL;
             PRAGMA synchronous = NORMAL;
             PRAGMA busy_timeout = 5000;
             PRAGMA foreign_keys = ON;",
        )?;
        Ok(conn)
    }

    fn init_schema(&self) -> Result<()> {
        let conn = self.get_connection()?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS watched_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tracked_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL UNIQUE,
                folder_id INTEGER REFERENCES watched_folders(id) ON DELETE SET NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL REFERENCES tracked_files(id) ON DELETE CASCADE,
                timestamp TEXT NOT NULL,
                hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                compressed_size INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_versions_file_id ON versions(file_id);
            CREATE INDEX IF NOT EXISTS idx_versions_timestamp ON versions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_tracked_files_path ON tracked_files(original_path);",
        )?;
        Ok(())
    }

    pub fn get_settings(&self) -> Result<AppSettings> {
        let conn = self.get_connection()?;
        let mut stmt = conn.prepare("SELECT key, value FROM settings")?;
        let rows = stmt.query_map([], |row| {
            let key: String = row.get(0)?;
            let val: String = row.get(1)?;
            Ok((key, val))
        })?;

        let mut defaults = AppSettings::default();
        for r in rows {
            let (key, val) = r?;
            match key.as_str() {
                "retention_days" => {
                    if let Ok(v) = val.parse::<i64>() {
                        defaults.retention_days = v;
                    }
                }
                "max_versions_per_file" => {
                    if let Ok(v) = val.parse::<i64>() {
                        defaults.max_versions_per_file = v;
                    }
                }
                "max_storage_mb" => {
                    if let Ok(v) = val.parse::<i64>() {
                        defaults.max_storage_mb = v;
                    }
                }
                "ignore_patterns" => {
                    if let Ok(v) = serde_json::from_str::<Vec<String>>(&val) {
                        defaults.ignore_patterns = v;
                    }
                }
                "theme" => defaults.theme = val,
                "autostart" => defaults.autostart = val == "true" || val == "1",
                "minimize_to_tray" => defaults.minimize_to_tray = val == "true" || val == "1",
                "language" => defaults.language = val,
                _ => {}
            }
        }

        Ok(defaults)
    }

    pub fn save_settings(&self, settings: &AppSettings) -> Result<()> {
        let conn = self.get_connection()?;
        let mut stmt = conn.prepare("INSERT OR REPLACE INTO settings (key, value) VALUES (?1, ?2)")?;

        stmt.execute(params!["retention_days", settings.retention_days.to_string()])?;
        stmt.execute(params!["max_versions_per_file", settings.max_versions_per_file.to_string()])?;
        stmt.execute(params!["max_storage_mb", settings.max_storage_mb.to_string()])?;
        stmt.execute(params![
            "ignore_patterns",
            serde_json::to_string(&settings.ignore_patterns).unwrap_or_default()
        ])?;
        stmt.execute(params!["theme", settings.theme])?;
        stmt.execute(params!["autostart", settings.autostart.to_string()])?;
        stmt.execute(params!["minimize_to_tray", settings.minimize_to_tray.to_string()])?;
        stmt.execute(params!["language", settings.language])?;

        Ok(())
    }

    pub fn add_watched_folder(&self, path: &str) -> Result<i64> {
        let conn = self.get_connection()?;
        let now = Utc::now().to_rfc3339();
        conn.execute(
            "INSERT OR IGNORE INTO watched_folders (path, created_at) VALUES (?1, ?2)",
            params![path, now],
        )?;
        Ok(conn.last_insert_rowid())
    }

    pub fn remove_watched_folder(&self, id: i64) -> Result<()> {
        let conn = self.get_connection()?;
        conn.execute("DELETE FROM watched_folders WHERE id = ?1", params![id])?;
        Ok(())
    }

    pub fn get_watched_folders(&self) -> Result<Vec<WatchedFolder>> {
        let conn = self.get_connection()?;
        let mut stmt = conn.prepare("SELECT id, path, created_at FROM watched_folders ORDER BY path ASC")?;
        let rows = stmt.query_map([], |row| {
            Ok(WatchedFolder {
                id: row.get(0)?,
                path: row.get(1)?,
                created_at: row.get(2)?,
            })
        })?;
        let mut folders = Vec::new();
        for r in rows {
            folders.push(r?);
        }
        Ok(folders)
    }

    pub fn get_or_create_tracked_file(&self, original_path: &str, folder_id: Option<i64>) -> Result<i64> {
        let conn = self.get_connection()?;
        let now = Utc::now().to_rfc3339();

        let mut stmt = conn.prepare("SELECT id FROM tracked_files WHERE original_path = ?1")?;
        let mut rows = stmt.query(params![original_path])?;
        if let Some(row) = rows.next()? {
            return row.get(0);
        }

        conn.execute(
            "INSERT INTO tracked_files (original_path, folder_id, is_active, updated_at) VALUES (?1, ?2, 1, ?3)",
            params![original_path, folder_id, now],
        )?;
        Ok(conn.last_insert_rowid())
    }

    pub fn delete_tracked_file(&self, file_id: i64) -> Result<()> {
        let conn = self.get_connection()?;
        conn.execute("DELETE FROM tracked_files WHERE id = ?1", params![file_id])?;
        Ok(())
    }

    pub fn get_last_version_hash(&self, file_id: i64) -> Result<Option<String>> {
        let conn = self.get_connection()?;
        let mut stmt = conn.prepare("SELECT hash FROM versions WHERE file_id = ?1 ORDER BY timestamp DESC LIMIT 1")?;
        let mut rows = stmt.query(params![file_id])?;
        if let Some(row) = rows.next()? {
            Ok(Some(row.get(0)?))
        } else {
            Ok(None)
        }
    }

    pub fn add_version(&self, file_id: i64, hash: &str, file_size: i64, compressed_size: i64) -> Result<i64> {
        let conn = self.get_connection()?;
        let now = Utc::now().to_rfc3339();

        conn.execute(
            "INSERT INTO versions (file_id, timestamp, hash, file_size, compressed_size)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![file_id, now, hash, file_size, compressed_size],
        )?;

        let version_id = conn.last_insert_rowid();

        conn.execute(
            "UPDATE tracked_files SET updated_at = ?1 WHERE id = ?2",
            params![now, file_id],
        )?;

        Ok(version_id)
    }

    pub fn get_tracked_files(&self) -> Result<Vec<TrackedFile>> {
        let conn = self.get_connection()?;
        let mut stmt = conn.prepare(
            "SELECT tf.id, tf.original_path, tf.folder_id, tf.is_active, tf.updated_at,
                    COUNT(v.id) as version_count,
                    COALESCE(MAX(v.file_size), 0) as latest_size
             FROM tracked_files tf
             LEFT JOIN versions v ON tf.id = v.file_id
             WHERE tf.is_active = 1
             GROUP BY tf.id
             ORDER BY tf.updated_at DESC",
        )?;

        let rows = stmt.query_map([], |row| {
            let original_path: String = row.get(1)?;
            let filename = Path::new(&original_path)
                .file_name()
                .map(|f| f.to_string_lossy().into_owned())
                .unwrap_or_else(|| original_path.clone());

            Ok(TrackedFile {
                id: row.get(0)?,
                original_path,
                filename,
                folder_id: row.get(2)?,
                is_active: row.get::<_, i64>(3)? == 1,
                updated_at: row.get(4)?,
                version_count: row.get(5)?,
                latest_size: row.get(6)?,
            })
        })?;

        let mut files = Vec::new();
        for r in rows {
            files.push(r?);
        }
        Ok(files)
    }

    pub fn get_versions_for_file(&self, file_id: i64) -> Result<Vec<FileVersion>> {
        let conn = self.get_connection()?;
        let mut stmt = conn.prepare(
            "SELECT id, file_id, timestamp, hash, file_size, compressed_size
             FROM versions
             WHERE file_id = ?1
             ORDER BY timestamp DESC",
        )?;

        let rows = stmt.query_map(params![file_id], |row| {
            Ok(FileVersion {
                id: row.get(0)?,
                file_id: row.get(1)?,
                timestamp: row.get(2)?,
                hash: row.get(3)?,
                file_size: row.get(4)?,
                compressed_size: row.get(5)?,
            })
        })?;

        let mut versions = Vec::new();
        for r in rows {
            versions.push(r?);
        }
        Ok(versions)
    }

    pub fn get_version_by_id(&self, version_id: i64) -> Result<Option<(FileVersion, String)>> {
        let conn = self.get_connection()?;
        let mut stmt = conn.prepare(
            "SELECT v.id, v.file_id, v.timestamp, v.hash, v.file_size, v.compressed_size, tf.original_path
             FROM versions v
             JOIN tracked_files tf ON v.file_id = tf.id
             WHERE v.id = ?1",
        )?;

        let mut rows = stmt.query(params![version_id])?;
        if let Some(row) = rows.next()? {
            let version = FileVersion {
                id: row.get(0)?,
                file_id: row.get(1)?,
                timestamp: row.get(2)?,
                hash: row.get(3)?,
                file_size: row.get(4)?,
                compressed_size: row.get(5)?,
            };
            let original_path: String = row.get(6)?;
            Ok(Some((version, original_path)))
        } else {
            Ok(None)
        }
    }

    pub fn get_all_active_hashes(&self) -> Result<HashSet<String>> {
        let conn = self.get_connection()?;
        let mut stmt = conn.prepare("SELECT DISTINCT hash FROM versions")?;
        let rows = stmt.query_map([], |row| row.get::<_, String>(0))?;
        let mut set = HashSet::new();
        for r in rows {
            set.insert(r?);
        }
        Ok(set)
    }

    pub fn prune_old_versions(&self, retention_days: i64, max_versions_per_file: i64) -> Result<usize> {
        let mut conn = self.get_connection()?;
        let tx = conn.transaction()?;

        let mut deleted_count = 0;

        // 1. Delete versions older than retention_days (if > 0)
        if retention_days > 0 {
            let cutoff = (Utc::now() - Duration::days(retention_days)).to_rfc3339();
            // Ensure we keep at least the latest 1 version per file even if old
            deleted_count += tx.execute(
                "DELETE FROM versions
                 WHERE timestamp < ?1
                   AND id NOT IN (
                       SELECT id FROM (
                           SELECT id, ROW_NUMBER() OVER (PARTITION BY file_id ORDER BY timestamp DESC) as rn
                           FROM versions
                       ) WHERE rn = 1
                   )",
                params![cutoff],
            )?;
        }

        // 2. Limit maximum versions per file (if > 0)
        if max_versions_per_file > 0 {
            deleted_count += tx.execute(
                "DELETE FROM versions
                 WHERE id IN (
                     SELECT id FROM (
                         SELECT id, ROW_NUMBER() OVER (PARTITION BY file_id ORDER BY timestamp DESC) as rn
                         FROM versions
                     ) WHERE rn > ?1
                 )",
                params![max_versions_per_file],
            )?;
        }

        tx.commit()?;
        Ok(deleted_count)
    }

    pub fn get_storage_stats(&self) -> Result<StorageStats> {
        let conn = self.get_connection()?;
        let mut stmt = conn.prepare(
            "SELECT 
                COUNT(v.id) as total_versions,
                COUNT(DISTINCT v.file_id) as total_files,
                COALESCE(SUM(v.file_size), 0) as total_orig,
                COALESCE(SUM(v.compressed_size), 0) as total_comp
             FROM versions v",
        )?;

        let mut rows = stmt.query([])?;
        if let Some(row) = rows.next()? {
            let total_versions: i64 = row.get(0)?;
            let total_files: i64 = row.get(1)?;
            let total_orig: i64 = row.get(2)?;
            let total_comp: i64 = row.get(3)?;
            let saved_ratio = if total_orig > 0 {
                (1.0 - (total_comp as f64 / total_orig as f64)) * 100.0
            } else {
                0.0
            };

            Ok(StorageStats {
                total_versions,
                total_files,
                total_original_bytes: total_orig,
                total_compressed_bytes: total_comp,
                saved_ratio,
            })
        } else {
            Ok(StorageStats {
                total_versions: 0,
                total_files: 0,
                total_original_bytes: 0,
                total_compressed_bytes: 0,
                saved_ratio: 0.0,
            })
        }
    }
}
