$ErrorActionPreference = "Stop"

$PackageRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$checks = @(
  "README_REPRODUCE.md",
  "source\automation_platform\projects\vmr_idea_dashboard\index.html",
  "source\automation_platform\projects\vmr_idea_dashboard\app.js",
  "source\automation_platform\projects\vmr_idea_dashboard\data\idea_opportunities_finegrained.json",
  "source\codex_skills\paper-writing\SKILL.md",
  "data\download_paper",
  "data\idea_graph\idea_opportunities_finegrained.json",
  "data\idea_graph\paper_micro_cards_index.json",
  "data\idea_graph\IDEA_REPORT_10_TOPICS.md"
)

$rows = foreach ($relative in $checks) {
  $path = Join-Path $PackageRoot $relative
  [pscustomobject]@{
    Item = $relative
    Exists = Test-Path -Path $path
  }
}

$rows | Format-Table -AutoSize

$missing = $rows | Where-Object { -not $_.Exists }
if ($missing) {
  throw "Package verification failed. Missing item count: $($missing.Count)"
}

$summaryTargets = @(
  "source\automation_platform",
  "source\codex_skills\paper-writing",
  "data\download_paper",
  "data\idea_graph"
)

Write-Host ""
Write-Host "Size summary:"
foreach ($relative in $summaryTargets) {
  $path = Join-Path $PackageRoot $relative
  $stats = Get-ChildItem -Path $path -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum
  $gb = [math]::Round(($stats.Sum / 1GB), 3)
  Write-Host "$relative`tfiles=$($stats.Count)`tGB=$gb"
}

Write-Host ""
Write-Host "Package verification passed: $PackageRoot"
