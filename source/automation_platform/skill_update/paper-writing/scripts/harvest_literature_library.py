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


DEFAULT_LIBRARY_DIR = Path(r"D:\syz_autopaper\auto_idea\video moment retrieval\download_paper")
USER_AGENT = "codex-paper-writing-literature-library/1.0"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


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
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


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


def identity_key(record: dict[str, Any]) -> str:
    external = record.get("external_ids") or {}
    doi = str(external.get("DOI") or external.get("doi") or "").lower().strip()
    if doi:
        return f"doi:{doi}"
    arxiv_id = str(external.get("ArXiv") or external.get("arxiv") or record.get("source_id") or "").lower().strip()
    if record.get("source") == "arxiv" and arxiv_id:
        return f"arxiv:{arxiv_id}"
    title_key = canonical_title(str(record.get("title") or ""))
    return f"title:{title_key}" if title_key else f"unknown:{sha1_short(json.dumps(record, sort_keys=True))}"


def merge_record(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key in ["title", "url", "pdf_url", "published", "venue", "acceptance_status"]:
        if not merged.get(key) and incoming.get(key):
            merged[key] = incoming[key]
    if len(str(incoming.get("summary") or "")) > len(str(merged.get("summary") or "")):
        merged["summary"] = incoming.get("summary") or ""
    if incoming.get("year") and (not merged.get("year") or int(incoming["year"]) > int(merged["year"])):
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
    by_key: dict[str, dict[str, Any]] = {}
    for record in records:
        key = identity_key(record)
        if key in by_key:
            by_key[key] = merge_record(by_key[key], record)
        else:
            by_key[key] = record
    return list(by_key.values())


def sort_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda row: (
            int(row.get("year") or 0),
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
        default="semantic_scholar,openalex,arxiv",
        help="Comma-separated sources: semantic_scholar, openalex, arxiv.",
    )
    parser.add_argument("--max-results", type=int, default=20, help="Max results per query and source.")
    parser.add_argument("--limit-papers", type=int, default=80, help="Max merged papers to materialize.")
    parser.add_argument("--year-min", type=int, default=None, help="Drop papers older than this year.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay between online requests.")
    parser.add_argument("--metadata-only", action="store_true", help="Do not download or parse PDFs.")
    parser.add_argument("--force", action="store_true", help="Re-download PDFs and overwrite extraction artifacts.")
    parser.add_argument("--render-dpi", type=int, default=160, help="DPI for figure/table page snapshots.")
    args = parser.parse_args()

    library_dir = ensure_dir(Path(args.out_dir).expanduser().resolve())
    queries = read_queries(args)
    source_names = [item.strip() for item in args.sources.split(",") if item.strip()]
    allowed = {"semantic_scholar", "openalex", "arxiv"}
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

    existing_index = read_jsonl(library_dir / "library_index.jsonl")
    by_key = {identity_key(row): row for row in existing_index}
    for row in index_rows:
        by_key[identity_key(row)] = row
    write_jsonl(library_dir / "library_index.jsonl", sort_records(list(by_key.values())))
    write_json(
        library_dir / "search_manifest.json",
        {
            "generated_at": now_iso(),
            "queries": queries,
            "sources": source_names,
            "max_results": args.max_results,
            "limit_papers": args.limit_papers,
            "year_min": args.year_min,
            "paper_count": len(index_rows),
            "library_dir": str(library_dir),
        },
    )
    print(f"Wrote index: {library_dir / 'library_index.jsonl'}")


if __name__ == "__main__":
    main()
