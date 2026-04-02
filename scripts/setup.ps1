# 0️⃣ Strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# 1️⃣ Install Python deps via uv
Write-Host "🔧 Installing Python dependencies…" -ForegroundColor Cyan
uv sync --extra dev

# 2️⃣ Install Playwright browsers
playwright install chromium

# 3️⃣ Create Chrome profiles for Tier-3
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (Test-Path $chrome) {
    Start-Process $chrome "--user-data-dir=$env:LOCALAPPDATA\exec-agent\chrome-claude"
    Start-Process $chrome "--user-data-dir=$env:LOCALAPPDATA\exec-agent\chrome-chatgpt"
} else {
    Write-Warning "Chrome not found – you must install Chrome manually."
}

# 4️⃣ Copy .env template if missing
if (-Not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "✅ .env created – edit with your secrets." -ForegroundColor Green
}

# 5️⃣ Done
Write-Host "🚀 Setup complete. Run: uv run scripts/run_agent.py" -ForegroundColor Green
