use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::channel;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use base64::{engine::general_purpose, Engine as _};

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

fn vault_documents_dir() -> PathBuf {
    project_root().join("data").join("documents")
}

fn path_under_vault(path: &Path) -> Result<PathBuf, String> {
    let vault = vault_documents_dir();
    let canonical_vault = vault
        .canonicalize()
        .map_err(|e| format!("Vault folder not found: {e}"))?;
    let resolved = if path.is_absolute() {
        path.to_path_buf()
    } else {
        vault.join(path)
    };
    let canonical = resolved
        .canonicalize()
        .map_err(|e| format!("Cannot read file: {e}"))?;
    if !canonical.starts_with(&canonical_vault) {
        return Err("Path is outside the documents vault".to_string());
    }
    if !is_supported_vault_file(&canonical) {
        return Err("Unsupported file type".to_string());
    }
    Ok(canonical)
}

fn find_file_by_basename(dir: &Path, basename: &std::ffi::OsStr) -> Option<PathBuf> {
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() {
                if let Some(found) = find_file_by_basename(&p, basename) {
                    return Some(found);
                }
            } else if entry.file_name() == basename {
                return Some(p);
            }
        }
    }
    None
}

fn find_file_by_basename_ci(dir: &Path, basename: &std::ffi::OsStr) -> Option<PathBuf> {
    let want = basename.to_string_lossy().to_lowercase();
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() {
                if let Some(found) = find_file_by_basename_ci(&p, basename) {
                    return Some(found);
                }
            } else if entry.file_name().to_string_lossy().to_lowercase() == want {
                return Some(p);
            }
        }
    }
    None
}

#[tauri::command]
fn read_vault_file_bytes(path: String) -> Result<Vec<u8>, String> {
    let file_path = PathBuf::from(&path);

    // 0. If the exact path exists on disk (absolute or relative), just read it.
    //    This is the most important fix for "recent" items and sources that store
    //    paths that are still valid on the user's machine.
    if file_path.exists() {
        match std::fs::read(&file_path) {
            Ok(data) if !data.is_empty() => return Ok(data),
            Ok(_) => return Err(format!("File is empty: {}", file_path.display())),
            Err(e) => return Err(format!("Failed to read {}: {}", file_path.display(), e)),
        }
    }

    // 1. Try the normal vault-restricted resolution (for paths relative to the vault root)
    if let Ok(canonical) = path_under_vault(&file_path) {
        if let Ok(data) = std::fs::read(&canonical) {
            if !data.is_empty() {
                return Ok(data);
            }
        }
    }

    // 2. Search the whole documents tree by basename (handles bare "Lec03.pdf")
    let basename = file_path.file_name();
    if let Some(basename) = basename {
        let vault = vault_documents_dir();
        if let Some(found) = find_file_by_basename(&vault, basename) {
            match std::fs::read(&found) {
                Ok(data) if !data.is_empty() => return Ok(data),
                Ok(_) => return Err(format!("Found {} but it is empty", found.display())),
                Err(e) => return Err(format!("Found {} but read failed: {}", found.display(), e)),
            }
        }
        if let Some(found) = find_file_by_basename_ci(&vault, basename) {
            match std::fs::read(&found) {
                Ok(data) if !data.is_empty() => return Ok(data),
                Ok(_) => return Err(format!("Found {} (ci) but it is empty", found.display())),
                Err(e) => return Err(format!("Found {} (ci) but read failed: {}", found.display(), e)),
            }
        }
    }

    Err(format!("PDF not found in vault or on disk. Tried: {}", path))
}

