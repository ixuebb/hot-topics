from __future__ import annotations

import json
import argparse
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


PHRASES = [
    "moment retrieval",
    "video grounding",
    "moment localization",
    "temporal grounding",
    "temporal localization",
]
DEFAULT_YEAR_MIN = 2022
DEFAULT_YEAR_MAX = date.today().year
YEAR_MIN = DEFAULT_YEAR_MIN
YEAR_MAX = DEFAULT_YEAR_MAX
TODAY = date.today().isoformat()
UA = "codex-paper-title-count/1.0"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
OUT_DIR = Path(r"D:\自动化论文平台\tmp\title_phrase_scan")
OUT_PATH = OUT_DIR / "scan_results.json"


def get(url: str, *, timeout: int = 45) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed after retries: {url}: {last_error}")


def canonical_title(title: str) -> str:
    return "".join(ch.lower() for ch in title if ch.isalnum())


def parse_year(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", str(value))
    return int(match.group(0)) if match else None


def matched_phrases(title: str) -> list[str]:
    lower = re.sub(r"\s+", " ", title.lower())
    return [phrase for phrase in PHRASES if phrase in lower]


def add_record(records: dict[str, dict[str, Any]], row: dict[str, Any]) -> None:
    title = str(row.get("title") or "").strip()
    year = parse_year(row.get("year"))
    phrases = matched_phrases(title)
    if not title or not phrases or year is None or year < YEAR_MIN or year > YEAR_MAX:
        return
    key_parts = []
    external = row.get("external_ids") or {}
    doi = str(external.get("doi") or external.get("DOI") or "").lower().strip()
    arxiv = str(external.get("arxiv") or external.get("ArXiv") or "").lower().strip()
    if doi:
        key_parts.append(f"doi:{doi}")
    if arxiv:
        key_parts.append(f"arxiv:{arxiv}")
    key_parts.append(f"title:{canonical_title(title)}")
    existing_key = next((key for key in key_parts if key in records), None)
    if existing_key is None:
        existing_key = key_parts[-1]
        records[existing_key] = {
            "title": title,
            "year": year,
            "venue": row.get("venue") or "",
            "url": row.get("url") or "",
            "pdf_url": row.get("pdf_url") or "",
            "sources": [],
            "phrases": [],
            "external_ids": {},
        }
    rec = records[existing_key]
    rec["year"] = max(int(rec.get("year") or year), year)
    if row.get("venue") and not rec.get("venue"):
        rec["venue"] = row["venue"]
    if row.get("url") and not rec.get("url"):
        rec["url"] = row["url"]
    if row.get("pdf_url") and not rec.get("pdf_url"):
        rec["pdf_url"] = row["pdf_url"]
    source = row.get("source")
    if source and source not in rec["sources"]:
        rec["sources"].append(source)
    for phrase in phrases:
        if phrase not in rec["phrases"]:
            rec["phrases"].append(phrase)
    for key, value in external.items():
        if value and not rec["external_ids"].get(key):
            rec["external_ids"][key] = value
    for key in key_parts:
        records[key] = rec


def scan_cvf(records: dict[str, dict[str, Any]], failures: list[str]) -> None:
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        for conf in ["CVPR", "ICCV"]:
            url = f"https://openaccess.thecvf.com/{conf}{year}?day=all"
            try:
                soup = BeautifulSoup(get(url, timeout=70).text, "html.parser")
            except Exception as exc:
                failures.append(f"cvf:{conf}{year}: {exc}")
                continue
            for node in soup.select("dt.ptitle"):
                link = node.find("a")
                title = node.get_text(" ", strip=True)
                detail_url = urllib.parse.urljoin(url, link.get("href") if link else "")
                add_record(
                    records,
                    {
                        "source": "cvf",
                        "title": title,
                        "year": year,
                        "venue": f"{conf} {year}",
                        "url": detail_url,
                        "external_ids": {"official_url": detail_url},
                    },
                )


def scan_neurips(records: dict[str, dict[str, Any]], failures: list[str]) -> None:
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        url = f"https://proceedings.neurips.cc/paper_files/paper/{year}"
        try:
            soup = BeautifulSoup(get(url, timeout=70).text, "html.parser")
        except Exception as exc:
            failures.append(f"neurips:{year}: {exc}")
            continue
        for link in soup.find_all("a"):
            href = link.get("href") or ""
            title = link.get_text(" ", strip=True)
            if not title or f"/paper_files/paper/{year}/" not in href or "Abstract" not in href:
                continue
            detail_url = urllib.parse.urljoin(url, href)
            add_record(
                records,
                {
                    "source": "neurips",
                    "title": title,
                    "year": year,
                    "venue": f"NeurIPS {year}",
                    "url": detail_url,
                    "external_ids": {"official_url": detail_url},
                },
            )


def openalex_works_for_phrase(phrase: str, failures: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = "*"
    page = 0
    while cursor and page < 30:
        page += 1
        params = {
            "filter": f"title.search:{phrase},from_publication_date:{YEAR_MIN}-01-01,to_publication_date:{YEAR_MAX}-12-31",
            "per-page": "200",
            "cursor": cursor,
        }
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        try:
            data = get(url, timeout=45).json()
        except Exception as exc:
            failures.append(f"openalex:{phrase}: {exc}")
            break
        rows.extend(data.get("results") or [])
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not data.get("results"):
            break
        time.sleep(0.2)
    return rows


def scan_openalex(records: dict[str, dict[str, Any]], failures: list[str]) -> None:
    for phrase in PHRASES:
        for item in openalex_works_for_phrase(phrase, failures):
            primary = item.get("primary_location") or {}
            source = primary.get("source") or {}
            doi = (item.get("doi") or "").replace("https://doi.org/", "")
            add_record(
                records,
                {
                    "source": "openalex",
                    "title": item.get("display_name") or "",
                    "year": item.get("publication_year"),
                    "venue": source.get("display_name") or "",
                    "url": item.get("doi") or item.get("id") or primary.get("landing_page_url") or "",
                    "pdf_url": primary.get("pdf_url") or "",
                    "external_ids": {"doi": doi, "openalex": item.get("id")},
                },
            )


def scan_arxiv(records: dict[str, dict[str, Any]], failures: list[str]) -> None:
    for phrase in PHRASES:
        words = phrase.split()
        query = " AND ".join(f"ti:{word}" for word in words)
        params = {
            "search_query": query,
            "start": "0",
            "max_results": "1000",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
        try:
            root = ET.fromstring(get(url, timeout=60).content)
        except Exception as exc:
            failures.append(f"arxiv:{phrase}: {exc}")
            continue
        for entry in root.findall(f"{ATOM}entry"):
            title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
            published = entry.findtext(f"{ATOM}published") or ""
            arxiv_id = (entry.findtext(f"{ATOM}id") or "").rsplit("/", 1)[-1]
            pdf_url = ""
            for link in entry.findall(f"{ATOM}link"):
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    pdf_url = link.attrib.get("href", "")
            add_record(
                records,
                {
                    "source": "arxiv",
                    "title": title,
                    "year": parse_year(published),
                    "venue": "arXiv",
                    "url": entry.findtext(f"{ATOM}id") or "",
                    "pdf_url": pdf_url,
                    "external_ids": {"arxiv": arxiv_id},
                },
            )
        time.sleep(3.0)


def scan_semantic_scholar(records: dict[str, dict[str, Any]], failures: list[str]) -> None:
    for phrase in PHRASES:
        offset = 0
        while offset < 1000:
            params = {
                "query": phrase,
                "limit": "100",
                "offset": str(offset),
                "fields": "title,year,venue,url,externalIds,openAccessPdf",
            }
            url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params)
            try:
                response = requests.get(url, headers={"User-Agent": UA}, timeout=35)
                if response.status_code == 429:
                    failures.append(f"semantic_scholar:{phrase}: HTTP 429 rate limited")
                    break
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                failures.append(f"semantic_scholar:{phrase}: {exc}")
                break
            items = data.get("data") or []
            if not items:
                break
            for item in items:
                external = item.get("externalIds") or {}
                pdf = item.get("openAccessPdf") or {}
                add_record(
                    records,
                    {
                        "source": "semantic_scholar",
                        "title": item.get("title") or "",
                        "year": item.get("year"),
                        "venue": item.get("venue") or "",
                        "url": item.get("url") or "",
                        "pdf_url": pdf.get("url") or "",
                        "external_ids": external,
                    },
                )
            offset += len(items)
            time.sleep(1.0)


def compact_unique(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[int] = set()
    unique: list[dict[str, Any]] = []
    for rec in records.values():
        ident = id(rec)
        if ident in seen:
            continue
        seen.add(ident)
        rec["sources"] = sorted(rec.get("sources") or [])
        rec["phrases"] = sorted(rec.get("phrases") or [])
        unique.append(rec)
    return sorted(unique, key=lambda row: (row.get("year") or 0, row.get("title") or ""), reverse=True)


def main() -> None:
    global YEAR_MIN, YEAR_MAX, OUT_DIR, OUT_PATH
    parser = argparse.ArgumentParser(description="Count title-phrase papers in a year range without downloading PDFs.")
    parser.add_argument("--year-min", type=int, default=DEFAULT_YEAR_MIN)
    parser.add_argument("--year-max", type=int, default=DEFAULT_YEAR_MAX)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()
    YEAR_MIN = args.year_min
    YEAR_MAX = args.year_max
    OUT_DIR = Path(args.out_dir)
    OUT_PATH = OUT_DIR / "scan_results.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    scan_cvf(records, failures)
    scan_neurips(records, failures)
    scan_openalex(records, failures)
    scan_arxiv(records, failures)
    scan_semantic_scholar(records, failures)
    unique = compact_unique(records)
    phrase_counts = Counter()
    source_counts = Counter()
    venue_counts = Counter()
    for row in unique:
        phrase_counts.update(row.get("phrases") or [])
        source_counts.update(row.get("sources") or [])
        if row.get("venue"):
            venue_counts[row["venue"]] += 1
    out = {
        "criteria": {
            "year_min_inclusive": YEAR_MIN,
            "year_max_inclusive": YEAR_MAX,
            "title_phrases": PHRASES,
            "downloaded_pdfs": False,
        },
        "total_unique": len(unique),
        "phrase_counts_nonexclusive": dict(sorted(phrase_counts.items())),
        "source_counts_nonexclusive": dict(sorted(source_counts.items())),
        "top_venues": venue_counts.most_common(30),
        "failures": failures,
        "records": unique,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ["criteria", "total_unique", "phrase_counts_nonexclusive", "source_counts_nonexclusive", "top_venues", "failures"]}, ensure_ascii=False, indent=2))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
