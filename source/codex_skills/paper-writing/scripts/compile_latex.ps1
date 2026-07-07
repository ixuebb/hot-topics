param(
  [Parameter(Mandatory=$true)]
  [string]$ProjectDir
)

$ErrorActionPreference = "Continue"
$project = Resolve-Path -LiteralPath $ProjectDir
$build = Join-Path $project "build"
New-Item -ItemType Directory -Force -Path $build | Out-Null

$main = Join-Path $project "main.tex"
$report = Join-Path $build "compile_report.json"
if (-not (Test-Path -LiteralPath $main)) {
  @{ success = $false; error = "Missing main.tex"; undefined_references = 0; command = $null } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $report -Encoding UTF8
  Write-Error "Missing main.tex"
  exit 1
}

$newtx = Join-Path $project "vendor\ctan_newtx\newtx"
if (Test-Path -LiteralPath $newtx) {
  $texDir = Join-Path $newtx "tex"
  $tfmDir = Join-Path $newtx "tfm"
  $vfDir = Join-Path $newtx "vf"
  $typeOneDir = Join-Path $newtx "type1"
  $afmDir = Join-Path $newtx "afm"
  $encDir = Join-Path $newtx "enc"
  $mapDir = Join-Path $newtx "map"
  $env:TEXINPUTS = "$texDir//;$($env:TEXINPUTS)"
  $env:TFMFONTS = "$tfmDir//;$($env:TFMFONTS)"
  $env:VFFONTS = "$vfDir//;$($env:VFFONTS)"
  $env:T1FONTS = "$typeOneDir//;$($env:T1FONTS)"
  $env:AFMFONTS = "$afmDir//;$($env:AFMFONTS)"
  $env:ENCFONTS = "$encDir//;$($env:ENCFONTS)"
  $env:TEXFONTMAPS = "$mapDir//;$($env:TEXFONTMAPS)"
}

$texgyre = Join-Path $project "vendor\ctan_texgyre\tex-gyre"
if (Test-Path -LiteralPath $texgyre) {
  $latexDir = Join-Path $texgyre "latex"
  $tfmDir = Join-Path $texgyre "tfm"
  $typeOneDir = Join-Path $texgyre "type1"
  $afmDir = Join-Path $texgyre "afm"
  $encDir = Join-Path $texgyre "enc"
  $mapDir = Join-Path $texgyre "map"
  $env:TEXINPUTS = "$latexDir//;$($env:TEXINPUTS)"
  $env:TFMFONTS = "$tfmDir//;$($env:TFMFONTS)"
  $env:T1FONTS = "$typeOneDir//;$($env:T1FONTS)"
  $env:AFMFONTS = "$afmDir//;$($env:AFMFONTS)"
  $env:ENCFONTS = "$encDir//;$($env:ENCFONTS)"
  $env:TEXFONTMAPS = "$mapDir//;$($env:TEXFONTMAPS)"
}

$latexmk = (Get-Command latexmk.exe -ErrorAction SilentlyContinue)
$perl = (Get-Command perl.exe -ErrorAction SilentlyContinue)
if ($latexmk -and $perl) {
  $cmd = @("latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-outdir=build", "main.tex")
} else {
  $pdflatex = (Get-Command pdflatex.exe -ErrorAction SilentlyContinue)
  if (-not $pdflatex) {
    @{ success = $false; error = "Neither latexmk nor pdflatex was found"; undefined_references = 0; command = $null } |
      ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $report -Encoding UTF8
    Write-Error "No LaTeX engine found"
    exit 1
  }
  $cmd = @("pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory=build", "main.tex")
}

Push-Location $project
try {
  $allOutput = @()
  $exe = $cmd[0]
  $argv = $cmd[1..($cmd.Length - 1)]
  $allOutput += & $exe @argv 2>&1
  $exit = $LASTEXITCODE
  if ($exe -eq "pdflatex" -and $exit -eq 0) {
    $bibtex = (Get-Command bibtex.exe -ErrorAction SilentlyContinue)
    if ($bibtex -and (Select-String -LiteralPath (Join-Path $build "main.aux") -Pattern "\\citation|\\bibdata" -Quiet -ErrorAction SilentlyContinue)) {
      $allOutput += & bibtex (Join-Path "build" "main") 2>&1
    }
    $allOutput += & $exe @argv 2>&1
    if ($LASTEXITCODE -ne 0) { $exit = $LASTEXITCODE }
    $allOutput += & $exe @argv 2>&1
    if ($LASTEXITCODE -ne 0) { $exit = $LASTEXITCODE }
  }
  $output = $allOutput
} finally {
  Pop-Location
}

$logPath = Join-Path $build "main.log"
$log = ""
if (Test-Path -LiteralPath $logPath) {
  $log = Get-Content -LiteralPath $logPath -Raw -ErrorAction SilentlyContinue
}
$undefined = ([regex]::Matches($log, "undefined references|Reference .* undefined|Citation .* undefined", "IgnoreCase")).Count
$pdf = Join-Path $build "main.pdf"
$success = ($exit -eq 0) -and (Test-Path -LiteralPath $pdf) -and ($undefined -eq 0)

@{
  success = $success
  exit_code = $exit
  command = ($cmd -join " ")
  pdf = $pdf
  undefined_references = $undefined
  output_tail = (($output | Select-Object -Last 80) -join "`n")
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $report -Encoding UTF8

if (-not $success) {
  Write-Host "LaTeX compile failed or has undefined refs. See $report"
  exit 1
}

Write-Host "LaTeX compile passed: $pdf"
