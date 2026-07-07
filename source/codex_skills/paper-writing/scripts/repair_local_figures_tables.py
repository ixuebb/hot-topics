from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import fitz
from PIL import Image, ImageOps


FIGURE_RE = re.compile(r"^\s*(?:Fig\.?|Figure)\s*([0-9]+[A-Za-z]?)\s*[\.:]", re.I)
TABLE_RE = re.compile(r"^\s*Table\s*([0-9]+[A-Za-z]?)\s*[\.:]", re.I)


@dataclass
class Caption:
    kind: str
    number: str
    page_index: int
    bbox: fitz.Rect
    text: str


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def remove_old_tables(paper_dir: Path) -> int:
    removed = 0
    old = paper_dir / "tables" / "extracted"
    if not old.exists():
        return 0
    for pattern in ("*.md", "*.csv"):
        for path in old.glob(pattern):
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def sanitize_text(text: Any) -> str:
    value = "" if text is None else str(text)
    value = value.encode("utf-8", "replace").decode("utf-8", "replace")
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", value)
    return normalize_space(value)


def sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {sanitize_text(key): sanitize_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_json(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(sanitize_json(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def union_rect(rects: Iterable[fitz.Rect]) -> fitz.Rect:
    iterator = iter(rects)
    rect = fitz.Rect(next(iterator))
    for item in iterator:
        rect |= fitz.Rect(item)
    return rect


def line_text(line: dict[str, Any]) -> str:
    return normalize_space("".join(span.get("text", "") for span in line.get("spans", [])))


def collect_captions(page: fitz.Page, page_index: int) -> list[Caption]:
    captions: list[Caption] = []
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        lines = block.get("lines", [])
        for line_index, line in enumerate(lines):
            text = line_text(line)
            match = FIGURE_RE.search(text) or TABLE_RE.search(text)
            if not match:
                continue
            kind = "figure" if FIGURE_RE.search(text) else "table"
            rects = [fitz.Rect(line.get("bbox"))]
            tail_parts = [text]
            # Captions often continue for one or two following lines in the same block.
            for follow in lines[line_index + 1 : line_index + 4]:
                follow_text = line_text(follow)
                if not follow_text or FIGURE_RE.search(follow_text) or TABLE_RE.search(follow_text):
                    break
                if len(follow_text) > 160 and kind == "figure":
                    break
                rects.append(fitz.Rect(follow.get("bbox")))
                tail_parts.append(follow_text)
            captions.append(
                Caption(
                    kind=kind,
                    number=match.group(1),
                    page_index=page_index,
                    bbox=union_rect(rects),
                    text=normalize_space(" ".join(tail_parts)),
                )
            )
    return captions


def page_pixmap(page: fitz.Page, dpi: int) -> tuple[Image.Image, float]:
    scale = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    mode = "RGB" if pix.n < 4 else "RGBA"
    image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image, scale


def rect_to_px(rect: fitz.Rect, scale: float, image: Image.Image, pad: int = 0) -> tuple[int, int, int, int]:
    x0 = max(0, int(math.floor(rect.x0 * scale)) - pad)
    y0 = max(0, int(math.floor(rect.y0 * scale)) - pad)
    x1 = min(image.width, int(math.ceil(rect.x1 * scale)) + pad)
    y1 = min(image.height, int(math.ceil(rect.y1 * scale)) + pad)
    return x0, y0, x1, y1


def nonwhite_mask(image: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(image)
    return gray.point(lambda value: 255 if value < 245 else 0)


def row_bands(mask: Image.Image, min_density: float = 0.012, max_gap: int = 28) -> list[tuple[int, int, int]]:
    width, height = mask.size
    pixels = mask.load()
    active: list[int] = []
    threshold = max(8, int(width * min_density))
    for y in range(height):
        count = 0
        for x in range(width):
            if pixels[x, y]:
                count += 1
        if count >= threshold:
            active.append(y)
    if not active:
        return []
    bands: list[tuple[int, int, int]] = []
    start = prev = active[0]
    ink = 1
    for y in active[1:]:
        if y - prev <= max_gap:
            ink += 1
            prev = y
        else:
            bands.append((start, prev, ink))
            start = prev = y
            ink = 1
    bands.append((start, prev, ink))
    return bands


def column_bounds(mask: Image.Image, y0: int, y1: int, min_count: int = 3) -> tuple[int, int] | None:
    width, _ = mask.size
    pixels = mask.load()
    active: list[int] = []
    for x in range(width):
        count = 0
        for y in range(max(0, y0), min(mask.height, y1)):
            if pixels[x, y]:
                count += 1
        if count >= min_count:
            active.append(x)
    if not active:
        return None
    return min(active), max(active)


def figure_crop_boxes(page: fitz.Page, image: Image.Image, scale: float, caption: Caption) -> tuple[tuple[int, int, int, int] | None, tuple[int, int, int, int] | None, dict[str, Any]]:
    caption_px = rect_to_px(caption.bbox, scale, image, pad=6)
    _, cy0, _, cy1 = caption_px
    search_top = 0
    search_bottom = max(0, cy0 - 3)
    if search_bottom <= 40:
        return None, None, {"reason": "caption too close to page top"}

    # Avoid selecting the title/abstract area for very early captions.
    if cy0 > image.height * 0.45:
        search_top = int(image.height * 0.08)
    region = image.crop((0, search_top, image.width, search_bottom))
    mask = nonwhite_mask(region)
    bands = row_bands(mask, min_density=0.012, max_gap=max(18, int(image.height * 0.01)))
    min_height = max(45, int(image.height * 0.035))
    viable = [(s, e, ink) for s, e, ink in bands if e - s + 1 >= min_height]
    if not viable:
        viable = bands
    if not viable:
        return None, None, {"reason": "no visual band above caption"}

    # Pick the nearest substantial band above caption, then merge adjacent nearby bands
    # so multi-panel figures and flowcharts stay whole.
    chosen_index = max(range(len(viable)), key=lambda idx: (viable[idx][1], viable[idx][2]))
    start, end, ink = viable[chosen_index]
    merge_gap = max(45, int(image.height * 0.025))
    i = chosen_index - 1
    while i >= 0:
        ps, pe, pink = viable[i]
        if start - pe <= merge_gap and (pe - ps + 1 >= min_height or pink > min_height):
            start = ps
            ink += pink
            i -= 1
        else:
            break
    y0 = max(0, search_top + start - 12)
    y1 = min(image.height, search_top + end + 12)
    mask_full = nonwhite_mask(image)
    x_bounds = column_bounds(mask_full, y0, y1, min_count=max(3, int((y1 - y0) * 0.006)))
    if x_bounds is None:
        return None, None, {"reason": "no x bounds"}
    x0, x1 = x_bounds
    pad_x = max(20, int(image.width * 0.025))
    x0 = max(0, x0 - pad_x)
    x1 = min(image.width, x1 + pad_x)

    # Discard tiny icon/frame-like crops.
    crop_w = x1 - x0
    crop_h = y1 - y0
    if crop_w < image.width * 0.22 or crop_h < image.height * 0.05:
        return None, None, {"reason": "crop too small", "crop_size": [crop_w, crop_h]}

    body_box = (x0, y0, x1, y1)
    with_caption_box = (
        x0,
        y0,
        x1,
        min(image.height, max(y1, cy1 + 8)),
    )
    return body_box, with_caption_box, {"caption": caption.text, "crop_size": [crop_w, crop_h]}


def save_crop(image: Image.Image, box: tuple[int, int, int, int], path: Path) -> None:
    ensure_dir(path.parent)
    crop = image.crop(box)
    crop.save(path)


def raw_cell(value: Any) -> str:
    value = "" if value is None else str(value)
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def clean_cell(value: Any) -> str:
    value = raw_cell(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def expand_multiline_rows(rows: list[list[Any]]) -> list[list[str]]:
    expanded: list[list[str]] = []
    for row in rows:
        raw = [raw_cell(cell) for cell in row]
        split = [[normalize_space(part) for part in cell.split("\n") if normalize_space(part)] for cell in raw]
        max_lines = max((len(parts) for parts in split), default=0)
        multiline_cells = sum(len(parts) > 1 for parts in split)
        if max_lines > 1 and multiline_cells >= 2:
            for line_index in range(max_lines):
                expanded.append([parts[line_index] if line_index < len(parts) else "" for parts in split])
        else:
            expanded.append([clean_cell(cell) for cell in raw])
    return expanded


def normalize_rows(rows: list[list[Any]]) -> list[list[str]]:
    cleaned = expand_multiline_rows([row for row in rows if row])
    cleaned = [row for row in cleaned if any(cell for cell in row)]
    if not cleaned:
        return []
    width = max(len(row) for row in cleaned)
    cleaned = [row + [""] * (width - len(row)) for row in cleaned]
    # Drop empty columns.
    keep = [idx for idx in range(width) if any(row[idx] for row in cleaned)]
    return [[row[idx] for idx in keep] for row in cleaned]


def table_quality(rows: list[list[str]]) -> tuple[bool, bool, list[str]]:
    reasons: list[str] = []
    if len(rows) < 2:
        return False, True, ["fewer than two nonempty rows"]
    width = max(len(row) for row in rows)
    if width < 2:
        return False, True, ["fewer than two columns"]
    cells = [cell for row in rows for cell in row]
    nonempty = sum(bool(cell) for cell in cells)
    ratio = nonempty / max(1, len(cells))
    if ratio < 0.35:
        reasons.append("too many empty cells")
    row_fill = [sum(bool(cell) for cell in row) for row in rows]
    if sum(1 for count in row_fill if count <= 1) > len(rows) * 0.45:
        reasons.append("too many one-cell rows")
    long_first_col = sum(1 for row in rows if row and len(row[0]) > 80 and sum(bool(cell) for cell in row[1:]) == 0)
    if long_first_col > 0:
        reasons.append("paragraph-like rows")
    if nonempty < 4:
        reasons.append("not enough data cells")
    header = rows[0]
    if any(not cell for cell in header):
        reasons.append("blank header cells")
    packed_numeric_cells = 0
    for row in rows[1:]:
        for cell in row:
            if len(re.findall(r"[-+]?\d+(?:\.\d+)?%?", cell)) >= 3:
                packed_numeric_cells += 1
    if packed_numeric_cells:
        reasons.append("multiple numeric values packed into one cell")
    needs_review = bool(reasons)
    valid = "paragraph-like rows" not in reasons and nonempty >= 4 and width >= 2 and ratio >= 0.25
    return valid, needs_review, reasons


def markdown_table(rows: list[list[str]]) -> str:
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    header = rows[0]
    body = rows[1:]

    def align(col: int) -> str:
        values = [row[col] for row in body if col < len(row) and row[col]]
        if values and sum(bool(re.search(r"[-+]?\d", value)) for value in values) >= max(1, len(values) // 2):
            return "---:"
        return "---"

    def line(row: list[str]) -> str:
        return "| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |"

    return "\n".join([line(header), line([align(i) for i in range(width)]), *[line(row) for row in body]])


def nearest_caption(captions: list[Caption], table_bbox: fitz.Rect, max_distance: float = 90.0) -> Caption | None:
    best: tuple[float, Caption] | None = None
    for caption in captions:
        if caption.kind != "table":
            continue
        # In these ML proceedings tables almost always use a caption above the
        # tabular body. If the nearest "Table" caption is below a detected bbox,
        # the bbox is often a figure/diagram above the caption.
        if caption.bbox.y0 > table_bbox.y0:
            continue
        distance = abs(caption.bbox.y1 - table_bbox.y0)
        horizontal_overlap = max(0.0, min(caption.bbox.x1, table_bbox.x1) - max(caption.bbox.x0, table_bbox.x0))
        if distance <= max_distance and horizontal_overlap > min(caption.bbox.width, table_bbox.width) * 0.25:
            if best is None or distance < best[0]:
                best = (distance, caption)
    return best[1] if best else None


def process_figures(doc: fitz.Document, paper_dir: Path, dpi: int, report: dict[str, Any]) -> None:
    out_dir = paper_dir / "figures" / "extracted_clean"
    clean_dir(out_dir)
    figure_count = 0
    skipped: list[dict[str, Any]] = []
    for page_index, page in enumerate(doc):
        captions = [cap for cap in collect_captions(page, page_index) if cap.kind == "figure"]
        if not captions:
            continue
        image, scale = page_pixmap(page, dpi)
        for caption in captions:
            body_box, with_caption_box, info = figure_crop_boxes(page, image, scale, caption)
            if body_box is None or with_caption_box is None:
                skipped.append({"page": page_index + 1, "caption": caption.text, **info})
                continue
            figure_count += 1
            stem = f"figure_{figure_count:03d}_page_{page_index + 1:03d}"
            save_crop(image, body_box, out_dir / f"{stem}.png")
            save_crop(image, with_caption_box, out_dir / f"{stem}_with_caption.png")
            (out_dir / f"{stem}.txt").write_text(caption.text + "\n", encoding="utf-8")
    report["figures_clean"] = figure_count
    report["figures_skipped"] = skipped


def process_tables(doc: fitz.Document, paper_dir: Path, dpi: int, report: dict[str, Any]) -> None:
    remove_old_tables(paper_dir)
    table_dir = paper_dir / "tables" / "extracted_clean"
    crop_dir = paper_dir / "tables" / "crops_clean"
    clean_dir(table_dir)
    clean_dir(crop_dir)
    table_count = 0
    skipped: list[dict[str, Any]] = []
    needs_review: list[dict[str, Any]] = []
    for page_index, page in enumerate(doc):
        captions = collect_captions(page, page_index)
        try:
            finder = page.find_tables()
        except Exception as exc:
            skipped.append({"page": page_index + 1, "reason": f"find_tables failed: {exc}"})
            continue
        if not finder or not finder.tables:
            continue
        image, scale = page_pixmap(page, dpi)
        for table in finder.tables:
            rows = normalize_rows(table.extract())
            valid, review, reasons = table_quality(rows)
            bbox = fitz.Rect(table.bbox)
            caption = nearest_caption(captions, bbox)
            if not caption:
                skipped.append({"page": page_index + 1, "bbox": list(bbox), "reasons": [*reasons, "no nearby table caption"]})
                continue
            if not valid:
                skipped.append({"page": page_index + 1, "bbox": list(bbox), "reasons": reasons})
                continue
            table_count += 1
            stem = f"table_{table_count:03d}_page_{page_index + 1:03d}"
            crop_rect = fitz.Rect(bbox)
            if caption:
                crop_rect |= caption.bbox
            crop_box = rect_to_px(crop_rect, scale, image, pad=12)
            save_crop(image, crop_box, crop_dir / f"{stem}.png")
            (table_dir / f"{stem}.md").write_text(markdown_table(rows) + "\n", encoding="utf-8")
            with (table_dir / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerows(rows)
            if caption:
                (table_dir / f"{stem}.caption.txt").write_text(caption.text + "\n", encoding="utf-8")
            if review:
                needs_review.append(
                    {
                        "table": stem,
                        "page": page_index + 1,
                        "caption": caption.text if caption else "",
                        "reasons": sorted(set(reasons)),
                    }
                )
    report["tables_clean"] = table_count
    report["tables_skipped"] = skipped
    report["tables_needs_review"] = needs_review


def process_paper(paper_dir: Path, dpi: int) -> dict[str, Any]:
    report: dict[str, Any] = {
        "paper_dir": str(paper_dir),
        "status": "ok",
        "figures_clean": 0,
        "tables_clean": 0,
    }
    pdf_path = paper_dir / "paper.pdf"
    if not pdf_path.exists():
        report["status"] = "missing_pdf"
        write_json(paper_dir / "repair_report.json", report)
        return report
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        report["status"] = "pdf_open_failed"
        report["error"] = str(exc)
        write_json(paper_dir / "repair_report.json", report)
        return report
    try:
        process_figures(doc, paper_dir, dpi, report)
        process_tables(doc, paper_dir, dpi, report)
    finally:
        doc.close()
    write_json(paper_dir / "repair_report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair already-downloaded paper figure/table extraction without downloading anything.")
    parser.add_argument("--library-dir", default=r"D:\syz_autopaper\auto_idea\video moment retrieval\download_paper")
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", action="append", default=[], help="Process paper dirs whose folder name contains this substring.")
    parser.add_argument("--skip-completed", action="store_true", help="Skip dirs with an existing repair_report.json status of ok or missing_pdf.")
    args = parser.parse_args()

    library_dir = Path(args.library_dir)
    paper_dirs = [path for path in sorted(library_dir.iterdir()) if path.is_dir()]
    if args.skip_completed:
        pending = []
        for path in paper_dirs:
            report_path = path / "repair_report.json"
            if report_path.exists():
                try:
                    status = json.loads(report_path.read_text(encoding="utf-8")).get("status")
                except Exception:
                    status = None
                if status in {"ok", "missing_pdf"}:
                    continue
            pending.append(path)
        paper_dirs = pending
    if args.only:
        needles = [item.lower() for item in args.only]
        paper_dirs = [path for path in paper_dirs if any(needle in path.name.lower() for needle in needles)]
    if args.limit is not None:
        paper_dirs = paper_dirs[: args.limit]

    reports = []
    for index, paper_dir in enumerate(paper_dirs, start=1):
        print(f"[{index}/{len(paper_dirs)}] {paper_dir.name}", flush=True)
        reports.append(process_paper(paper_dir, args.dpi))

    summary = {
        "library_dir": str(library_dir),
        "processed_dirs": len(reports),
        "missing_pdf": sum(row.get("status") == "missing_pdf" for row in reports),
        "figures_clean": sum(int(row.get("figures_clean") or 0) for row in reports),
        "tables_clean": sum(int(row.get("tables_clean") or 0) for row in reports),
        "tables_needs_review": sum(len(row.get("tables_needs_review") or []) for row in reports),
        "reports": reports,
    }
    write_json(library_dir / "repair_summary.json", summary)
    print(json.dumps(sanitize_json({key: summary[key] for key in ["processed_dirs", "missing_pdf", "figures_clean", "tables_clean", "tables_needs_review"]}), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
