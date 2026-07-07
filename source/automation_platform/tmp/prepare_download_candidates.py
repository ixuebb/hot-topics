from __future__ import annotations

import json
import argparse
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


DEFAULT_SCAN_PATH = Path(r"D:\自动化论文平台\tmp\title_phrase_scan\scan_results.json")
DEFAULT_OUT_DIR = Path(r"D:\自动化论文平台\tmp\title_phrase_scan")
UA = "codex-paper-library-prep/1.0"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


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


def chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def inverted_to_text(value: dict[str, list[int]] | None) -> str:
    if not value:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indices in value.items():
        for index in indices:
            positions.append((index, word))
    return " ".join(word for _, word in sorted(positions))


def clean_arxiv_id(value: str) -> str:
    match = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?", value or "")
    return match.group(1) if match else ""


def arxiv_pdf(value: str) -> str:
    arxiv_id = clean_arxiv_id(value)
    return f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else ""


def openalex_short(value: str) -> str:
    match = re.search(r"(W\d+)", value or "")
    return match.group(1) if match else ""


def split_authors(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*;\s*Proceedings.*$", "", text)
    return [item.strip() for item in text.split(",") if item.strip()]


def first_pdf_link(soup: BeautifulSoup, base_url: str) -> str:
    for link in soup.find_all("a"):
        href = link.get("href") or ""
        label = link.get_text(" ", strip=True).lower()
        if href.lower().endswith(".pdf") and ("paper" in href.lower() or label == "pdf" or "paper" in label):
            return urllib.parse.urljoin(base_url, href)
    for link in soup.find_all("a"):
        href = link.get("href") or ""
        if href.lower().endswith(".pdf"):
            return urllib.parse.urljoin(base_url, href)
    return ""


def fetch_openalex(ids: list[str], failures: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    ids = sorted({openalex_short(item) for item in ids if openalex_short(item)})
    for batch in chunks(ids, 50):
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
            {"filter": "openalex:" + "|".join(batch), "per-page": str(len(batch))}
        )
        try:
            data = get(url, timeout=45).json()
        except Exception as exc:
            failures.append(f"openalex batch {batch[:3]}...: {exc}")
            continue
        for item in data.get("results") or []:
            short = openalex_short(item.get("id") or "")
            primary = item.get("primary_location") or {}
            source = primary.get("source") or {}
            doi = (item.get("doi") or "").replace("https://doi.org/", "")
            out[short] = {
                "title": item.get("display_name") or "",
                "authors": [
                    ((auth.get("author") or {}).get("display_name")) or ""
                    for auth in item.get("authorships") or []
                ],
                "summary": inverted_to_text(item.get("abstract_inverted_index")),
                "year": item.get("publication_year"),
                "published": item.get("publication_date"),
                "venue": source.get("display_name") or "",
                "url": item.get("doi") or item.get("id") or primary.get("landing_page_url") or "",
                "pdf_url": primary.get("pdf_url") or "",
                "citation_count": item.get("cited_by_count"),
                "external_ids": {"doi": doi, "openalex": item.get("id")},
            }
        time.sleep(0.3)
    return out


def fetch_arxiv(ids: list[str], failures: list[str]) -> dict[str, dict[str, Any]]:
    ids = sorted({clean_arxiv_id(item) for item in ids if clean_arxiv_id(item)})
    out: dict[str, dict[str, Any]] = {}
    for batch in chunks(ids, 50):
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"id_list": ",".join(batch), "max_results": len(batch)})
        try:
            root = ET.fromstring(get(url, timeout=70).content)
        except Exception as exc:
            failures.append(f"arxiv batch {batch[:3]}...: {exc}")
            continue
        for entry in root.findall(f"{ATOM}entry"):
            entry_id = clean_arxiv_id(entry.findtext(f"{ATOM}id") or "")
            pdf_url = ""
            for link in entry.findall(f"{ATOM}link"):
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    pdf_url = link.attrib.get("href", "")
            out[entry_id] = {
                "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
                "authors": [author.findtext(f"{ATOM}name") or "" for author in entry.findall(f"{ATOM}author")],
                "summary": " ".join((entry.findtext(f"{ATOM}summary") or "").split()),
                "published": entry.findtext(f"{ATOM}published") or "",
                "updated": entry.findtext(f"{ATOM}updated") or "",
                "year": int((entry.findtext(f"{ATOM}published") or "0000")[:4] or 0),
                "url": entry.findtext(f"{ATOM}id") or "",
                "pdf_url": pdf_url or arxiv_pdf(entry_id),
                "venue": "arXiv",
                "external_ids": {"arxiv": entry_id, "doi": entry.findtext(f"{ARXIV}doi") or ""},
            }
        time.sleep(3.0)
    return out


