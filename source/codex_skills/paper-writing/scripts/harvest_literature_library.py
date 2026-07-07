from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional dependency
    fitz = None

try:
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency
    BeautifulSoup = None


DEFAULT_LIBRARY_DIR = Path(r"D:\syz_autopaper\auto_idea\video moment retrieval\download_paper")
USER_AGENT = "codex-paper-writing-literature-library/1.0"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
CURRENT_YEAR = datetime.now().year
CVF_BASE = "https://openaccess.thecvf.com/"
NEURIPS_BASE = "https://proceedings.neurips.cc/"
OFFICIAL_SOURCES = {"cvf", "neurips"}
SOURCE_PRIORITY = {
    "cvf": 100,
    "neurips": 100,
    "semantic_scholar": 50,
    "openalex": 40,
    "arxiv": 10,
}
TEXT_PAGE_CACHE: dict[str, str] = {}


DEFAULT_VMR_QUERIES = [
    "video moment retrieval QVHighlights",
    "temporal video grounding natural language video localization",
    "moment retrieval highlight detection",
    "Charades-STA ActivityNet Captions TACoS temporal grounding",
    "query dependent video moment retrieval transformer",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(sanitize_text(row), ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(sanitize_text(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(clean_string(text).rstrip() + "\n", encoding="utf-8")


def clean_string(value: str) -> str:
    return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def sanitize_text(value: Any) -> Any:
    if isinstance(value, str):
        return clean_string(value)
    if isinstance(value, list):
        return [sanitize_text(item) for item in value]
    if isinstance(value, dict):
        return {clean_string(str(key)): sanitize_text(item) for key, item in value.items()}
    return value


def slugify(text: str, fallback: str = "paper") -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return value or fallback


def canonical_title(title: str) -> str:
    return "".join(ch.lower() for ch in title if ch.isalnum())


def sha1_short(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:10]


def require_requests() -> None:
    if requests is None:
        raise RuntimeError("This script needs the 'requests' package for online search and download.")


def fetch_json(url: str, timeout: int = 45) -> dict[str, Any]:
    require_requests()
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_text(url: str, timeout: int = 45) -> str:
    require_requests()
    if url in TEXT_PAGE_CACHE:
        return TEXT_PAGE_CACHE[url]
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    TEXT_PAGE_CACHE[url] = response.text
    return response.text


def download_binary(url: str, timeout: int = 90) -> bytes:
    require_requests()
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.content


def parse_year(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).year
    except Exception:
        match = re.search(r"\b(19|20)\d{2}\b", value)
        return int(match.group(0)) if match else None


def inverted_to_text(value: dict[str, list[int]] | None) -> str:
    if not value:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indices in value.items():
        for index in indices:
            positions.append((index, word))
    return " ".join(word for _, word in sorted(positions))


def require_bs4() -> None:
    if BeautifulSoup is None:
        raise RuntimeError("This script needs 'beautifulsoup4' for official proceedings pages.")


def query_tokens(query: str) -> list[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "recent",
        "benchmark",
        "benchmarks",
    }
    tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", query)]
    return [token for token in tokens if token not in stopwords]


def text_match_score(query: str, *parts: str) -> int:
    text = " ".join(part for part in parts if part).lower()
    tokens = query_tokens(query)
    if not tokens:
        return 0
    score = sum(1 for token in tokens if token in text)
    phrase = query.strip().lower()
    if phrase and phrase in text:
        score += max(4, len(tokens))
    return score


def split_authors(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"\s*,\s*|\s+;\s+", text) if part.strip()]


def source_priority(record: dict[str, Any]) -> int:
    sources = record.get("sources") or [record.get("source")]
    return max((SOURCE_PRIORITY.get(str(source), 0) for source in sources if source), default=0)


def official_record(record: dict[str, Any]) -> bool:
    sources = set(record.get("sources") or [record.get("source")])
    return bool(sources & OFFICIAL_SOURCES)


def official_pdf_url(record: dict[str, Any]) -> bool:
    pdf_url = str(record.get("pdf_url") or "").lower()
    return "openaccess.thecvf.com" in pdf_url or "proceedings.neurips.cc" in pdf_url


def first_link(soup: Any, text_pattern: str | None = None, href_pattern: str | None = None) -> str:
    for link in soup.find_all("a"):
        text = link.get_text(" ", strip=True)
        href = link.get("href") or ""
        if text_pattern and not re.search(text_pattern, text, re.I):
            continue
        if href_pattern and not re.search(href_pattern, href, re.I):
            continue
        if href:
            return href
    return ""


def cvf_detail(detail_url: str) -> tuple[str, str]:
    try:
        detail_soup = BeautifulSoup(fetch_text(detail_url), "html.parser")
    except Exception:
        return "", ""
    abstract_node = detail_soup.find(id="abstract")
    summary = abstract_node.get_text(" ", strip=True) if abstract_node else ""
    pdf_href = first_link(detail_soup, text_pattern=r"pdf", href_pattern=r"\.pdf$")
    if not pdf_href:
        pdf_href = first_link(detail_soup, href_pattern=r"\.pdf$")
    return summary, urllib.parse.urljoin(detail_url, pdf_href) if pdf_href else ""


def cvf_search(query: str, limit: int, year_min: int | None = None, year_max: int | None = None) -> list[dict[str, Any]]:
    require_bs4()
    year_min = year_min or 2017
    year_max = year_max or CURRENT_YEAR
    rows: list[dict[str, Any]] = []
    for year in range(year_max, year_min - 1, -1):
        for conf in ["CVPR", "ICCV"]:
            list_url = f"{CVF_BASE}{conf}{year}?day=all"
            try:
                soup = BeautifulSoup(fetch_text(list_url, timeout=60), "html.parser")
            except Exception:
                continue
            for title_node in soup.select("dt.ptitle"):
                link = title_node.find("a")
                if not link:
                    continue
                title = link.get_text(" ", strip=True)
                detail_url = urllib.parse.urljoin(list_url, link.get("href") or "")
                details = title_node.find_next_sibling("dd")
                authors: list[str] = []
                pdf_url = ""
                if details:
                    author_node = details.find(class_="authors")
                    if author_node:
                        authors = split_authors(author_node.get_text(" ", strip=True))
                    pdf_href = first_link(details, text_pattern=r"pdf", href_pattern=r"\.pdf$")
                    if not pdf_href:
                        pdf_href = first_link(details, href_pattern=r"\.pdf$")
                    pdf_url = urllib.parse.urljoin(list_url, pdf_href) if pdf_href else ""
                if text_match_score(query, title, " ".join(authors)) <= 0:
                    continue
                summary, detail_pdf = cvf_detail(detail_url)
                pdf_url = detail_pdf or pdf_url
                rows.append(
                    {
                        "source": "cvf",
                        "sources": ["cvf"],
                        "source_id": f"{conf}{year}:{sha1_short(title)}",
                        "title": title,
                        "authors": authors,
                        "summary": summary,
                        "year": year,
                        "published": str(year),
                        "url": detail_url,
                        "pdf_url": pdf_url,
                        "venue": f"{conf} {year}",
                        "acceptance_status": "accepted",
                        "citation_count": None,
                        "external_ids": {"official_url": detail_url, "official_source": "cvf"},
                        "publication_types": ["Conference"],
                        "query": query,
                        "queries": [query],
                    }
                )
                if len(rows) >= limit:
                    return rows
    return rows


def neurips_detail(detail_url: str) -> tuple[str, list[str], str, str, str]:
    try:
        detail_soup = BeautifulSoup(fetch_text(detail_url), "html.parser")
    except Exception:
        return "", [], "", "", ""
    title_node = detail_soup.find("h1")
    title = title_node.get_text(" ", strip=True) if title_node else ""
    paragraphs = detail_soup.find_all("p")
    authors = split_authors(paragraphs[0].get_text(" ", strip=True)) if paragraphs else []
    venue = paragraphs[1].get_text(" ", strip=True) if len(paragraphs) > 1 else ""
    abstract = ""
    abstract_header = detail_soup.find(lambda tag: tag.name in {"h2", "h3"} and tag.get_text(" ", strip=True).lower() == "abstract")
    if abstract_header:
        abstract_node = abstract_header.find_next("p")
        if abstract_node:
            abstract = abstract_node.get_text(" ", strip=True)
    pdf_href = first_link(detail_soup, text_pattern=r"paper", href_pattern=r"\.pdf$")
    if not pdf_href:
        pdf_href = first_link(detail_soup, href_pattern=r"\.pdf$")
    return title, authors, venue, abstract, urllib.parse.urljoin(detail_url, pdf_href) if pdf_href else ""


def neurips_search(query: str, limit: int, year_min: int | None = None, year_max: int | None = None) -> list[dict[str, Any]]:
    require_bs4()
    year_min = year_min or 2017
    year_max = year_max or CURRENT_YEAR
    rows: list[dict[str, Any]] = []
    for year in range(year_max, year_min - 1, -1):
        list_url = f"{NEURIPS_BASE}paper_files/paper/{year}"
        try:
            soup = BeautifulSoup(fetch_text(list_url, timeout=60), "html.parser")
        except Exception:
            continue
        candidate_links = [
            link
            for link in soup.find_all("a")
            if link.get("href")
            and f"/paper_files/paper/{year}/" in link.get("href")
            and "Abstract" in link.get("href")
            and link.get_text(" ", strip=True)
        ]
        for link in candidate_links:
            title = link.get_text(" ", strip=True)
            if text_match_score(query, title) <= 0:
                continue
            detail_url = urllib.parse.urljoin(list_url, link.get("href") or "")
            detail_title, authors, venue_text, abstract, pdf_url = neurips_detail(detail_url)
            title = detail_title or title
            doi = ""
            doi_match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", venue_text, re.I)
            if doi_match:
                doi = doi_match.group(0)
            rows.append(
                {
                    "source": "neurips",
                    "sources": ["neurips"],
                    "source_id": f"neurips{year}:{sha1_short(title)}",
                    "title": title,
                    "authors": authors,
                    "summary": abstract,
                    "year": year,
                    "published": str(year),
                    "url": detail_url,
                    "pdf_url": pdf_url,
                    "venue": f"NeurIPS {year}",
                    "acceptance_status": "accepted",
                    "citation_count": None,
                    "external_ids": {"doi": doi, "official_url": detail_url, "official_source": "neurips"} if doi else {"official_url": detail_url, "official_source": "neurips"},
                    "publication_types": ["Conference"],
                    "query": query,
                    "queries": [query],
                }
            )
            if len(rows) >= limit:
                return rows
    return rows


def arxiv_search(query: str, max_results: int) -> list[dict[str, Any]]:
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
    require_requests()
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=45)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    rows: list[dict[str, Any]] = []
    for entry in root.findall(f"{ATOM}entry"):
        title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
        summary = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
        published = entry.findtext(f"{ATOM}published") or ""
        updated = entry.findtext(f"{ATOM}updated") or ""
        arxiv_id = (entry.findtext(f"{ATOM}id") or "").rsplit("/", 1)[-1]
        doi = entry.findtext(f"{ARXIV}doi") or ""
        pdf_url = ""
        for link in entry.findall(f"{ATOM}link"):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href", "")
        rows.append(
            {
                "source": "arxiv",
                "sources": ["arxiv"],
                "source_id": arxiv_id,
                "title": title,
                "authors": [a.findtext(f"{ATOM}name") or "" for a in entry.findall(f"{ATOM}author")],
                "summary": summary,
                "published": published,
                "updated": updated,
                "year": parse_year(published),
                "url": entry.findtext(f"{ATOM}id") or "",
                "pdf_url": pdf_url,
                "venue": "arXiv",
                "acceptance_status": "preprint",
                "external_ids": {"arxiv": arxiv_id, "doi": doi} if doi else {"arxiv": arxiv_id},
                "categories": [c.attrib.get("term", "") for c in entry.findall(f"{ATOM}category")],
                "query": query,
                "queries": [query],
            }
        )
    return rows


def semantic_scholar_search(query: str, limit: int) -> list[dict[str, Any]]:
    fields = ",".join(
        [
            "title",
            "abstract",
            "authors",
            "year",
            "citationCount",
            "venue",
            "url",
            "externalIds",
            "publicationTypes",
            "publicationDate",
            "openAccessPdf",
        ]
    )
    params = urllib.parse.urlencode({"query": query, "limit": limit, "fields": fields})
    data = fetch_json(f"https://api.semanticscholar.org/graph/v1/paper/search?{params}")
    rows: list[dict[str, Any]] = []
    for item in data.get("data", []):
        external = item.get("externalIds") or {}
        arxiv_id = external.get("ArXiv") or external.get("arxiv")
        open_pdf = item.get("openAccessPdf") or {}
        pdf_url = open_pdf.get("url") or (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "")
        venue = item.get("venue") or "Unknown"
        rows.append(
            {
                "source": "semantic_scholar",
                "sources": ["semantic_scholar"],
                "source_id": item.get("paperId"),
                "title": item.get("title") or "",
                "authors": [a.get("name", "") for a in item.get("authors", [])],
                "summary": item.get("abstract") or "",
                "year": item.get("year"),
                "published": item.get("publicationDate"),
                "url": item.get("url") or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""),
                "pdf_url": pdf_url,
                "venue": venue,
                "acceptance_status": "accepted" if venue and venue.lower() not in {"unknown", "arxiv"} else "preprint",
                "citation_count": item.get("citationCount"),
                "external_ids": external,
                "publication_types": item.get("publicationTypes") or [],
                "query": query,
                "queries": [query],
            }
        )
    return rows


def openalex_search(query: str, limit: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"search": query, "per-page": limit})
    data = fetch_json(f"https://api.openalex.org/works?{params}")
    rows: list[dict[str, Any]] = []
    for item in data.get("results", []):
        primary = item.get("primary_location") or {}
        source = primary.get("source") or {}
        venue = source.get("display_name") or "Unknown"
        doi = (item.get("doi") or "").replace("https://doi.org/", "")
        pdf_url = primary.get("pdf_url") or ""
        rows.append(
            {
                "source": "openalex",
                "sources": ["openalex"],
                "source_id": item.get("id"),
                "title": item.get("display_name") or "",
                "authors": [
                    ((auth.get("author") or {}).get("display_name")) or ""
                    for auth in item.get("authorships", [])
                ],
                "summary": inverted_to_text(item.get("abstract_inverted_index")),
                "year": item.get("publication_year"),
                "published": item.get("publication_date"),
                "url": item.get("doi") or item.get("id") or primary.get("landing_page_url") or "",
                "pdf_url": pdf_url,
                "venue": venue,
                "acceptance_status": "accepted" if venue and venue.lower() not in {"unknown", "arxiv"} else "preprint",
                "citation_count": item.get("cited_by_count"),
                "external_ids": {"doi": doi, "openalex": item.get("id")},
                "query": query,
                "queries": [query],
            }
        )
    return rows


