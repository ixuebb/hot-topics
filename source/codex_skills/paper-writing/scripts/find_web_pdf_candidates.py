from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests


DEFAULT_LIBRARY_DIR = Path(r"D:\syz_autopaper\auto_idea\video moment retrieval\download_paper")
USER_AGENT = "Mozilla/5.0 (compatible; syz-autopaper/1.0; +local-literature-library)"
TRUSTED_PAGE_DOMAINS = {
    "openaccess.thecvf.com",
    "aclanthology.org",
    "ojs.aaai.org",
    "proceedings.neurips.cc",
    "amazon.science",
    "liqiangnie.github.io",
}
PDF_HINTS = (".pdf", "arxiv.org/abs/", "arxiv.org/pdf/", "openaccess.thecvf.com/content/")
DOMAIN_TERMS = re.compile(
    r"video moment retrieval|moment retrieval|video grounding|moment localization|temporal grounding|natural language moment|spatio-temporal grounding",
    re.I,
)


def strip_markup(text: str) -> str:
    value = html.unescape(text or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def domain(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc.lower().removeprefix("www.")


def decode_ddg_url(url: str) -> str:
    value = html.unescape(url)
    if value.startswith("//duckduckgo.com/l/?"):
        value = "https:" + value
    parsed = urllib.parse.urlparse(value)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        query = urllib.parse.parse_qs(parsed.query)
        return query.get("uddg", [value])[0]
    return value


def direct_pdf_candidate(url: str) -> str:
    lower = url.lower()
    if "arxiv.org/abs/" in lower:
        arxiv_id = url.rstrip("/").rsplit("/", 1)[-1]
        return f"https://arxiv.org/pdf/{arxiv_id}"
    if "openaccess.thecvf.com/content/" in lower and "/html/" in lower and lower.endswith(".html"):
        return url.replace("/html/", "/papers/").removesuffix(".html") + ".pdf"
    if ".pdf" in lower:
        return url
    return ""


def fetch(url: str, timeout: int = 25) -> requests.Response:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response


def scrape_pdf_links(url: str) -> list[str]:
    if domain(url) not in TRUSTED_PAGE_DOMAINS:
        return []
    try:
        text = fetch(url).text
    except Exception:
        return []
    urls: list[str] = []
    meta_match = re.search(r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']', text, re.I)
    if meta_match:
        urls.append(urllib.parse.urljoin(url, html.unescape(meta_match.group(1))))
    for href in re.findall(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', text, re.I):
        urls.append(urllib.parse.urljoin(url, html.unescape(href)))
    return list(dict.fromkeys(urls))


def search_urls(title: str, max_results: int) -> list[str]:
    query = f'"{title}" PDF'
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    text = fetch(url).text
    urls: list[str] = []
    for match in re.finditer(r'class="result__a"\s+href="([^"]+)"', text, re.I):
        result_url = decode_ddg_url(match.group(1))
        if any(hint in result_url.lower() for hint in PDF_HINTS) or domain(result_url) in TRUSTED_PAGE_DOMAINS:
            urls.append(result_url)
        if len(urls) >= max_results:
            break
    return list(dict.fromkeys(urls))


def read_missing_records(library_dir: Path, limit: int | None) -> list[tuple[Path, dict[str, Any]]]:
    rows: list[tuple[Path, dict[str, Any]]] = []
    for paper_dir in sorted(path for path in library_dir.iterdir() if path.is_dir()):
        if (paper_dir / "paper.pdf").exists():
            continue
        meta_path = paper_dir / "metadata.json"
        if not meta_path.exists():
            continue
        try:
            record = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        haystack = " ".join(str(record.get(key) or "") for key in ["title", "summary", "venue"])
        if not DOMAIN_TERMS.search(haystack):
            continue
        rows.append((paper_dir, record))
        if limit and len(rows) >= limit:
            break
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Find web PDF candidates for missing local literature PDFs.")
    parser.add_argument("--library-dir", default=str(DEFAULT_LIBRARY_DIR))
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--max-results", type=int, default=8)
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    library_dir = Path(args.library_dir)
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for paper_dir, record in read_missing_records(library_dir, args.limit):
        title = strip_markup(str(record.get("title") or ""))
        found_urls: list[str] = []
        try:
            found_urls = search_urls(title, args.max_results)
        except Exception:
            found_urls = []
        for found_url in found_urls:
            pdf_urls = [direct_pdf_candidate(found_url)] if direct_pdf_candidate(found_url) else []
            pdf_urls.extend(scrape_pdf_links(found_url))
            for pdf_url in pdf_urls:
                if not pdf_url:
                    continue
                key = (paper_dir.name, pdf_url)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    {
                        "dir": paper_dir.name,
                        "title": title,
                        "source": "web_search",
                        "url": pdf_url,
                        "candidate_title": title,
                        "found_from": found_url,
                    }
                )
        if args.sleep > 0:
            time.sleep(args.sleep)

    out_path = Path(args.out)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in candidates:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"candidates": len(candidates), "out": str(out_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
