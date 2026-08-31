# Windows release build (run on Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $env:NOUS_NVIDIA_API_KEY) {
    throw "NOUS_NVIDIA_API_KEY must be set for release builds."
}

& "$Root\scripts\build_sidecar_bundle.ps1"

Push-Location "$Root\desktop"
npm run tauri build
Pop-Location

Write-Host "Build complete. Check desktop\src-tauri\target\release\bundle\"
