use std::collections::HashSet;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use blake3::Hasher;
use serde::{Deserialize, Serialize};
use similar::{ChangeTag, TextDiff};
use walkdir::WalkDir;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DiffLine {
    pub tag: String, // "insert", "delete", "equal"
    pub old_line_num: Option<usize>,
    pub new_line_num: Option<usize>,
    pub text: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DiffResult {
    pub lines: Vec<DiffLine>,
    pub additions: usize,
    pub deletions: usize,
    pub is_binary: bool,
}

pub fn is_image_extension(ext: &str) -> bool {
    matches!(
        ext.to_lowercase().as_str(),
        "jpg" | "jpeg" | "png" | "webp" | "gif" | "svg" | "bmp" | "ico" | "avif" | "tiff" | "tif"
    )
}

#[allow(dead_code)]
pub fn is_image_path(path: &str) -> bool {
    let ext = Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("");
    is_image_extension(ext)
}

pub fn is_visual_document_extension(ext: &str) -> bool {
    let lower = ext.to_lowercase();
    is_image_extension(&lower) || matches!(lower.as_str(), "pdf" | "ai" | "psd")
}

pub fn is_visual_document_path(path: &str) -> bool {
    let ext = Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("");
    is_visual_document_extension(ext)
}

pub fn is_docx_extension(ext: &str) -> bool {
    ext.eq_ignore_ascii_case("docx")
}

pub fn is_docx_path(path: &str) -> bool {
    let ext = Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("");
    is_docx_extension(ext)
}

pub fn extract_docx_text(bytes: &[u8]) -> Option<String> {
    if !bytes.starts_with(b"PK\x03\x04") {
        return None;
    }
    let reader = std::io::Cursor::new(bytes);
    let mut archive = zip::ZipArchive::new(reader).ok()?;
    let mut doc_file = archive.by_name("word/document.xml").ok()?;
    let mut xml = String::new();
    doc_file.read_to_string(&mut xml).ok()?;

    let mut result = String::with_capacity(xml.len() / 2);
    let mut current_tag = String::new();
    let mut in_text = false;

    let chars: Vec<char> = xml.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        let ch = chars[i];
        if ch == '<' {
            current_tag.clear();
            i += 1;
            while i < chars.len() && chars[i] != '>' {
                current_tag.push(chars[i]);
                i += 1;
            }
            let tag_trimmed = current_tag.trim();
            if tag_trimmed == "/w:p" {
                result.push('\n');
            } else if tag_trimmed == "w:br" || tag_trimmed == "w:br/" || tag_trimmed == "w:cr" || tag_trimmed == "w:cr/" {
                result.push('\n');
            } else if tag_trimmed == "w:tab" || tag_trimmed == "w:tab/" {
                result.push('\t');
            } else if tag_trimmed == "w:t" || tag_trimmed.starts_with("w:t ") {
                in_text = true;
            } else if tag_trimmed == "/w:t" {
                in_text = false;
            }
        } else {
            if in_text {
                result.push(ch);
            }
        }
        i += 1;
    }

    let decoded = result
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
        .replace("&apos;", "'");

    let trimmed = decoded.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

pub fn guess_mime(ext: &str) -> &'static str {
    match ext.to_lowercase().as_str() {
        "jpg" | "jpeg" => "image/jpeg",
        "png" => "image/png",
        "webp" => "image/webp",
        "gif" => "image/gif",
        "svg" => "image/svg+xml",
        "bmp" => "image/bmp",
        "ico" => "image/x-icon",
        "avif" => "image/avif",
        "tiff" | "tif" => "image/tiff",
        "pdf" => "application/pdf",
        "ai" => "application/pdf",
        _ => "application/octet-stream",
    }
}

pub fn is_binary_buffer(data: &[u8]) -> bool {
    let check_len = data.len().min(8192);
    data[..check_len].iter().any(|&b| b == 0)
}

