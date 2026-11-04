use std::path::{Path, PathBuf};

#[derive(Debug, Clone, serde::Serialize)]
pub struct AppStatus {
    pub id: String,
    pub name: String,
    pub installed: bool,
    pub connected: bool,
}

struct AppDef {
    id: &'static str,
    name: &'static str,
    bundles: &'static [&'static str],
    bins: &'static [&'static str],
}

const APPS: &[AppDef] = &[
    AppDef {
        id: "cursor",
        name: "Cursor",
        bundles: &["Cursor.app"],
        bins: &[],
    },
    AppDef {
        id: "claude",
        name: "Claude",
        bundles: &["Claude.app"],
        bins: &["claude"],
    },
    AppDef {
        id: "chatgpt",
        name: "ChatGPT",
        bundles: &["ChatGPT.app"],
        bins: &[],
    },
    AppDef {
        id: "grok",
        name: "Grok",
        bundles: &["Grok.app"],
        bins: &["grok"],
    },
    AppDef {
        id: "muse",
        name: "Muse",
        bundles: &["Muse.app"],
        bins: &["muse"],
    },
];

pub fn known_app(id: &str) -> bool {
    APPS.iter().any(|app| app.id == id)
}

pub fn app_name(id: &str) -> Option<&'static str> {
    APPS.iter().find(|app| app.id == id).map(|app| app.name)
}

pub fn detect_all(connected: &[String]) -> Vec<AppStatus> {
    let home = std::env::var_os("HOME").map(PathBuf::from);
    let path_env = std::env::var("PATH").unwrap_or_default();
    APPS
        .iter()
        .map(|app| AppStatus {
            id: app.id.to_string(),
            name: app.name.to_string(),
            installed: app_installed(app, home.as_deref(), &path_env),
            connected: connected.iter().any(|id| id == app.id),
        })
        .collect()
}

fn app_installed(app: &AppDef, home: Option<&Path>, path_env: &str) -> bool {
    app.bundles.iter().any(|bundle| bundle_exists(bundle, home))
        || app.bins.iter().any(|bin| binary_on_path(bin, home, path_env))
}

fn bundle_exists(bundle: &str, home: Option<&Path>) -> bool {
    let mut roots = vec![
        PathBuf::from("/Applications"),
        PathBuf::from("/System/Applications"),
    ];
    if let Some(home) = home {
        roots.push(home.join("Applications"));
    }
    roots.into_iter().any(|root| root.join(bundle).is_dir())
}

fn binary_on_path(bin: &str, home: Option<&Path>, path_env: &str) -> bool {
    let mut dirs: Vec<PathBuf> = path_env
        .split(':')
        .filter(|part| !part.is_empty())
        .map(PathBuf::from)
        .collect();
    dirs.push(PathBuf::from("/opt/homebrew/bin"));
    dirs.push(PathBuf::from("/usr/local/bin"));
    if let Some(home) = home {
        dirs.push(home.join(".local/bin"));
    }
    dirs.into_iter().any(|dir| dir.join(bin).is_file())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn catalog_has_the_five_apps() {
        let apps = detect_all(&[]);
        let ids: Vec<_> = apps.iter().map(|app| app.id.as_str()).collect();
        assert_eq!(ids, ["cursor", "claude", "chatgpt", "grok", "muse"]);
    }

    #[test]
    fn unknown_app_is_rejected() {
        assert!(!known_app("notion"));
        assert!(known_app("cursor"));
    }
}