def identity_keys(record: dict[str, Any]) -> list[str]:
    external = record.get("external_ids") or {}
    keys: list[str] = []
    doi = str(external.get("DOI") or external.get("doi") or "").lower().strip()
    if doi:
        keys.append(f"doi:{doi}")
    arxiv_id = str(external.get("ArXiv") or external.get("arxiv") or "").lower().strip()
    if record.get("source") == "arxiv" and arxiv_id:
        keys.append(f"arxiv:{arxiv_id}")
    elif arxiv_id:
        keys.append(f"arxiv:{arxiv_id}")
    title_key = canonical_title(str(record.get("title") or ""))
    if title_key:
        keys.append(f"title:{title_key}")
    if not keys:
        keys.append(f"unknown:{sha1_short(json.dumps(record, sort_keys=True))}")
    return keys


def identity_key(record: dict[str, Any]) -> str:
    return identity_keys(record)[0]


def merge_record(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    incoming_priority = source_priority(incoming)
    base_priority = source_priority(base)
    for key in ["title", "published"]:
        if incoming.get(key) and (not merged.get(key) or incoming_priority > base_priority):
            merged[key] = incoming[key]
    for key in ["url", "venue", "acceptance_status"]:
        if incoming.get(key) and (not merged.get(key) or incoming_priority > base_priority):
            merged[key] = incoming[key]
    if incoming.get("pdf_url") and (
        not merged.get("pdf_url")
        or incoming_priority > base_priority
        or (official_pdf_url(incoming) and not official_pdf_url(merged))
    ):
        merged["pdf_url"] = incoming["pdf_url"]
    if len(str(incoming.get("summary") or "")) > len(str(merged.get("summary") or "")):
        merged["summary"] = incoming.get("summary") or ""
    if incoming.get("year") and (
        not merged.get("year") or incoming_priority > base_priority or int(incoming["year"]) > int(merged["year"])
    ):
        merged["year"] = incoming["year"]
    if incoming.get("citation_count") and (
        not merged.get("citation_count") or int(incoming["citation_count"]) > int(merged["citation_count"])
    ):
        merged["citation_count"] = incoming["citation_count"]
    if incoming.get("authors") and len(incoming["authors"]) > len(merged.get("authors") or []):
        merged["authors"] = incoming["authors"]
    merged.setdefault("sources", [])
    for source in incoming.get("sources") or [incoming.get("source")]:
        if source and source not in merged["sources"]:
            merged["sources"].append(source)
    merged.setdefault("queries", [])
    for query in incoming.get("queries") or [incoming.get("query")]:
        if query and query not in merged["queries"]:
            merged["queries"].append(query)
    merged.setdefault("external_ids", {})
    for key, value in (incoming.get("external_ids") or {}).items():
        if value and not merged["external_ids"].get(key):
            merged["external_ids"][key] = value
    return merged


def merge_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_rows: list[dict[str, Any]] = []
    by_key: dict[str, int] = {}
    for record in records:
        keys = identity_keys(record)
        target_index = next((by_key[key] for key in keys if key in by_key), None)
        if target_index is None:
            merged_rows.append(record)
            target_index = len(merged_rows) - 1
        else:
            merged_rows[target_index] = merge_record(merged_rows[target_index], record)
        for key in identity_keys(merged_rows[target_index]) + keys:
            by_key[key] = target_index
    return merged_rows


def sort_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda row: (
            int(row.get("year") or 0),
            source_priority(row),
            int(row.get("citation_count") or 0),
            bool(row.get("pdf_url")),
            row.get("title") or "",
        ),
        reverse=True,
    )


