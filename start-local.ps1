# Resolve the project root so the script works from any current directory.
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
# Resolve the frontend directory for build and preview commands.
$frontendRoot = Join-Path $projectRoot "frontend"

function Test-Configured([string]$value) {
    return -not [string]::IsNullOrWhiteSpace($value)
}

function Write-CheckResult([string]$label, [bool]$configured, [string]$successText, [string]$warningText) {
    if ($configured) {
        Write-Host "[OK] $label - $successText" -ForegroundColor Green
    }
    else {
        Write-Host "[WARN] $label - $warningText" -ForegroundColor Yellow
    }
}

$hasDeepSeekKey = Test-Configured $env:DEEPSEEK_API_KEY
$hasOpenAIKey = Test-Configured $env:OPENAI_API_KEY
$hasLlmBaseUrl = Test-Configured $env:LLM_BASE_URL
$hasLlmModel = Test-Configured $env:LLM_MODEL
$hasAmapServiceKey = Test-Configured $env:AMAP_WEB_SERVICE_KEY
$hasAmapJsKey = Test-Configured $env:VITE_AMAP_JS_KEY

Write-Host "Checking local environment..." -ForegroundColor Cyan
Write-CheckResult "LLM key" ($hasDeepSeekKey -or $hasOpenAIKey) `
    "chat service can authenticate to an LLM provider." `
    "chat service will fail. Set DEEPSEEK_API_KEY or OPENAI_API_KEY."
Write-CheckResult "LLM_BASE_URL" $hasLlmBaseUrl `
    "custom LLM endpoint is configured." `
    "recommended for DeepSeek: https://api.deepseek.com/v1"
Write-CheckResult "LLM_MODEL" $hasLlmModel `
    "model name is configured." `
    "recommended for DeepSeek: deepseek-chat"
Write-CheckResult "AMAP_WEB_SERVICE_KEY" $hasAmapServiceKey `
    "backend can query real local POI and route data." `
    "planner will fall back to mock local candidates."
Write-CheckResult "VITE_AMAP_JS_KEY" $hasAmapJsKey `
    "frontend map display can use AMap JS." `
    "page can still run, but the live map may not render."

if (($hasDeepSeekKey -or $hasOpenAIKey) -and (-not $hasLlmBaseUrl -or -not $hasLlmModel)) {
    Write-Host "Hint: when using DeepSeek, set LLM_BASE_URL=https://api.deepseek.com/v1 and LLM_MODEL=deepseek-chat" -ForegroundColor Yellow
}

Write-Host ""

# Build the frontend first so preview always serves the latest bundle.
Write-Host "Building frontend for http://127.0.0.1:4175/ ..." -ForegroundColor Yellow
Push-Location $frontendRoot
$env:VITE_API_BASE_URL = "http://127.0.0.1:8002"
npm run build
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Frontend build failed. Startup aborted."
}
Pop-Location

# Start the backend on the only supported port.
Write-Host "Starting backend on http://127.0.0.1:8002/ ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$projectRoot'; python -m uvicorn api:app --reload --host 127.0.0.1 --port 8002"
)

# Start the frontend preview and bind it to the fixed backend address.
Write-Host "Starting frontend preview on http://127.0.0.1:4175/ ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$frontendRoot'; `$env:VITE_API_BASE_URL='http://127.0.0.1:8002'; npm run preview -- --host 127.0.0.1 --port 4175"
)

# Print the final URLs so there is only one local entrypoint to remember.
Write-Host ""
Write-Host "Services started:" -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:4175/"
Write-Host "Backend:  http://127.0.0.1:8002/"
Write-Host "Docs:     http://127.0.0.1:8002/docs"