#[tauri::command]
fn read_vault_file_base64(path: String) -> Result<String, String> {
    let bytes = read_vault_file_bytes(path)?;
    Ok(general_purpose::STANDARD.encode(bytes))
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
            let kind = match &event.kind {
                EventKind::Create(_) => "create",
                EventKind::Modify(_) => "modify",
                EventKind::Remove(_) => "remove",
                EventKind::Any => "other",
                // Ignore access/other noise so UI isn't thrashed by reads
                _ => continue,
            };
            for path in event.paths {
                // Emit for any path (files + folders) so project tree stays live
                let _ = app_handle.emit(
                    "vault-file-changed",
                    serde_json::json!({
                        "path": path.to_string_lossy().to_string(),
                        "kind": kind,
                    }),
                );
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

/// Ensure `path` resolves under the documents vault (path may not exist yet).
fn resolve_dest_under_vault(path: &Path) -> Result<PathBuf, String> {
    let vault = vault_documents_dir();
    if !vault.exists() {
        std::fs::create_dir_all(&vault).map_err(|e| format!("Cannot create vault: {e}"))?;
    }
    let canonical_vault = vault
        .canonicalize()
        .map_err(|e| format!("Vault folder not found: {e}"))?;

    let abs = if path.is_absolute() {
        path.to_path_buf()
    } else {
        vault.join(path)
    };

    // Walk up to an existing ancestor and join remaining components for a normalized path
    let mut ancestor = abs.clone();
    let mut suffix: Vec<PathBuf> = Vec::new();
    while !ancestor.exists() {
        match ancestor.file_name() {
            Some(name) => {
                suffix.push(PathBuf::from(name));
                ancestor = ancestor
                    .parent()
                    .ok_or_else(|| "Invalid destination path".to_string())?
                    .to_path_buf();
            }
            None => break,
        }
    }
    let mut resolved = if ancestor.exists() {
        ancestor
            .canonicalize()
            .map_err(|e| format!("Cannot resolve destination: {e}"))?
    } else {
        return Err("Destination is outside the documents vault".to_string());
    };
    for part in suffix.into_iter().rev() {
        resolved = resolved.join(part);
    }

    if !resolved.starts_with(&canonical_vault) {
        return Err("Destination is outside the documents vault".to_string());
    }
    Ok(resolved)
}

fn copy_dir_recursive(src: &Path, dest: &Path) -> Result<(), String> {
    if !src.is_dir() {
        return Err(format!("Source is not a directory: {}", src.display()));
    }
    std::fs::create_dir_all(dest).map_err(|e| format!("Cannot create {}: {e}", dest.display()))?;
    for entry in std::fs::read_dir(src).map_err(|e| format!("Cannot read {}: {e}", src.display()))?
    {
        let entry = entry.map_err(|e| e.to_string())?;
        let from = entry.path();
        let to = dest.join(entry.file_name());
        let ft = entry
            .file_type()
            .map_err(|e| format!("Cannot read entry type: {e}"))?;
        if ft.is_dir() {
            copy_dir_recursive(&from, &to)?;
        } else if ft.is_file() {
            if let Some(parent) = to.parent() {
                std::fs::create_dir_all(parent)
                    .map_err(|e| format!("Cannot create {}: {e}", parent.display()))?;
            }
            std::fs::copy(&from, &to)
                .map_err(|e| format!("Cannot copy {} → {}: {e}", from.display(), to.display()))?;
        }
        // skip symlinks / other
    }
    Ok(())
}

/// Copy an existing local directory into the vault (e.g. project subfolder).
/// Does not move or modify the source. Dest must stay under `data/documents`.
#[tauri::command]
fn copy_dir_into_vault(source: String, dest: String) -> Result<String, String> {
    let src = PathBuf::from(&source);
    if !src.exists() {
        return Err(format!("Source folder not found: {source}"));
    }
    if !src.is_dir() {
        return Err(format!("Source is not a folder: {source}"));
    }
    let dest_path = resolve_dest_under_vault(Path::new(&dest))?;
    if dest_path.exists() {
        return Err(format!(
            "Destination already exists: {}",
            dest_path.display()
        ));
    }
    // Ensure parent exists and is under vault
    if let Some(parent) = dest_path.parent() {
        if !parent.exists() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Cannot create parent folder: {e}"))?;
        }
        let _ = resolve_dest_under_vault(parent)?;
    }
    copy_dir_recursive(&src, &dest_path)?;
    Ok(dest_path.to_string_lossy().to_string())
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
            read_vault_file_bytes,
            read_vault_file_base64,
            restart_sidecar,
            start_vault_watch,
            stop_vault_watch,
            copy_dir_into_vault
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