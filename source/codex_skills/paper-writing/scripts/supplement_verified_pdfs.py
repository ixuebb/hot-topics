from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import fitz
import requests


DEFAULT_LIBRARY_DIR = Path(r"D:\syz_autopaper\auto_idea\video moment retrieval\download_paper")
HARVEST_SCRIPT = Path(r"C:\Users\SunYu\.codex\skills\paper-writing\scripts\harvest_literature_library.py")
USER_AGENT = "syz-autopaper/1.0 verified-pdf-supplement"
ATOM = "{http://www.w3.org/2005/Atom}"
S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
OPENALEX_URL = "https://api.openalex.org/works"
CROSSREF_URL = "https://api.crossref.org/works"
UNPAYWALL_URL = "https://api.unpaywall.org/v2"


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "based",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "the",
    "to",
    "towards",
    "using",
    "via",
    "with",
}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def strip_markup(text: str) -> str:
    value = html.unescape(text or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def normalize_title(text: str) -> str:
    value = strip_markup(text).lower()
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def title_tokens(text: str) -> set[str]:
    return {token for token in normalize_title(text).split() if len(token) > 2 and token not in STOPWORDS}


def title_score(expected: str, observed: str) -> float:
    expected_norm = normalize_title(expected)
    observed_norm = normalize_title(observed)
    if not expected_norm or not observed_norm:
        return 0.0
    if expected_norm in observed_norm:
        return 1.0
    seq = SequenceMatcher(None, expected_norm, observed_norm).ratio()
    expected_tokens = title_tokens(expected_norm)
    observed_tokens = title_tokens(observed_norm)
    if not expected_tokens:
        return seq
    shared = len(expected_tokens & observed_tokens)
    overlap = shared / len(expected_tokens)
    union = len(expected_tokens | observed_tokens) or 1
    jaccard = shared / union
    token_score = 0.65 * overlap + 0.35 * jaccard
    if len(expected_tokens) < 5:
        token_score = min(token_score, jaccard + 0.25)
    return max(seq, token_score)


def valid_arxiv_id(arxiv_id: str) -> bool:
    arxiv_id = arxiv_id.strip().removesuffix(".pdf")
    modern = re.match(r"^(\d{2})(\d{2})\.(\d{4,5})(?:v\d+)?$", arxiv_id)
    if modern:
        year = int(modern.group(1))
        month = int(modern.group(2))
        return 7 <= year <= 40 and 1 <= month <= 12
    return bool(re.match(r"^[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?$", arxiv_id))


def arxiv_id_from_url(url: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^/?#]+)", url, re.I)
    return match.group(1).removesuffix(".pdf") if match else ""


def direct_pdf_url_is_plausible(url: str) -> bool:
    if not url:
        return False
    if "arxiv.org" not in url.lower():
        return True
    arxiv_id = arxiv_id_from_url(url)
    return bool(arxiv_id and valid_arxiv_id(arxiv_id))


def request_json(url: str, params: dict[str, Any], timeout: int = 35) -> dict[str, Any]:
    response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def existing_pdf_candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    url = str(record.get("pdf_url") or "")
    if direct_pdf_url_is_plausible(url):
        return [{"source": "direct", "url": url, "candidate_title": record.get("title") or ""}]
    return []


def doi_from_record(record: dict[str, Any]) -> str:
    external = record.get("external_ids") or {}
    doi = str(external.get("DOI") or external.get("doi") or "").strip()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return doi.strip().strip(".")


def doi_pattern_candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    doi = doi_from_record(record)
    if not doi:
        return []
    title = str(record.get("title") or "")
    lower = doi.lower()
    rows: list[dict[str, Any]] = []
    if lower.startswith("10.1007/"):
        rows.append(
            {
                "source": "doi_pattern",
                "url": f"https://link.springer.com/content/pdf/{doi}.pdf",
                "candidate_title": title,
                "doi": doi,
            }
        )
    if lower.startswith("10.1145/"):
        rows.append(
            {
                "source": "doi_pattern",
                "url": f"https://dl.acm.org/doi/pdf/{doi}",
                "candidate_title": title,
                "doi": doi,
            }
        )
    if lower.startswith("10.18653/v1/"):
        anthology_id = doi.split("/", 1)[1].replace("v1/", "")
        rows.append(
            {
                "source": "doi_pattern",
                "url": f"https://aclanthology.org/{anthology_id}.pdf",
                "candidate_title": title,
                "doi": doi,
            }
        )
    if lower.startswith("10.3390/"):
        suffix = doi.split("/", 1)[1]
        rows.append(
            {
                "source": "doi_pattern",
                "url": f"https://www.mdpi.com/{suffix}/pdf",
                "candidate_title": title,
                "doi": doi,
            }
        )
    return rows


def arxiv_candidates(title: str, max_results: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    title_clean = strip_markup(title)
    tokens = [token for token in normalize_title(title_clean).split() if len(token) > 3 and token not in STOPWORDS]
    token_query = " AND ".join(f"ti:{token}" for token in tokens[:8])
    all_token_query = " AND ".join(f"all:{token}" for token in tokens[:8])
    queries = [f'ti:"{title_clean}"']
    if ":" in title_clean:
        prefix = title_clean.split(":", 1)[0].strip()
        if prefix and len(prefix.split()) >= 2:
            queries.append(f'ti:"{prefix}"')
    if token_query:
        queries.append(token_query)
    if all_token_query:
        queries.append(all_token_query)
    queries = list(dict.fromkeys(queries))
    for query in queries:
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
            {"search_query": query, "start": 0, "max_results": max_results, "sortBy": "relevance"}
        )
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=35)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        for entry in root.findall(f"{ATOM}entry"):
            candidate_title = strip_markup(entry.findtext(f"{ATOM}title") or "")
            score = title_score(title, candidate_title)
            if score < 0.78:
                continue
            pdf_url = ""
            for link in entry.findall(f"{ATOM}link"):
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    pdf_url = link.attrib.get("href", "")
                    break
            if not pdf_url:
                arxiv_id = (entry.findtext(f"{ATOM}id") or "").rsplit("/", 1)[-1]
                if arxiv_id and valid_arxiv_id(arxiv_id):
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
            if pdf_url and pdf_url not in seen_urls:
                seen_urls.add(pdf_url)
                rows.append(
                    {
                        "source": "arxiv",
                        "url": pdf_url,
                        "candidate_title": candidate_title,
                        "title_score": round(score, 3),
                    }
                )
        if rows:
            break
    return rows


def semantic_scholar_candidates(title: str, max_results: int) -> list[dict[str, Any]]:
    data = request_json(
        S2_URL,
        {
            "query": strip_markup(title),
            "limit": max_results,
            "fields": "title,year,venue,externalIds,openAccessPdf,url",
        },
    )
    rows: list[dict[str, Any]] = []
    for item in data.get("data", []):
        candidate_title = strip_markup(item.get("title") or "")
        score = title_score(title, candidate_title)
        if score < 0.82:
            continue
        external = item.get("externalIds") or {}
        open_pdf = item.get("openAccessPdf") or {}
        urls = []
        if open_pdf.get("url"):
            urls.append(open_pdf["url"])
        arxiv_id = external.get("ArXiv") or external.get("arxiv")
        if arxiv_id and valid_arxiv_id(str(arxiv_id)):
            urls.append(f"https://arxiv.org/pdf/{arxiv_id}")
        for url in dict.fromkeys(urls):
            rows.append(
                {
                    "source": "semantic_scholar",
                    "url": url,
                    "candidate_title": candidate_title,
                    "title_score": round(score, 3),
                    "year": item.get("year"),
                    "venue": item.get("venue"),
                }
            )
    return rows


def openalex_candidates(title: str, max_results: int) -> list[dict[str, Any]]:
    data = request_json(OPENALEX_URL, {"search": strip_markup(title), "per-page": max_results})
    rows: list[dict[str, Any]] = []
    for item in data.get("results", []):
        candidate_title = strip_markup(item.get("display_name") or "")
        score = title_score(title, candidate_title)
        if score < 0.86:
            continue
        urls: list[str] = []
        for location in [item.get("primary_location"), item.get("best_oa_location"), *(item.get("locations") or [])]:
            if not location:
                continue
            pdf_url = location.get("pdf_url") or ""
            if direct_pdf_url_is_plausible(pdf_url):
                urls.append(pdf_url)
        for url in dict.fromkeys(urls):
            rows.append(
                {
                    "source": "openalex",
                    "url": url,
                    "candidate_title": candidate_title,
                    "title_score": round(score, 3),
                    "year": item.get("publication_year"),
                }
            )
    return rows


def crossref_candidates(record: dict[str, Any], max_results: int) -> list[dict[str, Any]]:
    doi = doi_from_record(record)
    title = str(record.get("title") or "")
    items: list[dict[str, Any]] = []
    if doi:
        data = request_json(f"{CROSSREF_URL}/{urllib.parse.quote(doi, safe='')}", {})
        message = data.get("message") or {}
        items = [message]
    else:
        data = request_json(
            CROSSREF_URL,
            {
                "query.title": strip_markup(title),
                "rows": max_results,
                "select": "title,issued,link,DOI,container-title",
            },
        )
        items = data.get("message", {}).get("items", [])

    rows: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in items:
        titles = item.get("title") or []
        candidate_title = strip_markup(titles[0] if titles else title)
        score = title_score(title, candidate_title)
        if score < 0.82:
            continue
        for link in item.get("link") or []:
            url = str(link.get("URL") or "")
            if not url:
                continue
            urls = [url]
            if "link.springer.com/content/pdf/" in url and not url.lower().endswith(".pdf"):
                urls.append(f"{url}.pdf")
            for candidate_url in urls:
                if candidate_url in seen_urls:
                    continue
                seen_urls.add(candidate_url)
                rows.append(
                    {
                        "source": "crossref",
                        "url": candidate_url,
                        "candidate_title": candidate_title,
                        "title_score": round(score, 3),
                        "doi": item.get("DOI") or doi,
                    }
                )
    return rows


def unpaywall_candidates(record: dict[str, Any], email_address: str) -> list[dict[str, Any]]:
    doi = doi_from_record(record)
    if not doi or not email_address:
        return []
    data = request_json(
        f"{UNPAYWALL_URL}/{urllib.parse.quote(doi, safe='')}",
        {"email": email_address},
    )
    title = str(record.get("title") or "")
    rows: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for location in [data.get("best_oa_location"), *(data.get("oa_locations") or [])]:
        if not location:
            continue
        url = str(location.get("url_for_pdf") or "")
        if not url:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        rows.append(
            {
                "source": "unpaywall",
                "url": url,
                "candidate_title": title,
                "doi": doi,
                "host_type": location.get("host_type"),
                "license": location.get("license"),
            }
        )
    return rows


def get_pdf_bytes(url: str, max_bytes: int) -> bytes:
    with requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*;q=0.8"},
        timeout=(8, 45),
        stream=True,
        allow_redirects=True,
    ) as response:
        response.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=1024 * 128):
            if not chunk:
                continue
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"PDF exceeds max bytes: {total} > {max_bytes}")
        data = b"".join(chunks)
    if not data.startswith(b"%PDF"):
        raise ValueError("Downloaded content is not a PDF")
    return data