pub fn to_base64(data: &[u8]) -> String {
    const CHARSET: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::with_capacity((data.len() + 2) / 3 * 4);
    for chunk in data.chunks(3) {
        let b0 = chunk[0];
        let b1 = if chunk.len() > 1 { chunk[1] } else { 0 };
        let b2 = if chunk.len() > 2 { chunk[2] } else { 0 };

        out.push(CHARSET[(b0 >> 2) as usize] as char);
        out.push(CHARSET[(((b0 & 3) << 4) | (b1 >> 4)) as usize] as char);
        if chunk.len() > 1 {
            out.push(CHARSET[(((b1 & 15) << 2) | (b2 >> 6)) as usize] as char);
        } else {
            out.push('=');
        }
        if chunk.len() > 2 {
            out.push(CHARSET[(b2 & 63) as usize] as char);
        } else {
            out.push('=');
        }
    }
    out
}

pub struct Storage {
    objects_dir: PathBuf,
}

impl Storage {
    pub fn new(app_data_dir: &Path) -> std::io::Result<Self> {
        let objects_dir = app_data_dir.join("objects");
        fs::create_dir_all(&objects_dir)?;
        Ok(Self { objects_dir })
    }

    pub fn get_object_path(&self, hash: &str) -> PathBuf {
        if hash.len() < 4 {
            return self.objects_dir.join(hash);
        }
        self.objects_dir.join(&hash[..2]).join(&hash[2..])
    }

    #[allow(dead_code)]
    pub fn hash_file(&self, path: &Path) -> std::io::Result<(String, u64)> {
        let mut file = File::open(path)?;
        let mut hasher = Hasher::new();
        let mut buffer = [0u8; 65536];
        let mut total_bytes: u64 = 0;

        loop {
            let n = file.read(&mut buffer)?;
            if n == 0 {
                break;
            }
            hasher.update(&buffer[..n]);
            total_bytes += n as u64;
        }

        let hash = hasher.finalize().to_hex().to_string();
        Ok((hash, total_bytes))
    }

    pub fn save_file(&self, path: &Path) -> std::io::Result<(String, u64, u64)> {
        let raw_data = fs::read(path)?;
        let raw_size = raw_data.len() as u64;

        let mut hasher = Hasher::new();
        hasher.update(&raw_data);
        let hash = hasher.finalize().to_hex().to_string();

        let obj_path = self.get_object_path(&hash);
        if obj_path.exists() {
            let compressed_size = fs::metadata(&obj_path)?.len();
            return Ok((hash, raw_size, compressed_size));
        }

        if let Some(parent) = obj_path.parent() {
            fs::create_dir_all(parent)?;
        }

        let compressed_data = zstd::encode_all(&raw_data[..], 3)?;
        let compressed_size = compressed_data.len() as u64;

        let temp_path = obj_path.with_extension("tmp");
        {
            let mut temp_file = File::create(&temp_path)?;
            temp_file.write_all(&compressed_data)?;
            temp_file.flush()?;
        }

        fs::rename(&temp_path, &obj_path)?;

        Ok((hash, raw_size, compressed_size))
    }

    pub fn read_version_bytes(&self, hash: &str) -> std::io::Result<Vec<u8>> {
        let obj_path = self.get_object_path(hash);
        if !obj_path.exists() {
            return Err(std::io::Error::new(
                std::io::ErrorKind::NotFound,
                format!("Object not found in storage: {}", hash),
            ));
        }

        let compressed_data = fs::read(obj_path)?;
        let decompressed = zstd::decode_all(&compressed_data[..])?;
        Ok(decompressed)
    }

    pub fn read_version_text(&self, hash: &str) -> std::io::Result<String> {
        let bytes = self.read_version_bytes(hash)?;
        if is_binary_buffer(&bytes) {
            return Ok("[Бинарный файл. Текстовый предпросмотр недоступен]".to_string());
        }
        match String::from_utf8(bytes.clone()) {
            Ok(text) => Ok(text),
            Err(_) => Ok(String::from_utf8_lossy(&bytes).to_string()),
        }
    }

    pub fn read_version_data_url(&self, hash: &str, ext: &str) -> std::io::Result<String> {
        let bytes = self.read_version_bytes(hash)?;
        let mime = guess_mime(ext);
        let b64 = to_base64(&bytes);
        Ok(format!("data:{};base64,{}", mime, b64))
    }

