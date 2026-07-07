from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"Could not find expected block:\n{old}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_skill_docs.py <paper-writing-skill-dir>")
    root = Path(sys.argv[1])

    skill_path = root / "SKILL.md"
    skill = skill_path.read_text(encoding="utf-8")
    old = "- Literature survey: read `references/literature.md`. Use `search_openalex.py`, `search_semantic_scholar.py`, `search_literature.py`, `upgrade_venues.py`, `score_lqs.py`, and `verify_bib.py`."
    new = "- Literature survey: read `references/literature.md`. For durable online-to-local paper libraries, also read `references/literature_library.md` and use `harvest_literature_library.py` plus `search_local_library.py`. Use `search_openalex.py`, `search_semantic_scholar.py`, `search_literature.py`, `upgrade_venues.py`, `score_lqs.py`, and `verify_bib.py`."
    skill = replace_once(skill, old, new)
    old = "- Use web search or source APIs for current papers and venue status."
    new = "- Use web search or source APIs for current papers and venue status.\n- When the user asks to preserve literature for reuse, harvest open papers into the local literature library before writing: default VMR path `D:\\syz_autopaper\\auto_idea\\video moment retrieval\\download_paper`."
    skill = replace_once(skill, old, new)
    skill_path.write_text(skill, encoding="utf-8", newline="\n")

    lit_path = root / "references" / "literature.md"
    lit = lit_path.read_text(encoding="utf-8")
    insert = """## Stage 0: Local Library Harvest

When the task requires reusable literature assets, first build or refresh a local paper library. Read `references/literature_library.md`.

Default VMR command:

```powershell
python C:\\Users\\SunYu\\.codex\\skills\\paper-writing\\scripts\\harvest_literature_library.py --out-dir "D:\\syz_autopaper\\auto_idea\\video moment retrieval\\download_paper" --vmr-defaults --max-results 25 --limit-papers 120 --year-min 2017
```

Before writing related work or benchmark comparisons, search the local library:

```powershell
python C:\\Users\\SunYu\\.codex\\skills\\paper-writing\\scripts\\search_local_library.py --library-dir "D:\\syz_autopaper\\auto_idea\\video moment retrieval\\download_paper" --query "<claim, method, benchmark, or baseline>"
```

This stage materializes metadata, BibTeX, open PDFs, abstracts, introductions, figure assets, table assets, captions, and searchable text. It complements, but does not replace, citation scoring and BibTeX verification.

"""
    if "## Stage 0: Local Library Harvest" not in lit:
        lit = lit.replace("## Pipeline\n\nUse four stages: Recall, Score, Classify, Upgrade.\n\n", "## Pipeline\n\nUse five stages: Local Library Harvest, Recall, Score, Classify, Upgrade.\n\n" + insert, 1)
    lit_path.write_text(lit, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
