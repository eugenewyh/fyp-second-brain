use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::channel;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use notify::{EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use tauri::{AppHandle, Emitter, Manager, RunEvent, State};

struct SidecarState(Mutex<Option<Child>>);

struct WatchState {
    watcher: Mutex<Option<RecommendedWatcher>>,
    stop: Arc<Mutex<bool>>,
}

fn project_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("desktop dir")
        .parent()
        .expect("project root")
        .to_path_buf()
}

fn python_executable(root: &PathBuf) -> PathBuf {
    let venv_python = root.join(".venv/bin/python");
    if venv_python.exists() {
        return venv_python;
    }
    root.join(".venv/bin/python3")
}

fn start_sidecar_process(state: &SidecarState) -> Result<(), String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if guard.is_some() {
        return Ok(());
    }

    let root = project_root();
    let python = python_executable(&root);
    if !python.exists() {
        return Err(format!(
            "Python venv not found at {}. From project root run: python3.12 -m venv .venv && pip install -r requirements.txt",
            python.display()
        ));
    }

    let script = root.join("sidecar/server.py");
    if !script.exists() {
        return Err(format!("Sidecar script not found: {}", script.display()));
    }

    let child = Command::new(&python)
        .arg(&script)
        .current_dir(&root)
        .env("PYTHONPATH", root.join("src"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start sidecar: {e}"))?;

    *guard = Some(child);
    Ok(())
}

fn stop_sidecar_process(state: &SidecarState) {
    if let Ok(mut guard) = state.0.lock() {
        if let Some(mut child) = guard.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

#[tauri::command]
fn get_sidecar_url() -> String {
    std::env::var("SIDECAR_PORT")
        .map(|port| format!("http://127.0.0.1:{port}"))
        .unwrap_or_else(|_| "http://127.0.0.1:8765".to_string())
}

#[tauri::command]
fn get_project_root() -> String {
    project_root().to_string_lossy().to_string()
}

fn is_supported_vault_file(path: &Path) -> bool {
    path.extension()
        .and_then(|ext| ext.to_str())
        .map(|ext| {
            let lower = ext.to_lowercase();
            lower == "md" || lower == "txt" || lower == "pdf"
        })
        .unwrap_or(false)
}

#[tauri::command]
fn start_vault_watch(app: AppHandle, root: String, state: State<WatchState>) -> Result<(), String> {
    {
        let mut stop = state.stop.lock().map_err(|e| e.to_string())?;
        *stop = false;
    }

    let existing = state.watcher.lock().map_err(|e| e.to_string())?;
    if existing.is_some() {
        return Ok(());
    }
    drop(existing);

    let (tx, rx) = channel();
    let mut watcher = RecommendedWatcher::new(tx, notify::Config::default())
        .map_err(|e| e.to_string())?;
    watcher
        .watch(Path::new(&root), RecursiveMode::Recursive)
        .map_err(|e| e.to_string())?;

    {
        let mut guard = state.watcher.lock().map_err(|e| e.to_string())?;
        *guard = Some(watcher);
    }

    let stop_ref = Arc::clone(&state.stop);
    let app_handle = app.clone();

    thread::spawn(move || {
        for event in rx {
            if *stop_ref.lock().unwrap() {
                break;
            }
            let Ok(event) = event else { continue };
            let relevant = matches!(
                event.kind,
                EventKind::Create(_) | EventKind::Modify(_) | EventKind::Any
            );
            if !relevant {
                continue;
            }
            for path in event.paths {
                if is_supported_vault_file(&path) {
                    let _ = app_handle.emit(
                        "vault-file-changed",
                        serde_json::json!({ "path": path.to_string_lossy().to_string() }),
                    );
                }
            }
        }
    });

    Ok(())
}

#[tauri::command]
fn stop_vault_watch(state: State<WatchState>) -> Result<(), String> {
    if let Ok(mut stop) = state.stop.lock() {
        *stop = true;
    }
    if let Ok(mut guard) = state.watcher.lock() {
        *guard = None;
    }
    if let Ok(mut stop) = state.stop.lock() {
        *stop = false;
    }
    Ok(())
}

#[tauri::command]
fn restart_sidecar(state: State<SidecarState>) -> Result<String, String> {
    stop_sidecar_process(&state);
    std::thread::sleep(Duration::from_millis(300));
    start_sidecar_process(&state)?;
    Ok(get_sidecar_url())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let sidecar_state = SidecarState(Mutex::new(None));
    let watch_state = WatchState {
        watcher: Mutex::new(None),
        stop: Arc::new(Mutex::new(false)),
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_opener::init())
        .manage(sidecar_state)
        .manage(watch_state)
        .invoke_handler(tauri::generate_handler![
            get_sidecar_url,
            get_project_root,
            restart_sidecar,
            start_vault_watch,
            stop_vault_watch
        ])
        .setup(|app| {
            let state = app.state::<SidecarState>();
            if let Err(error) = start_sidecar_process(&state) {
                eprintln!("Sidecar startup warning: {error}");
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let RunEvent::Exit = event {
                let state = app_handle.state::<SidecarState>();
                stop_sidecar_process(&state);
                let watch = app_handle.state::<WatchState>();
                let _ = stop_vault_watch(watch);
            }
        });
}