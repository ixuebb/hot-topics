from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from workflow_common import read_jsonl, write_jsonl


POSITIVE_PATTERNS = [
    r"video moment retrieval",
    r"moment retrieval",
    r"temporal video grounding",
    r"temporal grounding",
    r"natural language video localization",
    r"video localization",
    r"video-language temporal",
    r"highlight detection",
    r"qvhighlights",
    r"charades",
    r"activitynet",
    r"tacos",
    r"ego4d",
]


def canonical_title(title: str) -> str:
    return "".join(ch.lower() for ch in title if ch.isalnum())


def inverted_to_text(value: dict[str, list[int]] | None) -> str:
    if not value:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indices in value.items():
        for index in indices:
            positions.append((index, word))
    return " ".join(word for _, word in sorted(positions))


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "codex-paper-writing/1.0 (mailto:example@example.com)"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def relevant(row: dict[str, Any]) -> bool:
    text = " ".join(str(row.get(key) or "") for key in ["title", "summary", "venue"]).lower()
    return any(re.search(pattern, text, re.I) for pattern in POSITIVE_PATTERNS)


def search(query: str, per_page: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"search": query, "per-page": per_page})
    url = f"https://api.openalex.org/works?{params}"
    data = fetch_json(url)
    rows = []
    for item in data.get("results", []):
        primary = item.get("primary_location") or {}
        source = primary.get("source") or {}
        venue = source.get("display_name") or item.get("host_venue", {}).get("display_name") or "Unknown"
        doi = item.get("doi")
        row = {
            "source": "openalex",
            "source_id": item.get("id"),
            "title": item.get("display_name") or "",
            "authors": [
                (((auth.get("author") or {}).get("display_name")) or "")
                for auth in item.get("authorships", [])
            ],
            "summary": inverted_to_text(item.get("abstract_inverted_index")),
            "year": item.get("publication_year"),
            "published": item.get("publication_date"),
            "url": doi or item.get("id") or "",
            "pdf_url": (primary.get("landing_page_url") or ""),
            "venue": venue,
            "acceptance_status": "accepted" if venue and venue.lower() not in {"unknown", "arxiv"} else "preprint",
            "citation_count": item.get("cited_by_count"),
            "external_ids": {"doi": doi, "openalex": item.get("id")},
            "query": query,
        }
        if relevant(row):
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Search OpenAlex for literature candidates with VMR relevance filtering.")
    parser.add_argument("project_dir")
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--queries-file", default=None)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    queries = list(args.query)
    if args.queries_file:
        queries.extend(
            line.strip()
            for line in Path(args.queries_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    if not queries:
        raise SystemExit("Provide --query or --queries-file.")

    out_path = project_dir / "refs" / "raw_candidates.jsonl"
    existing = [] if args.replace else read_jsonl(out_path)
    by_key = {canonical_title(row.get("title", "")): row for row in existing if row.get("title")}

    for index, query in enumerate(queries, start=1):
        print(f"[{index}/{len(queries)}] OpenAlex: {query}")
        try:
            rows = search(query, args.limit)
        except Exception as exc:
            print(f"  failed: {exc}")
            continue
        print(f"  relevant: {len(rows)}")
        for row in rows:
            key = canonical_title(row.get("title", ""))
            if key:
                by_key[key] = row
        if index < len(queries):
            time.sleep(args.sleep)

    write_jsonl(out_path, by_key.values())
    print(f"Wrote {len(by_key)} candidates to {out_path}")


if __name__ == "__main__":
    main()

