fn main() {
    tauri_build::build();

    // After every macOS debug build, refresh .app bundles so icon + binary stay aligned.
    #[cfg(all(target_os = "macos", debug_assertions))]
    {
        let manifest_dir = std::path::PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
        let sync = manifest_dir.join("../scripts/sync_macos_app_bundle.sh");
        if sync.exists() {
            let _ = std::process::Command::new("bash").arg(sync).status();
        }
    }
}
