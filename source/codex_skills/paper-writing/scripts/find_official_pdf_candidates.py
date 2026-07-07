from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.parse
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests


DEFAULT_LIBRARY_DIR = Path(r"D:\syz_autopaper\auto_idea\video moment retrieval\download_paper")
USER_AGENT = "syz-autopaper/1.0 official-pdf-candidate-finder"
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


def strip_markup(text: str) -> str:
    value = html.unescape(text or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def normalize_title(text: str) -> str:
    value = strip_markup(text).lower()
    value = value.replace("é", "e").replace("´", "").replace("`", "")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def title_tokens(text: str) -> set[str]:
    return {token for token in normalize_title(text).split() if len(token) > 2 and token not in STOPWORDS}


def title_score(expected: str, observed: str) -> float:
    expected_norm = normalize_title(expected)
    observed_norm = normalize_title(observed)
    if not expected_norm or not observed_norm:
        return 0.0
    if expected_norm in observed_norm or observed_norm in expected_norm:
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


def read_missing_records(library_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
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
        rows.append((paper_dir, record))
    return rows


def fetch_text(url: str, timeout: int = 35) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.text


def cvf_index_urls(years: list[int], include_workshops: bool) -> list[str]:
    urls: list[str] = []
    for year in years:
        for venue in ["CVPR", "ICCV", "WACV"]:
            urls.append(f"https://openaccess.thecvf.com/{venue}{year}?day=all")
            if include_workshops:
                urls.append(f"https://openaccess.thecvf.com/{venue}{year}_workshops/menu")
    return urls


def discover_cvf_workshop_urls(menu_html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    for href, _text in re.findall(r'<a\s+href="([^"]+)">([^<]+)</a>', menu_html, re.I):
        if "_workshops/" not in href:
            continue
        urls.append(urllib.parse.urljoin(base_url, href))
    return urls


def cvf_pdf_from_html_url(page_url: str) -> str:
    if "/html/" in page_url and page_url.endswith(".html"):
        return page_url.replace("/html/", "/papers/").removesuffix(".html") + ".pdf"
    return page_url


def parse_cvf_papers(index_html: str, index_url: str) -> list[dict[str, str]]:
    papers: list[dict[str, str]] = []
    pattern = re.compile(r'<dt class="ptitle">.*?<a href="([^"]+)">(.*?)</a>.*?</dt>', re.I | re.S)
    for href, title_html in pattern.findall(index_html):
        title = strip_markup(title_html)
        page_url = urllib.parse.urljoin(index_url, href)
        pdf_url = cvf_pdf_from_html_url(page_url)
        if title and pdf_url.endswith(".pdf"):
            papers.append({"title": title, "url": pdf_url, "page_url": page_url})
    return papers


def collect_cvf_papers(years: list[int], sleep: float, include_workshops: bool) -> list[dict[str, str]]:
    papers: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    queue = cvf_index_urls(years, include_workshops)
    seen_pages: set[str] = set()
    while queue:
        url = queue.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        try:
            text = fetch_text(url)
        except Exception:
            continue
        if url.endswith("/menu"):
            queue.extend(discover_cvf_workshop_urls(text, url))
        for paper in parse_cvf_papers(text, url):
            if paper["url"] in seen_urls:
                continue
            seen_urls.add(paper["url"])
            papers.append(paper)
        if sleep > 0:
            time.sleep(sleep)
    return papers


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Find official PDF candidates for missing local library PDFs.")
    parser.add_argument("--library-dir", default=str(DEFAULT_LIBRARY_DIR))
    parser.add_argument("--out", required=True)
    parser.add_argument("--source", choices=["cvf"], default="cvf")
    parser.add_argument("--years", default="2021,2022,2023,2024,2025,2026")
    parser.add_argument("--include-workshops", action="store_true")
    parser.add_argument("--min-score", type=float, default=0.92)
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    library_dir = Path(args.library_dir)
    missing_records = read_missing_records(library_dir)
    years = [int(item) for item in args.years.split(",") if item.strip()]
    official_papers = collect_cvf_papers(years, args.sleep, args.include_workshops)
    official_tokens = [title_tokens(paper["title"]) for paper in official_papers]
    token_index: dict[str, set[int]] = defaultdict(set)
    for index, tokens in enumerate(official_tokens):
        for token in tokens:
            token_index[token].add(index)

    rows: list[dict[str, Any]] = []
    for paper_dir, record in missing_records:
        title = str(record.get("title") or "")
        query_tokens = title_tokens(title)
        candidate_indexes: set[int] = set()
        for token in query_tokens:
            candidate_indexes.update(token_index.get(token, set()))
        if not candidate_indexes:
            continue
        best: tuple[float, dict[str, str]] | None = None
        for paper_index in candidate_indexes:
            official = official_papers[paper_index]
            score = title_score(title, official["title"])
            if score >= args.min_score and (best is None or score > best[0]):
                best = (score, official)
        if not best:
            continue
        score, official = best
        rows.append(
            {
                "dir": paper_dir.name,
                "title": title,
                "source": "cvf_index",
                "url": official["url"],
                "candidate_title": official["title"],
                "title_score": round(score, 3),
                "official_page": official["page_url"],
            }
        )

    out_path = Path(args.out)
    write_jsonl(out_path, rows)
    print(
        json.dumps(
            {
                "missing_records": len(missing_records),
                "official_papers": len(official_papers),
                "candidates": len(rows),
                "out": str(out_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