    pub fn compare_diff(&self, old_text: &str, new_text: &str) -> DiffResult {
        let diff = TextDiff::from_lines(old_text, new_text);
        let mut lines = Vec::new();
        let mut additions = 0;
        let mut deletions = 0;

        let mut old_num = 1;
        let mut new_num = 1;

        for change in diff.iter_all_changes() {
            let (tag_str, old_idx, new_idx) = match change.tag() {
                ChangeTag::Delete => {
                    deletions += 1;
                    let curr = old_num;
                    old_num += 1;
                    ("delete", Some(curr), None)
                }
                ChangeTag::Insert => {
                    additions += 1;
                    let curr = new_num;
                    new_num += 1;
                    ("insert", None, Some(curr))
                }
                ChangeTag::Equal => {
                    let old_curr = old_num;
                    let new_curr = new_num;
                    old_num += 1;
                    new_num += 1;
                    ("equal", Some(old_curr), Some(new_curr))
                }
            };

            lines.push(DiffLine {
                tag: tag_str.to_string(),
                old_line_num: old_idx,
                new_line_num: new_idx,
                text: change.value().trim_end_matches(['\r', '\n']).to_string(),
            });
        }

        DiffResult {
            lines,
            additions,
            deletions,
            is_binary: false,
        }
    }

    pub fn restore_file(&self, hash: &str, target_path: &Path) -> std::io::Result<()> {
        let content = self.read_version_bytes(hash)?;

        if let Some(parent) = target_path.parent() {
            fs::create_dir_all(parent)?;
        }

        // If target file exists and is read-only, clear read-only flag so it can be overwritten
        if target_path.exists() {
            if let Ok(metadata) = fs::metadata(target_path) {
                if metadata.permissions().readonly() {
                    let mut perms = metadata.permissions();
                    perms.set_readonly(false);
                    let _ = fs::set_permissions(target_path, perms);
                }
            }
        }

        let temp_target = target_path.with_extension("undoit_restore_tmp");
        {
            let mut f = File::create(&temp_target)?;
            f.write_all(&content)?;
            f.flush()?;
        }

        match fs::rename(&temp_target, target_path) {
            Ok(_) => Ok(()),
            Err(e) => {
                // Ensure temp file is cleaned up if rename fails (e.g. target locked by Word)
                let _ = fs::remove_file(&temp_target);
                Err(e)
            }
        }
    }

    pub fn prune_unreferenced_objects(&self, active_hashes: &HashSet<String>) -> std::io::Result<usize> {
        let mut deleted_count = 0;

        for entry in WalkDir::new(&self.objects_dir).into_iter().filter_map(|e| e.ok()) {
            if entry.file_type().is_file() {
                let path = entry.path();
                if let (Some(parent_name), Some(file_name)) = (
                    path.parent().and_then(|p| p.file_name()).and_then(|s| s.to_str()),
                    path.file_name().and_then(|s| s.to_str()),
                ) {
                    let full_hash = format!("{}{}", parent_name, file_name);
                    if !active_hashes.contains(&full_hash) {
                        if fs::remove_file(path).is_ok() {
                            deleted_count += 1;
                        }
                    }
                }
            }
        }

        Ok(deleted_count)
    }

    pub fn export_version_to_temp(&self, hash: &str, original_filename: &str) -> std::io::Result<PathBuf> {
        let temp_dir = std::env::temp_dir().join("undoit_preview");
        fs::create_dir_all(&temp_dir)?;

        let hash_prefix = if hash.len() >= 8 { &hash[..8] } else { hash };
        let sanitized_name = original_filename.replace(['/', '\\', ':', '*', '?', '"', '<', '>', '|'], "_");
        let temp_file = temp_dir.join(format!("{}_{}", hash_prefix, sanitized_name));

        if temp_file.exists() {
            // Already exported and immutable for this hash. Return immediately without re-writing.
            return Ok(temp_file);
        }

        let bytes = self.read_version_bytes(hash)?;
        fs::write(&temp_file, &bytes)?;

        // Safety: mark historical snapshot as read-only so editors don't silently save to %TEMP%
        if let Ok(metadata) = fs::metadata(&temp_file) {
            let mut perms = metadata.permissions();
            perms.set_readonly(true);
            let _ = fs::set_permissions(&temp_file, perms);
        }

        Ok(temp_file)
    }
}
