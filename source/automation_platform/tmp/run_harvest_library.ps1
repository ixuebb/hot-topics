$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
python -u "C:\Users\SunYu\.codex\skills\paper-writing\scripts\harvest_literature_library.py" `
  --out-dir "D:\syz_autopaper\auto_idea\video moment retrieval\download_paper" `
  --from-candidates "D:\syz_autopaper\auto_idea\video moment retrieval\download_candidates.jsonl" `
  --limit-papers 1000 `
  --download-sleep 0.2 `
  --render-dpi 160
