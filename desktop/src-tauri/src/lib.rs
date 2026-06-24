use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use serde::Serialize;
use tauri::{Manager, RunEvent, State};

struct SidecarState(Mutex<Option<Child>>);

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

#[derive(Serialize)]
struct VaultNode {
    name: String,
    path: String,
    #[serde(rename = "type")]
    entry_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    children: Option<Vec<VaultNode>>,
}

fn read_dir_entries(dir: &Path, max_depth: u8) -> Vec<VaultNode> {
    let mut entries: Vec<VaultNode> = Vec::new();
    let Ok(read_dir) = fs::read_dir(dir) else {
        return entries;
    };

    let mut items: Vec<_> = read_dir.filter_map(Result::ok).collect();
    items.sort_by_key(|e| e.file_name());

    for entry in items {
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with('.') {
            continue;
        }
        let is_dir = path.is_dir();
        let children = if is_dir && max_depth > 0 {
            let nested = read_dir_entries(&path, max_depth - 1);
            if nested.is_empty() {
                None
            } else {
                Some(nested)
            }
        } else {
            None
        };
        entries.push(VaultNode {
            name,
            path: path.to_string_lossy().to_string(),
            entry_type: if is_dir { "folder".into() } else { "file".into() },
            children,
        });
    }
    entries
}

#[tauri::command]
fn list_vault_tree() -> Result<Vec<VaultNode>, String> {
    let vault_dir = project_root().join("data").join("documents");
    if !vault_dir.exists() {
        fs::create_dir_all(&vault_dir).map_err(|e| format!("Failed to create vault dir: {e}"))?;
    }
    Ok(vec![VaultNode {
        name: "data/documents/".into(),
        path: vault_dir.to_string_lossy().to_string(),
        entry_type: "folder".into(),
        children: {
            let kids = read_dir_entries(&vault_dir, 4);
            if kids.is_empty() {
                None
            } else {
                Some(kids)
            }
        },
    }])
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

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(sidecar_state)
        .invoke_handler(tauri::generate_handler![
            get_sidecar_url,
            get_project_root,
            list_vault_tree,
            restart_sidecar
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
            }
        });
}