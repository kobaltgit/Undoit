#[cfg(target_os = "windows")]
use std::fs;
#[cfg(target_os = "windows")]
use std::path::PathBuf;
#[cfg(target_os = "windows")]
use winreg::enums::*;
#[cfg(target_os = "windows")]
use winreg::RegKey;

#[cfg(target_os = "windows")]
const UNDOIT_ICO_BYTES: &[u8] = include_bytes!("../icons/icon.ico");

#[cfg(target_os = "windows")]
fn ensure_app_icon_file() -> Result<PathBuf, String> {
    let base_dir = std::env::var("APPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."));
    let undoit_dir = base_dir.join("Undoit");
    let _ = fs::create_dir_all(&undoit_dir);
    let ico_path = undoit_dir.join("undoit.ico");

    let write_needed = match fs::metadata(&ico_path) {
        Ok(m) => m.len() != UNDOIT_ICO_BYTES.len() as u64,
        Err(_) => true,
    };

    if write_needed {
        fs::write(&ico_path, UNDOIT_ICO_BYTES).map_err(|e| e.to_string())?;
    }

    Ok(ico_path)
}

#[cfg(target_os = "windows")]
fn notify_shell_change() {
    #[link(name = "shell32")]
    extern "system" {
        fn SHChangeNotify(w_event_id: i32, u_flags: u32, dw_item1: *const std::ffi::c_void, dw_item2: *const std::ffi::c_void);
    }
    const SHCNE_ASSOCCHANGED: i32 = 0x08000000;
    const SHCNF_IDLIST: u32 = 0x0000;
    unsafe {
        SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, std::ptr::null(), std::ptr::null());
    }
}

pub fn is_context_menu_enabled() -> bool {
    #[cfg(target_os = "windows")]
    {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        hkcu.open_subkey(r"Software\Classes\*\shell\Undoit").is_ok()
    }
    #[cfg(not(target_os = "windows"))]
    {
        false
    }
}

pub fn set_context_menu_enabled(enabled: bool) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let exe_path = std::env::current_exe().map_err(|e| e.to_string())?;
        let exe_str = exe_path.to_string_lossy().to_string();
        let ico_path = ensure_app_icon_file()?;
        let ico_str = ico_path.to_string_lossy().to_string();

        let targets = [
            r"Software\Classes\*\shell\Undoit",
            r"Software\Classes\Directory\shell\Undoit",
            r"Software\Classes\Directory\Background\shell\Undoit",
        ];

        if enabled {
            for target in &targets {
                let (key, _) = hkcu.create_subkey(target).map_err(|e| e.to_string())?;
                key.set_value("", &"История версий Undoit")
                    .map_err(|e| e.to_string())?;
                let _ = key.set_value("Icon", &format!("\"{}\"", ico_str));

                let (cmd_key, _) = key.create_subkey("command").map_err(|e| e.to_string())?;
                let cmd_val = if target.contains("Background") {
                    format!("\"{}\" \"%V\"", exe_str)
                } else {
                    format!("\"{}\" \"%1\"", exe_str)
                };
                cmd_key.set_value("", &cmd_val).map_err(|e| e.to_string())?;
            }
        } else {
            for target in &targets {
                let _ = hkcu.delete_subkey_all(target);
            }
        }

        notify_shell_change();
        Ok(())
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = enabled;
        Ok(())
    }
}
