use std::fs;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager};

#[cfg(target_os = "windows")]
pub struct NamedMutex {
    handle: *mut std::ffi::c_void,
}

#[cfg(target_os = "windows")]
unsafe impl Send for NamedMutex {}
#[cfg(target_os = "windows")]
unsafe impl Sync for NamedMutex {}

#[cfg(target_os = "windows")]
impl NamedMutex {
    pub fn try_acquire(name: &str) -> Option<Self> {
        let wide: Vec<u16> = name.encode_utf16().chain(std::iter::once(0)).collect();
        unsafe {
            #[link(name = "kernel32")]
            extern "system" {
                fn CreateMutexW(
                    lp_attrs: *mut std::ffi::c_void,
                    b_initial: i32,
                    lp_name: *const u16,
                ) -> *mut std::ffi::c_void;
                fn GetLastError() -> u32;
                fn CloseHandle(h: *mut std::ffi::c_void) -> i32;
            }
            const ERROR_ALREADY_EXISTS: u32 = 183;

            let handle = CreateMutexW(std::ptr::null_mut(), 1, wide.as_ptr());
            if handle.is_null() || GetLastError() == ERROR_ALREADY_EXISTS {
                if !handle.is_null() {
                    CloseHandle(handle);
                }
                None
            } else {
                Some(Self { handle })
            }
        }
    }
}

#[cfg(target_os = "windows")]
impl Drop for NamedMutex {
    fn drop(&mut self) {
        if !self.handle.is_null() {
            unsafe {
                #[link(name = "kernel32")]
                extern "system" {
                    fn CloseHandle(h: *mut std::ffi::c_void) -> i32;
                }
                CloseHandle(self.handle);
            }
        }
    }
}

fn get_ipc_port_file() -> PathBuf {
    let base = std::env::var("APPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."));
    let dir = base.join("Undoit");
    let _ = fs::create_dir_all(&dir);
    dir.join("ipc.port")
}

/// Checks if an instance of Undoit is already running.
/// If running, forwards command line arguments to it, brings it to the front, and returns `true`.
/// If not running, returns `false` and caller should continue app initialization.
pub fn handle_potential_secondary_instance() -> bool {
    let port_file = get_ipc_port_file();
    if let Ok(content) = fs::read_to_string(&port_file) {
        if let Ok(port) = content.trim().parse::<u16>() {
            let addr_str = format!("127.0.0.1:{}", port);
            if let Ok(addr) = addr_str.parse() {
                if let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(400)) {
                    // Connected to primary instance! Forward arguments.
                    let args: Vec<String> = std::env::args().skip(1).collect();
                    let payload = serde_json::to_string(&args).unwrap_or_else(|_| "[]".to_string());
                    let _ = stream.write_all(format!("{}\n", payload).as_bytes());
                    let _ = stream.flush();

                    // Wait briefly for acknowledgment
                    let mut buf = [0u8; 16];
                    let _ = stream.read(&mut buf);

                    #[cfg(target_os = "windows")]
                    focus_existing_window();

                    return true; // Is secondary, handled and should exit
                }
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        // Try acquiring the named mutex
        if NamedMutex::try_acquire("Local\\Undoit_SingleInstance_Mutex_Kobalt").is_none() {
            // Mutex exists
            focus_existing_window();
            return true;
        }
    }

    false
}

#[cfg(target_os = "windows")]
fn focus_existing_window() {
    unsafe {
        #[link(name = "user32")]
        extern "system" {
            fn FindWindowW(lp_class_name: *const u16, lp_window_name: *const u16) -> *mut std::ffi::c_void;
            fn SetForegroundWindow(h_wnd: *mut std::ffi::c_void) -> i32;
            fn ShowWindow(h_wnd: *mut std::ffi::c_void, n_cmd_show: i32) -> i32;
        }
        const SW_RESTORE: i32 = 9;

        let wide_title: Vec<u16> = "Undoit - Time Machine"
            .encode_utf16()
            .chain(std::iter::once(0))
            .collect();
        let hwnd = FindWindowW(std::ptr::null(), wide_title.as_ptr());
        if !hwnd.is_null() {
            ShowWindow(hwnd, SW_RESTORE);
            SetForegroundWindow(hwnd);
        }
    }
}

/// Starts the IPC server on the primary instance to listen for future secondary instance launches.
pub fn start_primary_ipc_listener(app_handle: AppHandle) {
    std::thread::spawn(move || {
        let listener = match TcpListener::bind("127.0.0.1:0") {
            Ok(l) => l,
            Err(e) => {
                eprintln!("Failed to bind single-instance IPC listener: {}", e);
                return;
            }
        };

        if let Ok(addr) = listener.local_addr() {
            let port_file = get_ipc_port_file();
            let _ = fs::write(&port_file, addr.port().to_string());
        }

        for stream in listener.incoming() {
            match stream {
                Ok(mut socket) => {
                    use std::io::BufRead;
                    let mut reader = std::io::BufReader::new(&mut socket);
                    let mut line = String::new();
                    if reader.read_line(&mut line).is_ok() {
                        let args: Vec<String> = serde_json::from_str(line.trim()).unwrap_or_default();

                        // Show and focus existing window
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.unminimize();
                            let _ = window.set_focus();

                            // If a file was passed as argument (e.g. from Explorer context menu)
                            if !args.is_empty() {
                                let target_file = args[0].clone();
                                let _ = window.emit("open-file-path", target_file);
                            }
                        }
                    }
                    let _ = socket.write_all(b"OK\n");
                    let _ = socket.flush();
                }
                Err(_) => {}
            }
        }
    });
}
