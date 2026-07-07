from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_LIBRARY_DIR = Path(r"D:\syz_autopaper\auto_idea\video moment retrieval\download_paper")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def tokenize(value: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", value)]


def score_text(tokens: list[str], text: str, weight: float) -> float:
    lower = text.lower()
    score = 0.0
    for token in tokens:
        score += lower.count(token) * weight
    quoted = re.findall(r'"([^"]+)"', " ".join(tokens))
    for phrase in quoted:
        if phrase.lower() in lower:
            score += 10.0 * weight
    return score


def snippet(text: str, tokens: list[str], width: int = 220) -> str:
    lower = text.lower()
    positions = [lower.find(token) for token in tokens if lower.find(token) >= 0]
    if not positions:
        return ""
    start = max(0, min(positions) - width // 3)
    value = re.sub(r"\s+", " ", text[start : start + width]).strip()
    return value


def load_paper_text(paper_dir: Path, include_full_text: bool) -> tuple[dict[str, Any], dict[str, str]]:
    metadata = read_json(paper_dir / "metadata.json")
    parts = {
        "title": str(metadata.get("title") or ""),
        "abstract": read_text(paper_dir / "abstract.md"),
        "introduction": read_text(paper_dir / "introduction.md"),
        "figure_captions": read_text(paper_dir / "figures" / "captions.md"),
        "table_captions": read_text(paper_dir / "tables" / "captions.md"),
        "bib": read_text(paper_dir / "citation.bib"),
    }
    if include_full_text:
        parts["full_text"] = read_text(paper_dir / "full_text.txt")
    table_dir = paper_dir / "tables" / "extracted"
    if table_dir.exists():
        parts["tables"] = "\n\n".join(read_text(path) for path in sorted(table_dir.glob("*.md")))
    return metadata, parts


def search_library(library_dir: Path, query: str, include_full_text: bool) -> list[dict[str, Any]]:
    tokens = tokenize(query)
    weights = {
        "title": 8.0,
        "abstract": 4.0,
        "introduction": 3.0,
        "figure_captions": 2.5,
        "table_captions": 2.5,
        "tables": 2.0,
        "bib": 1.0,
        "full_text": 0.5,
    }
    results: list[dict[str, Any]] = []
    for paper_dir in sorted(path for path in library_dir.iterdir() if path.is_dir()):
        metadata, parts = load_paper_text(paper_dir, include_full_text)
        if not metadata and not any(parts.values()):
            continue
        score = sum(score_text(tokens, text, weights.get(name, 1.0)) for name, text in parts.items())
        if score <= 0:
            continue
        combined = "\n".join(parts.values())
        results.append(
            {
                "score": round(score, 3),
                "title": metadata.get("title") or paper_dir.name,
                "year": metadata.get("year"),
                "venue": metadata.get("venue"),
                "authors": metadata.get("authors") or [],
                "folder": str(paper_dir),
                "pdf_path": metadata.get("pdf_path") or str(paper_dir / "paper.pdf"),
                "snippet": snippet(combined, tokens),
            }
        )
    return sorted(results, key=lambda row: (row["score"], row.get("year") or 0), reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search a local harvested paper library.")
    parser.add_argument("--library-dir", default=str(DEFAULT_LIBRARY_DIR))
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--include-full-text", action="store_true")
    parser.add_argument("--jsonl", action="store_true")
    args = parser.parse_args()

    library_dir = Path(args.library_dir).expanduser().resolve()
    if not library_dir.exists():
        raise SystemExit(f"Library directory does not exist: {library_dir}")
    results = search_library(library_dir, args.query, args.include_full_text)[: args.limit]
    if args.jsonl:
        for row in results:
            print(json.dumps(row, ensure_ascii=False, sort_keys=True))
        return
    for index, row in enumerate(results, start=1):
        authors = ", ".join(row.get("authors") or [])
        print(f"{index}. [{row['score']}] {row.get('year') or 'n.d.'} - {row['title']}")
        if authors:
            print(f"   Authors: {authors}")
        if row.get("venue"):
            print(f"   Venue: {row['venue']}")
        print(f"   Folder: {row['folder']}")
        if row.get("snippet"):
            print(f"   Snippet: {row['snippet']}")


if __name__ == "__main__":
    main()
