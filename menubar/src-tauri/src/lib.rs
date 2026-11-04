mod db;
mod detect;

use std::sync::Mutex;
use std::time::Duration;

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, State, WebviewWindow, WindowEvent,
};

use db::{HomeSummary, Memory, MemoryDetail, Store, Topic};
use detect::{app_name, detect_all, known_app, AppStatus};

struct DbState(Mutex<Store>);

fn store_mut<'a>(state: &'a State<'a, DbState>) -> Result<std::sync::MutexGuard<'a, Store>, String> {
    state.0.lock().map_err(|_| "Database is busy".to_string())
}

#[tauri::command]
fn list_apps(state: State<DbState>) -> Result<Vec<AppStatus>, String> {
    let store = store_mut(&state)?;
    let connected = store.connected_ids()?;
    Ok(detect_all(&connected))
}

#[tauri::command]
fn set_connected(state: State<DbState>, app_id: String, connected: bool) -> Result<(), String> {
    if !known_app(&app_id) {
        return Err("Unknown app".into());
    }
    if connected {
        let status = detect_all(&[]).into_iter().find(|app| app.id == app_id);
        if !status.map(|app| app.installed).unwrap_or(false) {
            return Err("That app is not installed".into());
        }
    }
    store_mut(&state)?.set_connected(&app_id, connected)
}

#[tauri::command]
fn home_summary(state: State<DbState>) -> Result<HomeSummary, String> {
    let store = store_mut(&state)?;
    let names = store
        .connected_ids()?
        .into_iter()
        .filter_map(|id| app_name(&id).map(|name| name.to_string()))
        .collect::<Vec<_>>();
    store.home_summary(&names)
}

#[tauri::command]
fn list_topics(state: State<DbState>, query: Option<String>) -> Result<Vec<Topic>, String> {
    store_mut(&state)?.list_topics(query.as_deref().unwrap_or(""))
}

#[tauri::command]
fn create_topic(state: State<DbState>, title: String) -> Result<Topic, String> {
    store_mut(&state)?.create_topic(&title)
}

#[tauri::command]
fn list_memories(
    state: State<DbState>,
    query: Option<String>,
    topic_id: Option<String>,
    about_you: Option<bool>,
    app_id: Option<String>,
    limit: Option<i64>,
) -> Result<Vec<Memory>, String> {
    let limit = limit.unwrap_or(50).clamp(1, 200);
    store_mut(&state)?.list_memories(
        query.as_deref().unwrap_or(""),
        topic_id.as_deref(),
        about_you.unwrap_or(false),
        app_id.as_deref(),
        limit,
    )
}

#[tauri::command]
fn create_memory(
    state: State<DbState>,
    body: String,
    topic_id: Option<String>,
    app_id: Option<String>,
) -> Result<Memory, String> {
    if let Some(app_id) = &app_id {
        if !known_app(app_id) {
            return Err("Unknown app".into());
        }
    }
    store_mut(&state)?.create_memory(&body, topic_id.as_deref(), app_id.as_deref())
}

#[tauri::command]
fn get_memory(state: State<DbState>, id: String) -> Result<MemoryDetail, String> {
    store_mut(&state)?.get_memory(&id)
}

#[tauri::command]
fn link_memories(state: State<DbState>, from_id: String, to_id: String) -> Result<(), String> {
    store_mut(&state)?.link_memories(&from_id, &to_id)
}

fn show_browse(app: &AppHandle, path: Option<&str>) -> Result<(), String> {
    if let Some(panel) = app.get_webview_window("panel") {
        let _ = panel.hide();
    }
    let window = app
        .get_webview_window("browse")
        .ok_or("Browse window is missing")?;
    window.show().map_err(|e| e.to_string())?;
    let _ = window.unminimize();
    window.set_focus().map_err(|e| e.to_string())?;
    if let Some(path) = path {
        window.emit("navigate", path).map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn open_browse(app: AppHandle, path: String) -> Result<(), String> {
    show_browse(&app, Some(path.as_str()))
}

fn toggle_panel(window: &WebviewWindow) {
    let visible = window.is_visible().unwrap_or(false);
    if visible {
        let _ = window.hide();
        return;
    }
    if let Ok(Some(monitor)) = window.current_monitor() {
        let screen = monitor.size();
        let scale = monitor.scale_factor();
        let win = window
            .outer_size()
            .unwrap_or(tauri::PhysicalSize::new(380, 560));
        let margin = (12.0 * scale) as i32;
        let menu_bar = (24.0 * scale) as i32;
        let x = screen.width as i32 - win.width as i32 - margin;
        let y = menu_bar;
        let _ = window.set_position(tauri::PhysicalPosition::new(x.max(0), y.max(0)));
    }
    let _ = window.show();
    let _ = window.set_focus();
}

fn hide_panel_when_blurred(window: WebviewWindow) {
    window.clone().on_window_event(move |event| {
        if let WindowEvent::Focused(false) = event {
            let panel = window.clone();
            std::thread::spawn(move || {
                std::thread::sleep(Duration::from_millis(180));
                if !panel.is_focused().unwrap_or(false) {
                    let _ = panel.hide();
                }
            });
        }
    });
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
            let store = Store::open(&dir.join("memory.db"))?;
            app.manage(DbState(Mutex::new(store)));

            let open = MenuItem::with_id(app, "open", "Open Memory", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &quit])?;
            let icon = app
                .default_window_icon()
                .cloned()
                .ok_or("Menu bar icon is missing")?;
            let mut tray = TrayIconBuilder::with_id("memory")
                .icon(icon)
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        if let Some(window) = tray.app_handle().get_webview_window("panel") {
                            toggle_panel(&window);
                        }
                    }
                })
                .on_menu_event(|app, event| {
                    if event.id() == "open" {
                        let _ = show_browse(app, None);
                    } else if event.id() == "quit" {
                        app.exit(0);
                    }
                });
            tray = tray.tooltip("Memory");
            tray.build(app)?;

            if let Some(panel) = app.get_webview_window("panel") {
                hide_panel_when_blurred(panel);
            }
            if let Some(browse) = app.get_webview_window("browse") {
                let app_handle = app.handle().clone();
                browse.on_window_event(move |event| {
                    if let WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        if let Some(window) = app_handle.get_webview_window("browse") {
                            let _ = window.hide();
                        }
                    }
                });
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            list_apps,
            set_connected,
            home_summary,
            list_topics,
            create_topic,
            list_memories,
            create_memory,
            get_memory,
            link_memories,
            open_browse
        ])
        .build(tauri::generate_context!())
        .expect("error while running memory")
        .run(|app, event| {
            if let tauri::RunEvent::Reopen { .. } = event {
                let _ = show_browse(app, None);
            }
        });
}
