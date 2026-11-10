<#
.SYNOPSIS
  Daily TrendForge run on this PC: start camofox-browser -> collect -> stop camofox -> commit & push.

.DESCRIPTION
  Running from a home connection with a real browser (Camoufox) avoids the blocks that sites such as
  Reddit apply to scripts and datacenter IPs. Scheduled by scripts\install-schedule.ps1.
  Logs go to logs\daily-YYYY-MM-DD.log (last 30 kept).

.PARAMETER CamofoxDir
  Path to the camofox-browser checkout (default: $env:CAMOFOX_DIR or E:\camofox-browser-master).
.PARAMETER NoPush
  Collect and commit locally, but don't push.
#>
param(
  [string]$CamofoxDir = $(if ($env:CAMOFOX_DIR) { $env:CAMOFOX_DIR } else { 'E:\camofox-browser-master' }),
  [int]$Port = 9377,
  [switch]$NoPush
)

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force $LogDir | Out-Null
$Stamp = Get-Date -Format 'yyyy-MM-dd'
$Log = Join-Path $LogDir "daily-$Stamp.log"

function Write-Log([string]$msg) {
  $line = "{0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg
  Add-Content -Path $Log -Value $line -Encoding utf8
  Write-Host $line
}

function Test-Camofox {
  try { return (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:$Port/health").StatusCode -eq 200 }
  catch { return $false }
}

Write-Log "=== TrendForge daily run ==="
$started = $null

# ---- 1. camofox-browser ---------------------------------------------------
if (Test-Camofox) {
  Write-Log "camofox already running on port $Port (reusing it)"
} elseif (-not (Test-Path (Join-Path $CamofoxDir 'node_modules'))) {
  Write-Log "WARNING: $CamofoxDir has no node_modules (run 'npm install' there). Continuing without camofox."
} else {
  Write-Log "starting camofox from $CamofoxDir"
  $started = Start-Process -FilePath 'node' -ArgumentList 'server.js' -WorkingDirectory $CamofoxDir `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $LogDir 'camofox.out.log') `
    -RedirectStandardError (Join-Path $LogDir 'camofox.err.log')
  $deadline = (Get-Date).AddSeconds(120)
  while (-not (Test-Camofox) -and (Get-Date) -lt $deadline -and -not $started.HasExited) { Start-Sleep -Seconds 2 }
  if (Test-Camofox) { Write-Log "camofox ready (pid $($started.Id))" }
  else { Write-Log "WARNING: camofox did not become healthy; see logs\camofox.err.log. Continuing without it." }
}
if (Test-Camofox) { $env:CAMOFOX_URL = "http://127.0.0.1:$Port" }

# ---- 2. credentials ---------------------------------------------------------
if (-not $env:GITHUB_TOKEN) {
  $tok = (& gh auth token 2>$null)
  if ($LASTEXITCODE -eq 0 -and $tok) { $env:GITHUB_TOKEN = $tok.Trim(); Write-Log "using GitHub token from gh CLI" }
}

# ---- 3. collect -----------------------------------------------------------
$py = Join-Path $Root '.venv\Scripts\python.exe'
Push-Location $Root
try {
  cmd /c "`"$py`" -m trendforge run >> `"$Log`" 2>&1"
  $runOk = ($LASTEXITCODE -eq 0)
  Write-Log ("trendforge run " + $(if ($runOk) { 'succeeded' } else { "FAILED (exit $LASTEXITCODE)" }))
} finally {
  # ---- 4. stop camofox if we started it ------------------------------------
  if ($started -and -not $started.HasExited) {
    cmd /c "taskkill /PID $($started.Id) /T /F >nul 2>&1"
    Write-Log "camofox stopped"
  }
}

# ---- 5. commit & push -------------------------------------------------------
if ($runOk -and (Test-Path (Join-Path $Root '.git'))) {
  cmd /c "git add site/data data reports README.md >> `"$Log`" 2>&1"
  cmd /c "git diff --cached --quiet"
  if ($LASTEXITCODE -ne 0) {
    cmd /c "git commit -q -m `"data: daily update $Stamp (local + camofox)`" >> `"$Log`" 2>&1"
    Write-Log "committed data for $Stamp"
  } else {
    Write-Log "no data changes to commit"
  }
  $remote = (& git remote 2>$null)
  if ($NoPush) { Write-Log "push skipped (-NoPush)" }
  elseif (-not $remote) { Write-Log "no git remote yet; push skipped" }
  else {
    cmd /c "git pull --rebase --autostash -q >> `"$Log`" 2>&1"
    cmd /c "git push -q >> `"$Log`" 2>&1"
    Write-Log ("git push " + $(if ($LASTEXITCODE -eq 0) { 'ok' } else { "FAILED (exit $LASTEXITCODE)" }))
  }
}
Pop-Location

# ---- 6. keep last 30 logs ---------------------------------------------------
Get-ChildItem $LogDir -Filter 'daily-*.log' | Sort-Object Name -Descending | Select-Object -Skip 30 | Remove-Item -Force
Write-Log "=== done ==="
if (-not $runOk) { exit 1 }
