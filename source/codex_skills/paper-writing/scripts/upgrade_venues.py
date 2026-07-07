from __future__ import annotations

import argparse
import difflib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from workflow_common import read_jsonl, write_jsonl


def normalize_title(title: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in title).split())


def title_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "codex-paper-writing/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def semantic_scholar_lookup(title: str) -> dict[str, Any] | None:
    params = urllib.parse.urlencode(
        {
            "query": title,
            "limit": 3,
            "fields": "title,authors,year,citationCount,venue,url,externalIds,publicationTypes,publicationVenue",
        }
    )
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    data = fetch_json(url)
    best = None
    best_score = 0.0
    for item in data.get("data", []):
        score = title_similarity(title, item.get("title", ""))
        if score > best_score:
            best = item
            best_score = score
    if best and best_score >= 0.86:
        best["_match_score"] = round(best_score, 3)
        return best
    return None


def dblp_lookup(title: str) -> dict[str, Any] | None:
    params = urllib.parse.urlencode({"q": title, "format": "json", "h": 3})
    url = f"https://dblp.org/search/publ/api?{params}"
    data = fetch_json(url)
    hits = data.get("result", {}).get("hits", {}).get("hit", [])
    best = None
    best_score = 0.0
    for hit in hits:
        info = hit.get("info", {})
        score = title_similarity(title, info.get("title", ""))
        if score > best_score:
            best = info
            best_score = score
    if best and best_score >= 0.86:
        best["_match_score"] = round(best_score, 3)
        return best
    return None


def enrich_row(row: dict[str, Any], use_semantic_scholar: bool, use_dblp: bool) -> dict[str, Any]:
    title = row.get("title", "")
    enriched = dict(row)
    evidence = list(enriched.get("upgrade_evidence", []))

    if use_semantic_scholar and title:
        try:
            ss = semantic_scholar_lookup(title)
        except Exception as exc:
            ss = None
            evidence.append({"source": "semantic_scholar", "status": "error", "error": str(exc)})
        if ss:
            enriched["semantic_scholar_id"] = ss.get("paperId")
            enriched["citation_count"] = ss.get("citationCount")
            enriched["url"] = ss.get("url") or enriched.get("url")
            venue = ss.get("venue") or (ss.get("publicationVenue") or {}).get("name")
            if venue:
                enriched["venue"] = venue
                if str(venue).lower() != "arxiv":
                    enriched["acceptance_status"] = "accepted"
            if ss.get("year"):
                enriched["year"] = ss.get("year")
            evidence.append({"source": "semantic_scholar", "status": "matched", "match_score": ss.get("_match_score"), "venue": venue, "citation_count": ss.get("citationCount")})

    if use_dblp and title:
        current_venue = str(enriched.get("venue", "")).lower()
        if current_venue in {"", "arxiv"} or enriched.get("acceptance_status") != "accepted":
            try:
                dblp = dblp_lookup(title)
            except Exception as exc:
                dblp = None
                evidence.append({"source": "dblp", "status": "error", "error": str(exc)})
            if dblp:
                venue = dblp.get("venue") or dblp.get("booktitle") or dblp.get("journal")
                if venue:
                    enriched["venue"] = venue
                    enriched["acceptance_status"] = "accepted"
                if dblp.get("year"):
                    enriched["year"] = int(dblp["year"])
                if dblp.get("url"):
                    enriched["dblp_url"] = dblp.get("url")
                evidence.append({"source": "dblp", "status": "matched", "match_score": dblp.get("_match_score"), "venue": venue, "url": dblp.get("url")})

    enriched["upgrade_evidence"] = evidence
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich paper candidates with citation counts and accepted venues.")
    parser.add_argument("project_dir")
    parser.add_argument("--no-semantic-scholar", action="store_true")
    parser.add_argument("--no-dblp", action="store_true")
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    raw_path = project_dir / "refs" / "raw_candidates.jsonl"
    scored_path = project_dir / "refs" / "scored_candidates.jsonl"
    rows = read_jsonl(scored_path) or read_jsonl(raw_path)
    if not rows:
        raise SystemExit("No candidates found. Run search_literature.py first.")

    enriched = []
    for index, row in enumerate(rows, start=1):
        print(f"[{index}/{len(rows)}] {row.get('title', '')[:100]}")
        enriched.append(enrich_row(row, not args.no_semantic_scholar, not args.no_dblp))
        if index < len(rows):
            time.sleep(args.sleep)

    write_jsonl(project_dir / "refs" / "enriched_candidates.jsonl", enriched)
    write_jsonl(raw_path, enriched)
    accepted = sum(1 for row in enriched if row.get("acceptance_status") == "accepted")
    cited = sum(1 for row in enriched if row.get("citation_count") is not None)
    print(f"Enriched candidates: {len(enriched)}")
    print(f"With citation counts: {cited}")
    print(f"Accepted venue evidence: {accepted}")
    print("Next: rerun score_lqs.py to regenerate scored candidates, citation plan, and BibTeX.")


if __name__ == "__main__":
    main()

