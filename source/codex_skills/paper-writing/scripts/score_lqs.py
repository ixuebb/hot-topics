from __future__ import annotations

import argparse
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_common import read_json, read_jsonl, write_jsonl


WEIGHTS = {
    "recency": 0.30,
    "citation_impact": 0.25,
    "venue": 0.20,
    "institution": 0.10,
    "acceptance": 0.15,
}

TOP_VENUES = {
    "neurips",
    "icml",
    "iclr",
    "acl",
    "emnlp",
    "naacl",
    "cvpr",
    "iccv",
    "eccv",
    "aaai",
    "ijcai",
    "sigmod",
    "vldb",
    "kdd",
    "www",
}


def bib_key(row: dict[str, Any]) -> str:
    authors = row.get("authors") or []
    first = "anon"
    if authors:
        first = re.sub(r"[^A-Za-z0-9]", "", str(authors[0]).split()[-1]).lower() or "anon"
    year = str(row.get("year") or "nd")
    stem_words = re.findall(r"[A-Za-z0-9]+", row.get("title", "").lower())[:4]
    stem = "".join(word[:8] for word in stem_words) or "paper"
    return f"{first}{year}{stem}"


def recency_score(year: int | None) -> float:
    if not year:
        return 4.0
    age = datetime.now(timezone.utc).year - year
    if age <= 0:
        return 10.0
    if age == 1:
        return 8.0
    if age == 2:
        return 5.0
    if age == 3:
        return 3.0
    return 2.0


def citation_score(row: dict[str, Any]) -> float:
    citations = row.get("citation_count")
    year = row.get("year")
    if citations is None:
        return 4.0
    months = max(1, (datetime.now(timezone.utc).year - int(year or datetime.now(timezone.utc).year)) * 12)
    per_month = float(citations) / months
    if per_month >= 50:
        return 10.0
    if per_month >= 10:
        return 8.0
    if per_month >= 3:
        return 6.0
    if per_month >= 1:
        return 4.0
    return 2.0


def venue_score(row: dict[str, Any]) -> float:
    venue = str(row.get("venue") or "").lower()
    if any(v in venue for v in TOP_VENUES):
        return 10.0
    if "journal" in venue or "transactions" in venue:
        return 7.0
    if "workshop" in venue:
        return 4.0
    if "arxiv" in venue:
        return 3.0
    return 5.0


def institution_score(row: dict[str, Any]) -> float:
    text = " ".join(str(x) for x in [row.get("summary", ""), row.get("affiliation", ""), row.get("institution", "")]).lower()
    top_markers = ["stanford", "mit", "berkeley", "cmu", "oxford", "cambridge", "google", "deepmind", "openai", "meta", "microsoft"]
    if any(marker in text for marker in top_markers):
        return 9.0
    return 5.0


def acceptance_score(row: dict[str, Any]) -> float:
    status = str(row.get("acceptance_status") or "").lower()
    venue = str(row.get("venue") or "").lower()
    if "accepted" in status or any(v in venue for v in TOP_VENUES):
        return 10.0
    if "under review" in status:
        return 5.0
    if "preprint" in status or "arxiv" in venue:
        return 3.0
    return 5.0


def classify_depth(lqs: float, rank: int, profile: str = "survey") -> str:
    if profile == "original_research":
        if lqs >= 8.0 and rank <= 10:
            return "A"
        if lqs >= 6.0:
            return "B"
        if lqs >= 3.0:
            return "C"
        return "D"
    if lqs >= 8.2 and rank <= 20:
        return "A"
    if lqs >= 7.0:
        return "B"
    if lqs >= 5.0:
        return "C"
    return "D"


def escape_bib(value: str) -> str:
    return value.replace("{", "\\{").replace("}", "\\}").replace("&", "\\&")


