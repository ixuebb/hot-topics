from __future__ import annotations

import argparse
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

from workflow_common import read_jsonl, write_jsonl


ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


def parse_year(value: str) -> int | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).year
    except Exception:
        return None


def arxiv_query(query: str, max_results: int) -> list[dict[str, Any]]:
    encoded = urllib.parse.urlencode(
        {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    url = f"https://export.arxiv.org/api/query?{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "codex-paper-writing/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    root = ET.fromstring(data)
    rows: list[dict[str, Any]] = []
    for entry in root.findall(f"{ATOM}entry"):
        title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
        summary = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
        published = entry.findtext(f"{ATOM}published") or ""
        updated = entry.findtext(f"{ATOM}updated") or ""
        authors = [a.findtext(f"{ATOM}name") or "" for a in entry.findall(f"{ATOM}author")]
        arxiv_id = (entry.findtext(f"{ATOM}id") or "").rsplit("/", 1)[-1]
        pdf_url = ""
        for link in entry.findall(f"{ATOM}link"):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href", "")
        rows.append(
            {
                "source": "arxiv",
                "source_id": arxiv_id,
                "title": title,
                "authors": authors,
                "summary": summary,
                "published": published,
                "updated": updated,
                "year": parse_year(published),
                "url": entry.findtext(f"{ATOM}id") or "",
                "pdf_url": pdf_url,
                "categories": [c.attrib.get("term", "") for c in entry.findall(f"{ATOM}category")],
                "venue": "arXiv",
                "acceptance_status": "preprint",
            }
        )
    return rows


def canonical_title(title: str) -> str:
    return "".join(ch.lower() for ch in title if ch.isalnum())


def main() -> None:
    parser = argparse.ArgumentParser(description="High-recall arXiv literature search.")
    parser.add_argument("project_dir")
    parser.add_argument("--query", action="append", default=[], help="Search query. Repeat for multiple queries.")
    parser.add_argument("--queries-file", default=None, help="Plain text file with one query per line.")
    parser.add_argument("--max-results", type=int, default=25, help="Max arXiv results per query.")
    parser.add_argument("--sleep", type=float, default=3.0, help="Delay between arXiv calls.")
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
        raise SystemExit("Provide at least one --query or --queries-file.")

    out_path = project_dir / "refs" / "raw_candidates.jsonl"
    existing = read_jsonl(out_path)
    by_key = {canonical_title(row.get("title", "")): row for row in existing if row.get("title")}

    for index, query in enumerate(queries, start=1):
        print(f"[{index}/{len(queries)}] arXiv: {query}")
        try:
            rows = arxiv_query(query, args.max_results)
        except Exception as exc:
            print(f"  failed: {exc}")
            continue
        for row in rows:
            row["query"] = query
            key = canonical_title(row.get("title", ""))
            if key and key not in by_key:
                by_key[key] = row
        if index < len(queries):
            time.sleep(args.sleep)

    write_jsonl(out_path, by_key.values())
    print(f"Wrote {len(by_key)} raw candidates to {out_path}")


if __name__ == "__main__":
    main()

