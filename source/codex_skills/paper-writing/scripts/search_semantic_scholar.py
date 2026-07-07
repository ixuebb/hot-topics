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
    r"charades-sta",
    r"activitynet captions",
    r"tacos",
    r"ego4d",
    r"natural language queries",
]

NEGATIVE_PATTERNS = [
    r"software",
    r"repository",
    r"quantum",
    r"molecular",
    r"medical image",
    r"speech",
    r"audio-only",
]


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "codex-paper-writing/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def relevant(item: dict[str, Any]) -> bool:
    text = " ".join(str(item.get(key) or "") for key in ["title", "abstract", "venue"]).lower()
    if any(re.search(pattern, text, re.I) for pattern in NEGATIVE_PATTERNS):
        return False
    return any(re.search(pattern, text, re.I) for pattern in POSITIVE_PATTERNS)


def canonical_title(title: str) -> str:
    return "".join(ch.lower() for ch in title if ch.isalnum())


def search(query: str, limit: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,authors,year,citationCount,venue,url,externalIds,publicationTypes,publicationDate",
        }
    )
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    data = fetch_json(url)
    rows = []
    for item in data.get("data", []):
        if not relevant(item):
            continue
        external = item.get("externalIds") or {}
        venue = item.get("venue") or "Unknown"
        arxiv = external.get("ArXiv")
        rows.append(
            {
                "source": "semantic_scholar",
                "source_id": item.get("paperId"),
                "title": item.get("title") or "",
                "authors": [a.get("name", "") for a in item.get("authors", [])],
                "summary": item.get("abstract") or "",
                "year": item.get("year"),
                "published": item.get("publicationDate"),
                "url": item.get("url") or (f"https://arxiv.org/abs/{arxiv}" if arxiv else ""),
                "pdf_url": f"https://arxiv.org/pdf/{arxiv}" if arxiv else "",
                "venue": venue,
                "acceptance_status": "accepted" if venue and venue.lower() not in {"unknown", "arxiv"} else "preprint",
                "citation_count": item.get("citationCount"),
                "external_ids": external,
                "publication_types": item.get("publicationTypes") or [],
                "query": query,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Semantic Scholar for literature candidates with VMR relevance filtering.")
    parser.add_argument("project_dir")
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--queries-file", default=None)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=1.2)
    parser.add_argument("--replace", action="store_true", help="Replace raw_candidates.jsonl instead of merging.")
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
        print(f"[{index}/{len(queries)}] Semantic Scholar: {query}")
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