def to_bibtex(row: dict[str, Any]) -> str:
    key = row["bib_key"]
    authors = " and ".join(row.get("authors") or ["Unknown"])
    title = escape_bib(row.get("title", "Untitled"))
    year = row.get("year") or "n.d."
    url = row.get("url") or row.get("pdf_url") or ""
    venue = row.get("venue") or "arXiv"
    entry_type = "misc" if str(venue).lower() == "arxiv" else "inproceedings"
    fields = [
        f"  title={{{title}}}",
        f"  author={{{escape_bib(authors)}}}",
        f"  year={{{year}}}",
    ]
    if entry_type == "misc":
        fields.append(f"  note={{{escape_bib(venue)}}}")
    else:
        fields.append(f"  booktitle={{{escape_bib(venue)}}}")
    if url:
        fields.append(f"  url={{{url}}}")
    return f"@{entry_type}{{{key},\n" + ",\n".join(fields) + "\n}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Score raw literature candidates with LQS and emit citation plan/BibTeX.")
    parser.add_argument("project_dir")
    parser.add_argument("--min-lqs", type=float, default=None, help="Minimum LQS to include in BibTeX.")
    parser.add_argument("--max-bib", type=int, default=None, help="Maximum entries to include in BibTeX and citation plan.")
    parser.add_argument("--profile", choices=["survey", "original_research"], default=None)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    state = read_json(project_dir / "state.json", default={})
    profile = args.profile or state.get("project", {}).get("paper_type", "survey")
    min_lqs = args.min_lqs
    if min_lqs is None:
        min_lqs = 3.0 if profile == "original_research" else 5.0
    max_bib = args.max_bib
    if max_bib is None and profile == "original_research":
        max_bib = 60
    rows = read_jsonl(project_dir / "refs" / "raw_candidates.jsonl")
    if not rows:
        raise SystemExit("No raw candidates found. Run search_literature.py first.")

    scored = []
    seen_keys: set[str] = set()
    for row in rows:
        scores = {
            "recency": recency_score(row.get("year")),
            "citation_impact": citation_score(row),
            "venue": venue_score(row),
            "institution": institution_score(row),
            "acceptance": acceptance_score(row),
        }
        lqs = sum(scores[key] * WEIGHTS[key] for key in WEIGHTS)
        row = dict(row)
        row["lqs_dimensions"] = scores
        row["lqs"] = round(lqs, 3)
        key = bib_key(row)
        suffix = 2
        while key in seen_keys:
            key = f"{key}{suffix}"
            suffix += 1
        seen_keys.add(key)
        row["bib_key"] = key
        if lqs >= 7.0:
            row["citation_role"] = "must-cite"
        elif lqs >= 5.0:
            row["citation_role"] = "conditional"
        else:
            row["citation_role"] = "drop"
        scored.append(row)

    scored.sort(key=lambda item: item.get("lqs", 0), reverse=True)
    for rank, row in enumerate(scored, start=1):
        row["rank"] = rank
        row["citation_depth"] = classify_depth(float(row["lqs"]), rank, profile)

    write_jsonl(project_dir / "refs" / "scored_candidates.jsonl", scored)

    eligible = [row for row in scored if row.get("citation_depth") != "D"]
    if max_bib is not None:
        eligible = eligible[:max_bib]
    citation_plan = [
        {
            "bib_key": row["bib_key"],
            "title": row.get("title"),
            "lqs": row.get("lqs"),
            "depth": row.get("citation_depth"),
            "role": row.get("citation_role"),
            "taxonomy_cell": row.get("taxonomy_cell", "unassigned"),
            "intended_use": "Assign to a section before citing.",
        }
        for row in eligible
    ]
    write_jsonl(project_dir / "refs" / "citation_plan.jsonl", citation_plan)

    bib_rows = [row for row in scored if float(row.get("lqs", 0)) >= float(min_lqs)]
    if max_bib is not None:
        bib_rows = bib_rows[:max_bib]
    bib_entries = [to_bibtex(row) for row in bib_rows]
    (project_dir / "refs" / "references.bib").write_text("\n".join(bib_entries), encoding="utf-8")

    print(f"Profile: {profile}")
    print(f"Scored {len(scored)} candidates.")
    print(f"BibTeX entries: {len(bib_entries)}")
    print(f"A/B/C/D: {sum(r['citation_depth']=='A' for r in scored)}/{sum(r['citation_depth']=='B' for r in scored)}/{sum(r['citation_depth']=='C' for r in scored)}/{sum(r['citation_depth']=='D' for r in scored)}")


if __name__ == "__main__":
    main()