def official_enrich(record: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    out = dict(record)
    external = dict(out.get("external_ids") or {})
    url = external.get("official_url") or out.get("url") or ""
    if not url:
        return out
    try:
        if "openaccess.thecvf.com" in url:
            soup = BeautifulSoup(get(url, timeout=60).text, "html.parser")
            title = soup.select_one("#papertitle")
            authors = soup.select_one("#authors")
            abstract = soup.select_one("#abstract")
            if title:
                out["title"] = title.get_text(" ", strip=True)
            if authors:
                out["authors"] = split_authors(authors.get_text(" ", strip=True))
            if abstract:
                out["summary"] = abstract.get_text(" ", strip=True)
            pdf_url = first_pdf_link(soup, url)
            if pdf_url:
                out["pdf_url"] = pdf_url
            external["official_source"] = "cvf"
        elif "proceedings.neurips.cc" in url and "Abstract" in url:
            soup = BeautifulSoup(get(url, timeout=60).text, "html.parser")
            title = soup.find("h1")
            paragraphs = soup.find_all("p")
            if title:
                out["title"] = title.get_text(" ", strip=True)
            if paragraphs:
                out["authors"] = split_authors(paragraphs[0].get_text(" ", strip=True))
            abstract_header = soup.find(lambda tag: tag.name in {"h2", "h3"} and tag.get_text(" ", strip=True).lower() == "abstract")
            if abstract_header:
                abstract = abstract_header.find_next("p")
                if abstract:
                    out["summary"] = abstract.get_text(" ", strip=True)
            pdf_url = first_pdf_link(soup, url)
            if pdf_url:
                out["pdf_url"] = pdf_url
            external["official_source"] = "neurips"
    except Exception as exc:
        failures.append(f"official {url}: {exc}")
    out["external_ids"] = external
    return out


def merge_missing(base: dict[str, Any], incoming: dict[str, Any], prefer_pdf: bool = False) -> dict[str, Any]:
    out = dict(base)
    for key in ["title", "year", "published", "venue", "url", "citation_count"]:
        if incoming.get(key) and not out.get(key):
            out[key] = incoming[key]
    if incoming.get("authors") and not out.get("authors"):
        out["authors"] = incoming["authors"]
    if incoming.get("summary") and len(str(incoming["summary"])) > len(str(out.get("summary") or "")):
        out["summary"] = incoming["summary"]
    if incoming.get("pdf_url") and (prefer_pdf or not out.get("pdf_url")):
        out["pdf_url"] = incoming["pdf_url"]
    out.setdefault("external_ids", {})
    for key, value in (incoming.get("external_ids") or {}).items():
        if value and not out["external_ids"].get(key):
            out["external_ids"][key] = value
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare enriched download candidates from a title-phrase scan.")
    parser.add_argument("--scan-path", default=str(DEFAULT_SCAN_PATH))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()
    scan_path = Path(args.scan_path)
    out_dir = Path(args.out_dir)
    out_jsonl = out_dir / "download_candidates.jsonl"
    out_report = out_dir / "download_candidates_report.json"

    data = json.loads(scan_path.read_text(encoding="utf-8"))
    records = data["records"]
    failures: list[str] = []
    openalex_ids = [((row.get("external_ids") or {}).get("openalex") or "") for row in records]
    arxiv_ids = [((row.get("external_ids") or {}).get("arxiv") or "") for row in records]
    arxiv_ids.extend((row.get("pdf_url") or "") for row in records)
    arxiv_ids.extend(((row.get("external_ids") or {}).get("doi") or "") for row in records)

    print(f"records={len(records)} openalex_ids={sum(bool(openalex_short(x)) for x in openalex_ids)} arxiv_ids={sum(bool(clean_arxiv_id(x)) for x in arxiv_ids)}")
    openalex = fetch_openalex(openalex_ids, failures)
    arxiv = fetch_arxiv(arxiv_ids, failures)
    print(f"openalex_fetched={len(openalex)} arxiv_fetched={len(arxiv)}")

    candidates: list[dict[str, Any]] = []
    for row in records:
        candidate = dict(row)
        candidate.setdefault("source", (candidate.get("sources") or ["scan"])[0])
        candidate.setdefault("query", "; ".join(candidate.get("phrases") or []))
        candidate.setdefault("queries", candidate.get("phrases") or [])
        candidate.setdefault("acceptance_status", "accepted" if candidate.get("venue") and "arxiv" not in str(candidate.get("venue")).lower() else "preprint")
        candidate.setdefault("authors", [])
        candidate.setdefault("summary", "")
        external = dict(candidate.get("external_ids") or {})
        short = openalex_short(external.get("openalex") or "")
        if short and short in openalex:
            candidate = merge_missing(candidate, openalex[short])
        arxiv_id = clean_arxiv_id(external.get("arxiv") or candidate.get("pdf_url") or external.get("doi") or "")
        if arxiv_id and arxiv_id in arxiv:
            candidate = merge_missing(candidate, arxiv[arxiv_id], prefer_pdf=not candidate.get("pdf_url"))
        if set(candidate.get("sources") or []) & {"cvf", "neurips"}:
            before_pdf = candidate.get("pdf_url") or ""
            candidate = official_enrich(candidate, failures)
            if before_pdf and "openaccess.thecvf.com" not in str(candidate.get("pdf_url")) and "proceedings.neurips.cc" not in str(candidate.get("pdf_url")):
                candidate["fallback_pdf_url"] = before_pdf
        if not candidate.get("pdf_url"):
            pdf = arxiv_pdf(external.get("arxiv") or external.get("doi") or candidate.get("url") or "")
            if pdf:
                candidate["pdf_url"] = pdf
        candidates.append(candidate)

    candidates.sort(key=lambda row: (int(row.get("year") or 0), row.get("title") or ""), reverse=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for row in candidates:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    report = {
        "input_records": len(records),
        "candidates": len(candidates),
        "with_pdf_url": sum(bool(row.get("pdf_url")) for row in candidates),
        "with_authors": sum(bool(row.get("authors")) for row in candidates),
        "with_summary": sum(bool(row.get("summary")) for row in candidates),
        "official_pdf_urls": sum(
            "openaccess.thecvf.com" in str(row.get("pdf_url") or "") or "proceedings.neurips.cc" in str(row.get("pdf_url") or "")
            for row in candidates
        ),
        "failures": failures,
    }
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Wrote {out_jsonl}")


if __name__ == "__main__":
    main()
