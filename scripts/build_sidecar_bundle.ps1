# Build the Python sidecar bundle for Tauri release (Windows).
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Bundle = Join-Path $Root "desktop\src-tauri\sidecar-bundle"
$Req = Join-Path $Root "requirements.txt"
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

if (-not (Test-Path $Req)) {
    throw "Missing requirements.txt at $Req"
}

if (-not $env:NOUS_NVIDIA_API_KEY) {
    throw "NOUS_NVIDIA_API_KEY is required for release builds."
}

Write-Host "==> Cleaning sidecar bundle at $Bundle"
if (Test-Path $Bundle) { Remove-Item -Recurse -Force $Bundle }
New-Item -ItemType Directory -Path $Bundle | Out-Null

Write-Host "==> Creating venv"
& $Python -m venv (Join-Path $Bundle "venv")
$VenvPython = Join-Path $Bundle "venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip wheel
& $VenvPython -m pip install -r $Req

Write-Host "==> Copying application code"
Copy-Item -Recurse (Join-Path $Root "src") (Join-Path $Bundle "src")
Copy-Item -Recurse (Join-Path $Root "sidecar") (Join-Path $Bundle "sidecar")
New-Item -ItemType Directory -Path (Join-Path $Bundle "data") -Force | Out-Null
Copy-Item -Recurse (Join-Path $Root "data\job_router") (Join-Path $Bundle "data\job_router")

Write-Host "==> Pre-caching fastembed model"
$env:FASTEMBED_CACHE_PATH = Join-Path $Bundle "fastembed_cache"
New-Item -ItemType Directory -Path $env:FASTEMBED_CACHE_PATH -Force | Out-Null
& $VenvPython -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

Write-Host "==> Writing operator.env"
$OperatorEnv = @(
    "LLM_PROVIDER=nvidia",
    "LLM_BASE_URL=https://integrate.api.nvidia.com/v1",
    "LLM_MODEL=nvidia/nemotron-3-super-120b-a12b",
    "LLM_FALLBACK_MODEL=nvidia/nemotron-3-nano-30b-a3b",
    "EMBEDDING_PROVIDER=fastembed",
    "EMBEDDING_MODEL=BAAI/bge-small-en-v1.5",
    "NOUS_NVIDIA_API_KEY=$($env:NOUS_NVIDIA_API_KEY)"
)
if ($env:GEMINI_API_KEY) { $OperatorEnv += "GEMINI_API_KEY=$($env:GEMINI_API_KEY)" }
if ($env:TAVILY_API_KEY) { $OperatorEnv += "TAVILY_API_KEY=$($env:TAVILY_API_KEY)" }
$OperatorEnv | Set-Content -Path (Join-Path $Bundle "operator.env") -Encoding UTF8

Write-Host "==> Sidecar bundle ready: $Bundle"