def first_author_slug(authors: list[str]) -> str:
    if not authors:
        return "unknown"
    first = authors[0].strip()
    if not first:
        return "unknown"
    token = re.split(r"\s+", first)[-1]
    return slugify(token, "author")[:24]


def paper_dir_name(record: dict[str, Any]) -> str:
    year = str(record.get("year") or "unknown")
    author = first_author_slug(record.get("authors") or [])
    title = slugify(str(record.get("title") or "untitled"))[:80].strip("-")
    return f"{year}_{author}_{title}_{sha1_short(canonical_title(str(record.get('title') or 'untitled')))}"[:150]


def latex_escape(value: str) -> str:
    return (
        value.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def bib_key(record: dict[str, Any]) -> str:
    authors = record.get("authors") or []
    author = first_author_slug(authors)
    year = str(record.get("year") or "nd")
    title_words = re.findall(r"[A-Za-z0-9]+", str(record.get("title") or "paper"))
    title_word = next((word for word in title_words if len(word) > 3), "paper").lower()
    return re.sub(r"[^A-Za-z0-9_:-]", "", f"{author}{year}{title_word}")


def render_bibtex(record: dict[str, Any]) -> str:
    venue = str(record.get("venue") or "")
    external = record.get("external_ids") or {}
    doi = external.get("DOI") or external.get("doi")
    arxiv_id = external.get("ArXiv") or external.get("arxiv")
    accepted = venue and venue.lower() not in {"unknown", "arxiv"}
    entry_type = "inproceedings" if accepted else "article"
    fields = {
        "title": latex_escape(str(record.get("title") or "")),
        "author": latex_escape(" and ".join(record.get("authors") or [])),
        "year": str(record.get("year") or ""),
        "url": str(record.get("url") or record.get("pdf_url") or ""),
    }
    if accepted:
        fields["booktitle"] = latex_escape(venue)
    elif arxiv_id:
        fields["journal"] = f"arXiv preprint arXiv:{arxiv_id}"
        fields["eprint"] = str(arxiv_id)
        fields["archivePrefix"] = "arXiv"
    elif venue:
        fields["journal"] = latex_escape(venue)
    if doi:
        fields["doi"] = str(doi)
    body = ",\n".join(f"  {key} = {{{value}}}" for key, value in fields.items() if value)
    return f"@{entry_type}{{{bib_key(record)},\n{body}\n}}\n"


def arxiv_pdf_from_record(record: dict[str, Any]) -> str:
    external = record.get("external_ids") or {}
    values = [
        str(external.get("ArXiv") or external.get("arxiv") or ""),
        str(record.get("url") or ""),
        str(record.get("pdf_url") or ""),
    ]
    for value in values:
        stripped = value.strip()
        lower = stripped.lower()
        if not ("arxiv" in lower or re.match(r"^\d{4}\.\d{4,5}(?:v\d+)?$", stripped)):
            continue
        match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", value)
        if not match:
            continue
        yymm = match.group(1).split(".", 1)[0]
        month = int(yymm[2:])
        if 1 <= month <= 12:
            return f"https://arxiv.org/pdf/{match.group(1)}"
    return ""


def resolve_record_links(record: dict[str, Any]) -> dict[str, Any]:
    record = dict(record)
    external = dict(record.get("external_ids") or {})
    record["external_ids"] = external
    official_url = str(external.get("official_url") or record.get("url") or "")
    try:
        if "openaccess.thecvf.com" in official_url:
            summary, pdf_url = cvf_detail(official_url)
            if summary and len(summary) > len(str(record.get("summary") or "")):
                record["summary"] = summary
            if pdf_url:
                record["pdf_url"] = pdf_url
                external.setdefault("official_source", "cvf")
        elif "proceedings.neurips.cc" in official_url and "Abstract" in official_url:
            title, authors, venue, abstract, pdf_url = neurips_detail(official_url)
            if title:
                record["title"] = title
            if authors and not record.get("authors"):
                record["authors"] = authors
            if venue and not record.get("venue"):
                record["venue"] = venue
            if abstract and len(abstract) > len(str(record.get("summary") or "")):
                record["summary"] = abstract
            if pdf_url:
                record["pdf_url"] = pdf_url
                external.setdefault("official_source", "neurips")
    except Exception as exc:
        record.setdefault("link_resolution_errors", []).append(str(exc))
    if not record.get("pdf_url"):
        arxiv_pdf = arxiv_pdf_from_record(record)
        if arxiv_pdf:
            record["pdf_url"] = arxiv_pdf
    return record


def normalize_pdf_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_abstract(full_text: str, metadata_summary: str) -> str:
    if metadata_summary.strip():
        return metadata_summary.strip()
    match = re.search(
        r"(?is)(?:^|\n)\s*abstract\s*\n?(.*?)(?=\n\s*(?:keywords|index terms|1\s*\.?\s*introduction|introduction)\b)",
        full_text,
    )
    if match:
        return normalize_pdf_text(match.group(1))
    return ""


def extract_introduction(full_text: str) -> str:
    start_patterns = [
        r"(?im)^\s*(?:1|I)\.?\s+Introduction\s*$",
        r"(?im)^\s*Introduction\s*$",
    ]
    start_match = None
    for pattern in start_patterns:
        start_match = re.search(pattern, full_text)
        if start_match:
            break
    if not start_match:
        return ""
    rest = full_text[start_match.end() :]
    end_patterns = [
        r"(?im)^\s*(?:2|II)\.?\s+.+$",
        r"(?im)^\s*(?:Related Work|Background|Preliminaries|Method|Approach|Problem Formulation|Dataset|Experiments)\s*$",
    ]
    end_positions = []
    for pattern in end_patterns:
        match = re.search(pattern, rest)
        if match:
            end_positions.append(match.start())
    end = min(end_positions) if end_positions else min(len(rest), 12000)
    return normalize_pdf_text(rest[:end])


def caption_blocks(page_texts: list[tuple[int, str]], kind: str) -> list[str]:
    if kind == "figure":
        pattern = re.compile(r"^\s*(?:Fig\.?|Figure)\s*\d+[\.:]?\s+", re.I)
    else:
        pattern = re.compile(r"^\s*Table\s*\d+[\.:]?\s+", re.I)
    blocks: list[str] = []
    for page_number, text in page_texts:
        lines = [line.strip() for line in text.splitlines()]
        for index, line in enumerate(lines):
            if not pattern.search(line):
                continue
            block = [f"Page {page_number}: {line}"]
            for follow in lines[index + 1 : index + 6]:
                if not follow or pattern.search(follow) or re.match(r"^\s*(?:Fig\.?|Figure|Table)\s*\d+", follow, re.I):
                    break
                if len(follow) > 4:
                    block.append(follow)
            blocks.append(" ".join(block))
    return blocks


def markdown_table(rows: list[list[Any]]) -> str:
    cleaned = [["" if cell is None else str(cell).replace("\n", " ").strip() for cell in row] for row in rows if row]
    if not cleaned:
        return ""
    width = max(len(row) for row in cleaned)
    cleaned = [row + [""] * (width - len(row)) for row in cleaned]
    header = cleaned[0]
    separator = ["---"] * width
    body = cleaned[1:] if len(cleaned) > 1 else []

    def line(row: list[str]) -> str:
        return "| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |"

    return "\n".join([line(header), line(separator), *[line(row) for row in body]])


def sanitize_table_rows(rows: list[list[Any]]) -> list[list[str]]:
    return [
        [clean_string("" if cell is None else str(cell).replace("\n", " ").strip()) for cell in row]
        for row in rows
        if row
    ]


def save_page_snapshot(page: Any, path: Path, dpi: int) -> None:
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    ensure_dir(path.parent)
    pix.save(str(path))


def extract_pdf_assets(pdf_path: Path, paper_dir: Path, record: dict[str, Any], render_dpi: int) -> dict[str, Any]:
    report: dict[str, Any] = {
        "pdf": str(pdf_path),
        "full_text": False,
        "abstract": False,
        "introduction": False,
        "embedded_images": 0,
        "figure_page_snapshots": 0,
        "tables": 0,
        "table_page_snapshots": 0,
        "errors": [],
    }
    if fitz is None:
        report["errors"].append("PyMuPDF is not installed; PDF extraction skipped.")
        return report

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        report["errors"].append(f"Could not open PDF: {exc}")
        return report

    page_texts: list[tuple[int, str]] = []
    full_chunks: list[str] = []
    try:
        for page_index, page in enumerate(doc):
            text = page.get_text("text") or ""
            page_number = page_index + 1
            page_texts.append((page_number, text))
            full_chunks.append(f"\n\n--- Page {page_number} ---\n{text}")
        full_text = normalize_pdf_text("".join(full_chunks))
        if full_text:
            write_text(paper_dir / "full_text.txt", full_text)
            report["full_text"] = True

        abstract = extract_abstract(full_text, str(record.get("summary") or ""))
        write_text(paper_dir / "abstract.md", f"# Abstract\n\n{abstract}" if abstract else "# Abstract\n\n")
        report["abstract"] = bool(abstract)

        introduction = extract_introduction(full_text)
        write_text(
            paper_dir / "introduction.md",
            f"# Introduction\n\n{introduction}" if introduction else "# Introduction\n\n",
        )
        report["introduction"] = bool(introduction)

        figure_captions = caption_blocks(page_texts, "figure")
        table_captions = caption_blocks(page_texts, "table")
        write_text(
            paper_dir / "figures" / "captions.md",
            "# Figure Captions\n\n" + ("\n\n".join(f"- {item}" for item in figure_captions) if figure_captions else ""),
        )
        write_text(
            paper_dir / "tables" / "captions.md",
            "# Table Captions\n\n" + ("\n\n".join(f"- {item}" for item in table_captions) if table_captions else ""),
        )

        seen_images: set[str] = set()
        embedded_dir = ensure_dir(paper_dir / "figures" / "embedded")
        for page_index, page in enumerate(doc):
            for image in page.get_images(full=True):
                xref = image[0]
                try:
                    image_data = doc.extract_image(xref)
                    data = image_data.get("image")
                    ext = image_data.get("ext") or "png"
                    if not data:
                        continue
                    digest = hashlib.sha1(data).hexdigest()
                    if digest in seen_images:
                        continue
                    seen_images.add(digest)
                    name = f"figure_{len(seen_images):03d}_page_{page_index + 1:03d}.{ext}"
                    (embedded_dir / name).write_bytes(data)
                except Exception as exc:
                    report["errors"].append(f"Image extraction failed on page {page_index + 1}: {exc}")
        report["embedded_images"] = len(seen_images)

        figure_page_dir = ensure_dir(paper_dir / "figures" / "pages")
        table_page_dir = ensure_dir(paper_dir / "tables" / "pages")
        for page_index, page in enumerate(doc):
            text = page_texts[page_index][1]
            page_number = page_index + 1
            if re.search(r"\b(?:Fig\.?|Figure)\s*\d+", text, re.I):
                save_page_snapshot(page, figure_page_dir / f"page_{page_number:03d}.png", render_dpi)
                report["figure_page_snapshots"] += 1
            if re.search(r"\bTable\s*\d+", text, re.I):
                save_page_snapshot(page, table_page_dir / f"page_{page_number:03d}.png", render_dpi)
                report["table_page_snapshots"] += 1

        tables_dir = ensure_dir(paper_dir / "tables" / "extracted")
        table_count = 0
        for page_index, page in enumerate(doc):
            finder = None
            try:
                finder = page.find_tables()
            except Exception as exc:
                report["errors"].append(f"Table detection failed on page {page_index + 1}: {exc}")
            if not finder:
                continue
            for table in finder.tables:
                try:
                    rows = table.extract()
                except Exception as exc:
                    report["errors"].append(f"Table extraction failed on page {page_index + 1}: {exc}")
                    continue
                if not rows:
                    continue
                rows = sanitize_table_rows(rows)
                table_count += 1
                stem = f"table_{table_count:03d}_page_{page_index + 1:03d}"
                write_text(tables_dir / f"{stem}.md", markdown_table(rows))
                with (tables_dir / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerows(rows)
        report["tables"] = table_count
    finally:
        doc.close()
    return report


def write_paper_artifacts(record: dict[str, Any], library_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    record = resolve_record_links(record)
    paper_dir = ensure_dir(library_dir / paper_dir_name(record))
    record = dict(record)
    record["local_dir"] = str(paper_dir)
    record["bib_key"] = bib_key(record)
    record["updated_at"] = now_iso()
    write_json(paper_dir / "metadata.json", record)
    write_text(paper_dir / "citation.bib", render_bibtex(record))
    write_text(paper_dir / "abstract.md", f"# Abstract\n\n{record.get('summary') or ''}")
    pdf_path = paper_dir / "paper.pdf"
    downloaded = False
    errors: list[str] = []
    pdf_url = str(record.get("pdf_url") or "")
    if not args.metadata_only and pdf_url and (args.force or not pdf_path.exists()):
        try:
            data = download_binary(pdf_url)
            if data[:5] != b"%PDF-":
                errors.append(f"Downloaded content is not a PDF: {pdf_url}")
            else:
                pdf_path.write_bytes(data)
                downloaded = True
        except Exception as exc:
            errors.append(f"Download failed from {pdf_url}: {exc}")
    extraction_report = {"downloaded": downloaded, "pdf_url": pdf_url, "errors": errors}
    if pdf_path.exists() and not args.metadata_only:
        extraction_report.update(extract_pdf_assets(pdf_path, paper_dir, record, args.render_dpi))
    write_json(paper_dir / "extraction_report.json", extraction_report)
    record["pdf_path"] = str(pdf_path) if pdf_path.exists() else ""
    record["downloaded"] = bool(pdf_path.exists())
    record["extraction_report"] = str(paper_dir / "extraction_report.json")
    write_json(paper_dir / "metadata.json", record)
    return record


def read_queries(args: argparse.Namespace) -> list[str]:
    queries = list(args.query or [])
    if args.queries_file:
        for line in Path(args.queries_file).read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                queries.append(line)
    if args.vmr_defaults:
        queries.extend(DEFAULT_VMR_QUERIES)
    deduped: list[str] = []
    for query in queries:
        if query not in deduped:
            deduped.append(query)
    return deduped


def run_searches(queries: list[str], sources: list[str], args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    searchers = {
        "cvf": lambda query, limit: cvf_search(query, limit, args.year_min, args.year_max),
        "neurips": lambda query, limit: neurips_search(query, limit, args.year_min, args.year_max),
        "arxiv": arxiv_search,
        "semantic_scholar": semantic_scholar_search,
        "openalex": openalex_search,
    }
    total = len(queries) * len(sources)
    step = 0
    for query in queries:
        for source in sources:
            step += 1
            searcher = searchers[source]
            print(f"[{step}/{total}] {source}: {query}")
            try:
                found = searcher(query, args.max_results)
            except Exception as exc:
                print(f"  failed: {exc}")
                found = []
            print(f"  found: {len(found)}")
            rows.extend(found)
            time.sleep(args.sleep)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a local paper library with PDFs, abstracts, introductions, figures, tables, and BibTeX."
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_LIBRARY_DIR), help="Local download_paper directory.")
    parser.add_argument("--query", action="append", default=[], help="Search query. Repeat for multiple queries.")
    parser.add_argument("--queries-file", default=None, help="Text file with one query per line.")
    parser.add_argument("--from-candidates", action="append", default=[], help="Existing raw_candidates.jsonl files to harvest.")
    parser.add_argument("--vmr-defaults", action="store_true", help="Add default Video Moment Retrieval queries.")
    parser.add_argument(
        "--sources",
        default="cvf,neurips,semantic_scholar,openalex,arxiv",
        help="Comma-separated sources: cvf, neurips, semantic_scholar, openalex, arxiv.",
    )
    parser.add_argument("--max-results", type=int, default=20, help="Max results per query and source.")
    parser.add_argument("--limit-papers", type=int, default=80, help="Max merged papers to materialize.")
    parser.add_argument("--year-min", type=int, default=None, help="Drop papers older than this year.")
    parser.add_argument("--year-max", type=int, default=CURRENT_YEAR, help="Newest proceedings year to scan.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay between online requests.")
    parser.add_argument("--metadata-only", action="store_true", help="Do not download or parse PDFs.")
    parser.add_argument("--force", action="store_true", help="Re-download PDFs and overwrite extraction artifacts.")
    parser.add_argument("--download-sleep", type=float, default=0.2, help="Delay between paper downloads.")
    parser.add_argument("--render-dpi", type=int, default=160, help="DPI for figure/table page snapshots.")
    args = parser.parse_args()

    library_dir = ensure_dir(Path(args.out_dir).expanduser().resolve())
    queries = read_queries(args)
    source_names = [item.strip() for item in args.sources.split(",") if item.strip()]
    allowed = {"cvf", "neurips", "semantic_scholar", "openalex", "arxiv"}
    unknown = [source for source in source_names if source not in allowed]
    if unknown:
        raise SystemExit(f"Unknown sources: {', '.join(unknown)}")
    if not queries and not args.from_candidates:
        raise SystemExit("Provide --query, --queries-file, --vmr-defaults, or --from-candidates.")

    records: list[dict[str, Any]] = []
    for path_value in args.from_candidates:
        records.extend(read_jsonl(Path(path_value).expanduser()))
    if queries:
        records.extend(run_searches(queries, source_names, args))
    if args.year_min is not None:
        records = [row for row in records if not row.get("year") or int(row.get("year")) >= args.year_min]
    merged = sort_records(merge_records(records))[: args.limit_papers]

    print(f"Materializing {len(merged)} merged papers into {library_dir}")
    index_rows = []
    for index, record in enumerate(merged, start=1):
        title = record.get("title") or "(untitled)"
        print(f"[{index}/{len(merged)}] {title}")
        try:
            index_rows.append(write_paper_artifacts(record, library_dir, args))
        except Exception as exc:
            print(f"  failed: {exc}")
        if args.download_sleep > 0:
            time.sleep(args.download_sleep)

    existing_index = read_jsonl(library_dir / "library_index.jsonl")
    write_jsonl(library_dir / "library_index.jsonl", sort_records(merge_records([*existing_index, *index_rows])))
    write_json(
        library_dir / "search_manifest.json",
        {
            "generated_at": now_iso(),
            "queries": queries,
            "sources": source_names,
            "max_results": args.max_results,
            "limit_papers": args.limit_papers,
            "year_min": args.year_min,
            "year_max": args.year_max,
            "paper_count": len(index_rows),
            "library_dir": str(library_dir),
        },
    )
    print(f"Wrote index: {library_dir / 'library_index.jsonl'}")


if __name__ == "__main__":
    main()
