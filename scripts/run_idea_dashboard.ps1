param(
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$PackageRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DashboardDir = Join-Path $PackageRoot "source\automation_platform\projects\vmr_idea_dashboard"

if (-not (Test-Path -Path $DashboardDir)) {
  throw "Dashboard directory not found: $DashboardDir"
}

$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" -or $_.State -eq "LISTENING" }
if ($existing) {
  Write-Host "Port $Port is already listening. Open http://127.0.0.1:$Port/ or stop the existing process first."
  exit 0
}

$OutLog = Join-Path $DashboardDir "server.out.log"
$ErrLog = Join-Path $DashboardDir "server.err.log"
$PidFile = Join-Path $DashboardDir "server.pid"

$process = Start-Process -FilePath python `
  -ArgumentList @("-m", "http.server", "$Port", "--bind", "127.0.0.1") `
  -WorkingDirectory $DashboardDir `
  -RedirectStandardOutput $OutLog `
  -RedirectStandardError $ErrLog `
  -WindowStyle Hidden `
  -PassThru

Set-Content -Path $PidFile -Value $process.Id -Encoding ASCII

Write-Host "VMR Idea Dashboard started."
Write-Host "PID: $($process.Id)"
Write-Host "URL: http://127.0.0.1:$Port/"
