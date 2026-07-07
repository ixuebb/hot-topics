param(
  [Parameter(Mandatory=$true)]
  [string]$ProjectDir,

  [string]$RemoteHost = "",
  [string]$RemoteUser = "",
  [int]$Port = 22,
  [string]$RemoteDir = "",
  [string]$KeyPath = "",
  [string]$RemoteSetupCommand = "",
  [switch]$SkipRemoteCommands,
  [switch]$Compile
)

$ErrorActionPreference = "Continue"

function Add-CommonSshArgs {
  param([string[]]$Base)
  $args = @()
  $args += $Base
  if ($KeyPath -ne "") {
    $args += @("-i", $KeyPath)
  }
  $args += @("-o", "StrictHostKeyChecking=no")
  return $args
}

function Invoke-Remote {
  param([string]$Command)
  $sshArgs = Add-CommonSshArgs @("-p", "$Port", $Target, "bash", "-lc", $Command)
  & ssh @sshArgs
  return $LASTEXITCODE
}

function Test-RemotePath {
  param([string]$Path)
  $escaped = $Path.Replace("'", "'\''")
  $code = Invoke-Remote "test -e '$escaped'"
  return ($code -eq 0)
}

function Copy-RemotePath {
  param([string]$RemotePath, [string]$LocalPath)
  if (-not (Test-RemotePath $RemotePath)) {
    return $false
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LocalPath) | Out-Null
  $scpArgs = Add-CommonSshArgs @("-P", "$Port", "-r", "${Target}:$RemotePath", $LocalPath)
  & scp @scpArgs
  return ($LASTEXITCODE -eq 0)
}

$project = Resolve-Path -LiteralPath $ProjectDir
$registryPath = Join-Path $project "experiments\registry.json"
if ((Test-Path -LiteralPath $registryPath) -and $RemoteDir -eq "") {
  $registry = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json
  if ($registry.remote -and $registry.remote.base_dir) {
    $RemoteDir = [string]$registry.remote.base_dir
  }
}

if ($RemoteHost -eq "") {
  Write-Error "RemoteHost is required, for example root@connect.westb.seetacloud.com"
  exit 1
}
if ($RemoteDir -eq "") {
  Write-Error "RemoteDir is required or must be present in experiments/registry.json"
  exit 1
}

if ($RemoteHost.Contains("@")) {
  $Target = $RemoteHost
} elseif ($RemoteUser -ne "") {
  $Target = "$RemoteUser@$RemoteHost"
} else {
  $Target = $RemoteHost
}

$report = [ordered]@{
  generated_at = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  project_dir = "$project"
  target = $Target
  port = $Port
  remote_dir = $RemoteDir
  copied = @()
  failed = @()
  local_refresh = @()
}

if (-not $SkipRemoteCommands) {
  $setup = ""
  if ($RemoteSetupCommand -ne "") {
    $setup = "$RemoteSetupCommand && "
  }
  $remoteCmd = "$setup cd '$RemoteDir' && " +
    "if [ -f scripts/collect_results.py ]; then python scripts/collect_results.py; fi; " +
    "if [ -f scripts/viz_paper.py ]; then python scripts/viz_paper.py || true; fi"
  $code = Invoke-Remote $remoteCmd
  $report.remote_command_exit_code = $code
}

$copies = @(
  @{ remote = "$RemoteDir/experiments/results/"; local = (Join-Path $project "experiments\results") },
  @{ remote = "$RemoteDir/experiments/logs/"; local = (Join-Path $project "experiments\logs") },
  @{ remote = "$RemoteDir/results/paper_numbers.tex"; local = (Join-Path $project "results_numbers.tex") },
  @{ remote = "$RemoteDir/results/paper_numbers.json"; local = (Join-Path $project "experiments\paper_numbers_remote.json") },
  @{ remote = "$RemoteDir/results/figures_paper/"; local = (Join-Path $project "figures") },
  @{ remote = "$RemoteDir/figures/"; local = (Join-Path $project "figures") }
)

foreach ($item in $copies) {
  $ok = Copy-RemotePath $item.remote $item.local
  if ($ok) {
    $report.copied += $item
  } else {
    $report.failed += $item
  }
}

$skillScripts = Split-Path -Parent $MyInvocation.MyCommand.Path
$collect = Join-Path $skillScripts "collect_paper_results.py"
$figs = Join-Path $skillScripts "generate_paper_figures.py"
$compileScript = Join-Path $skillScripts "compile_latex.ps1"

if (Test-Path -LiteralPath $collect) {
  & python $collect "$project" --patch-main
  $report.local_refresh += @{ command = "collect_paper_results.py"; exit_code = $LASTEXITCODE }
}
if (Test-Path -LiteralPath $figs) {
  & python $figs "$project"
  $report.local_refresh += @{ command = "generate_paper_figures.py"; exit_code = $LASTEXITCODE }
}
if ($Compile -and (Test-Path -LiteralPath $compileScript)) {
  & powershell -ExecutionPolicy Bypass -File $compileScript -ProjectDir "$project"
  $report.local_refresh += @{ command = "compile_latex.ps1"; exit_code = $LASTEXITCODE }
}

$reportPath = Join-Path $project "experiments\refresh_report.json"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $reportPath) | Out-Null
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Wrote $reportPath"
