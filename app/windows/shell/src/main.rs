// Star Tracker for Windows (D72): starts the bundled backend (app/windows/backend: the shared UI server, discovery,
// BLE set-up and the reused Sony camera code) without a console window, shows the UI in a native window, and stops
// the backend on exit.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::{SocketAddr, TcpStream};
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

use tauri::{Manager, RunEvent, Url};

const PORT: u16 = 5570;
const HOME: &str = "http://127.0.0.1:5570/web/ui/index.html";
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

struct Backend(Mutex<Option<Child>>);

fn backend_up() -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], PORT));
    TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok()
}

fn main() {
    let app = tauri::Builder::default()
        .setup(|app| {
            // A backend left running (e.g. a second window) is reused.
            let mut child = None;
            if !backend_up() {
                let exe = app.path().resource_dir()?.join("backend").join("startracker-backend.exe");
                let mut cmd = Command::new(&exe);
                if let Some(dir) = exe.parent() {
                    cmd.current_dir(dir);
                }
                #[cfg(windows)]
                cmd.creation_flags(CREATE_NO_WINDOW);
                child = Some(cmd.spawn()?);
            }
            app.manage(Backend(Mutex::new(child)));

            let win = app.get_webview_window("main").expect("main window");
            thread::spawn(move || {
                for _ in 0..1200 {
                    if backend_up() {
                        let _ = win.navigate(Url::parse(HOME).expect("home url"));
                        return;
                    }
                    thread::sleep(Duration::from_millis(100));
                }
                let _ = win.eval(
                    "document.getElementById('msg').textContent = \
                     'The Star Tracker backend did not start. Close Star Tracker and open it again.'",
                );
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while starting Star Tracker");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(backend) = handle.try_state::<Backend>() {
                if let Some(mut child) = backend.0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        }
    });
}