def verify_pdf(data: bytes, expected_title: str, min_score: float) -> dict[str, Any]:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        page_texts = []
        for page_index in range(min(3, doc.page_count)):
            page_texts.append(doc.load_page(page_index).get_text("text"))
        first_pages = strip_markup("\n".join(page_texts))
        score = title_score(expected_title, first_pages[:8000])
        return {
            "ok": score >= min_score,
            "page_count": doc.page_count,
            "title_score": round(score, 3),
            "matched_text_preview": first_pages[:500],
        }
    finally:
        doc.close()


def load_harvest_module() -> Any:
    spec = importlib.util.spec_from_file_location("harvest_literature_library", HARVEST_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {HARVEST_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def extract_after_download(harvest: Any, pdf_path: Path, paper_dir: Path, record: dict[str, Any], render_dpi: int) -> dict[str, Any]:
    try:
        return harvest.extract_pdf_assets(pdf_path, paper_dir, record, render_dpi)
    except Exception as exc:
        return {"errors": [f"post-download extraction failed: {exc}"]}


def candidate_stream(
    record: dict[str, Any],
    sources: set[str],
    max_results: int,
    extra_candidates: list[dict[str, Any]] | None = None,
    unpaywall_email: str = "",
) -> Iterable[dict[str, Any]]:
    title = str(record.get("title") or "")
    seen: set[str] = set()
    for row in extra_candidates or []:
        url = row.get("url") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        yield row
    source_functions = [
        ("direct", lambda: existing_pdf_candidates(record)),
        ("doi_pattern", lambda: doi_pattern_candidates(record)),
        ("arxiv", lambda: arxiv_candidates(title, max_results)),
        ("semantic_scholar", lambda: semantic_scholar_candidates(title, max_results)),
        ("crossref", lambda: crossref_candidates(record, max_results)),
        ("unpaywall", lambda: unpaywall_candidates(record, unpaywall_email)),
        ("openalex", lambda: openalex_candidates(title, max_results)),
    ]
    for name, fn in source_functions:
        if name not in sources:
            continue
        try:
            rows = fn()
        except Exception as exc:
            yield {"source": name, "error": f"candidate lookup failed: {exc}"}
            continue
        for row in rows:
            url = row.get("url") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            yield row


def process_paper(
    paper_dir: Path,
    args: argparse.Namespace,
    harvest: Any | None,
    extra_candidates_by_dir: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    meta_path = paper_dir / "metadata.json"
    if not meta_path.exists():
        return {"dir": paper_dir.name, "status": "missing_metadata"}
    record = json.loads(meta_path.read_text(encoding="utf-8"))
    title = strip_markup(str(record.get("title") or ""))
    row: dict[str, Any] = {
        "dir": paper_dir.name,
        "title": title,
        "year": record.get("year"),
        "status": "not_found",
        "attempts": [],
    }
    pdf_path = paper_dir / "paper.pdf"
    if pdf_path.exists() and not args.force:
        row["status"] = "already_has_pdf"
        return row

    for candidate in candidate_stream(
        record,
        set(args.sources.split(",")),
        args.max_results,
        (extra_candidates_by_dir or {}).get(paper_dir.name, []),
        args.unpaywall_email,
    ):
        attempt = dict(candidate)
        row["attempts"].append(attempt)
        if candidate.get("error"):
            if "429" in str(candidate.get("error")):
                row["status"] = "rate_limited"
                row["rate_limited_source"] = candidate.get("source")
                if args.rate_limit_sleep > 0:
                    time.sleep(args.rate_limit_sleep)
                if args.stop_on_rate_limit:
                    return row
            continue
        url = str(candidate.get("url") or "")
        try:
            data = get_pdf_bytes(url, args.max_bytes)
            verification = verify_pdf(data, title, args.min_title_score)
            attempt["verification"] = verification
            if not verification.get("ok"):
                attempt["error"] = "title verification failed"
                continue
            if not args.dry_run:
                tmp_path = paper_dir / "paper.pdf.tmp"
                tmp_path.write_bytes(data)
                tmp_path.replace(pdf_path)
                record["pdf_url"] = url
                record["pdf_path"] = str(pdf_path)
                record["downloaded"] = True
                record["pdf_resolution"] = {
                    "source": candidate.get("source"),
                    "candidate_title": candidate.get("candidate_title"),
                    "title_score": verification.get("title_score"),
                    "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                write_json(meta_path, record)
                extraction_report = {
                    "downloaded": True,
                    "pdf_url": url,
                    "verified": verification,
                    "errors": [],
                }
                if harvest is not None:
                    extraction_report.update(extract_after_download(harvest, pdf_path, paper_dir, record, args.render_dpi))
                write_json(paper_dir / "extraction_report.json", extraction_report)
            row.update(
                {
                    "status": "downloaded" if not args.dry_run else "verified_dry_run",
                    "pdf_url": url,
                    "source": candidate.get("source"),
                    "verification": verification,
                }
            )
            return row
        except Exception as exc:
            attempt["error"] = str(exc)
            continue
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve, verify, and supplement missing PDFs in a local literature library.")
    parser.add_argument("--library-dir", default=str(DEFAULT_LIBRARY_DIR))
    parser.add_argument("--sources", default="direct,doi_pattern,arxiv,semantic_scholar,crossref,openalex")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Skip directories already present in the report file.")
    parser.add_argument("--restart-report", action="store_true", help="Delete the existing report file before running.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-extraction", action="store_true")
    parser.add_argument("--render-dpi", type=int, default=160)
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--max-bytes", type=int, default=120 * 1024 * 1024)
    parser.add_argument("--min-title-score", type=float, default=0.78)
    parser.add_argument("--sleep", type=float, default=0.6)
    parser.add_argument("--rate-limit-sleep", type=float, default=30.0)
    parser.add_argument("--stop-on-rate-limit", action="store_true", help="Stop the run after the first 429-style lookup error.")
    parser.add_argument("--url-candidates", action="append", default=[], help="JSONL rows with dir/url/source/candidate_title to try before online lookup.")
    parser.add_argument("--unpaywall-email", default="", help="Real contact email required by the Unpaywall API when using --sources unpaywall.")
    parser.add_argument("--report-name", default="pdf_supplement_report.jsonl")
    args = parser.parse_args()

    library_dir = Path(args.library_dir)
    report_path = library_dir.parent / args.report_name
    if report_path.exists() and args.restart_report:
        report_path.unlink()
    reported_dirs: set[str] = set()
    if args.resume and report_path.exists():
        for line in report_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("dir"):
                reported_dirs.add(str(row["dir"]))

    paper_dirs = [path for path in sorted(library_dir.iterdir()) if path.is_dir()]
    paper_dirs = [path for path in paper_dirs if args.force or not (path / "paper.pdf").exists()]
    if reported_dirs:
        paper_dirs = [path for path in paper_dirs if path.name not in reported_dirs]
    if args.only:
        needles = [item.lower() for item in args.only]
        paper_dirs = [path for path in paper_dirs if any(needle in path.name.lower() for needle in needles)]
    if args.limit:
        paper_dirs = paper_dirs[: args.limit]

    extra_candidates_by_dir: dict[str, list[dict[str, Any]]] = {}
    for candidate_path in args.url_candidates:
        for line in Path(candidate_path).read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.lstrip("\ufeff")
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("dir") and row.get("url"):
                row.setdefault("source", "manual_url")
                extra_candidates_by_dir.setdefault(str(row["dir"]), []).append(row)

    harvest = None if args.skip_extraction or args.dry_run else load_harvest_module()
    summary = {
        "processed": 0,
        "downloaded": 0,
        "verified_dry_run": 0,
        "not_found": 0,
        "rate_limited": 0,
        "already_has_pdf": 0,
        "missing_metadata": 0,
    }
    for index, paper_dir in enumerate(paper_dirs, start=1):
        print(f"[{index}/{len(paper_dirs)}] {paper_dir.name}", flush=True)
        row = process_paper(paper_dir, args, harvest, extra_candidates_by_dir)
        summary["processed"] += 1
        summary[row.get("status", "not_found")] = summary.get(row.get("status", "not_found"), 0) + 1
        append_jsonl(report_path, row)
        print(f"  -> {row.get('status')} {row.get('source') or ''} {row.get('pdf_url') or ''}", flush=True)
        if row.get("status") == "rate_limited" and args.stop_on_rate_limit:
            print(f"Stopping after rate limit from {row.get('rate_limited_source')}", flush=True)
            break
        if args.sleep > 0:
            time.sleep(args.sleep)
    write_json(library_dir.parent / "pdf_supplement_summary.json", summary | {"report": str(report_path)})
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
