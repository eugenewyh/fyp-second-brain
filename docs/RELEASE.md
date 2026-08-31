# Release & download (GitHub Releases)

End users and FYP evaluators download Nous from **GitHub Releases** (repo collaborators only while the repo is private):

**https://github.com/eugenewyh/fyp-second-brain/releases**

## For evaluators (install)

1. Open the [latest release](https://github.com/eugenewyh/fyp-second-brain/releases/latest).
2. Download the installer for your platform:
   - **macOS (Apple Silicon):** `Nous_*_aarch64.dmg`
   - **Windows:** `Nous_*_x64-setup.exe` (if published)
3. **macOS (unsigned build):** If macOS blocks the app, right-click the app → **Open** → confirm once.
4. Launch **Nous**. Sign in if prompted. NVIDIA AI is included — no API key required.

User data is stored outside the app bundle:

- macOS: `~/Library/Application Support/com.tp068819.nous`
- Windows: `%APPDATA%\com.tp068819.nous`

## For maintainers (publish a release)

### 1. Build artifacts

macOS (on a Mac):

```bash
export NOUS_NVIDIA_API_KEY=nvapi-...
./scripts/package_release.sh
```

Windows (on Windows):

```powershell
$env:NOUS_NVIDIA_API_KEY = "nvapi-..."
.\scripts\package_release.ps1
```

Optional smoke test before packaging:

```bash
./scripts/build_sidecar_bundle.sh
./scripts/smoke_release.sh
```

Artifacts:

| Platform | Path |
|----------|------|
| macOS `.dmg` | `desktop/src-tauri/target/release/bundle/dmg/` |
| macOS `.app` | `desktop/src-tauri/target/release/bundle/macos/` |
| Windows NSIS | `desktop/src-tauri/target/release/bundle/nsis/` |

### 2. Publish to GitHub

Requires [GitHub CLI](https://cli.github.com/) (`gh auth login`).

```bash
# Default tag: v<version> from desktop/src-tauri/tauri.conf.json (e.g. v0.1.0)
./scripts/publish_github_release.sh

# Custom tag (e.g. FYP demo)
./scripts/publish_github_release.sh --tag v0.1.0-fyp

# Skip rebuild if artifacts already exist
./scripts/publish_github_release.sh --skip-build
```

Or manually:

```bash
git tag v0.1.0-fyp
git push github v0.1.0-fyp
gh release create v0.1.0-fyp \
  desktop/src-tauri/target/release/bundle/dmg/*.dmg \
  --title "Nous v0.1.0 (FYP demo)" \
  --notes-file .github/release_notes/TEMPLATE.md
```

## Scope notes

- While the repo is **private**, only collaborators can access Releases; add evaluators under **Settings → Collaborators**.
- Release builds embed an operator NVIDIA key for bundled AI; treat as demo-scale only.
- Code signing / notarization (macOS) and auto-update are out of scope for this FYP build.
