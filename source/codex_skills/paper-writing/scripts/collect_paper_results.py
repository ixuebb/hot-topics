from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from workflow_common import ensure_dir, now_iso, project_path, read_json, write_json


SKIP_JSON_NAMES = {"paper_numbers.json", "figure_manifest.json", "compile_report.json", "gate_report.json"}
DIGIT_WORDS = {
    "0": "Zero",
    "1": "One",
    "2": "Two",
    "3": "Three",
    "4": "Four",
    "5": "Five",
    "6": "Six",
    "7": "Seven",
    "8": "Eight",
    "9": "Nine",
}


def macro_case(text: str) -> str:
    parts = re.findall(r"[A-Za-z]+|[0-9]+", str(text))
    if not parts:
        return "Metric"
    converted: list[str] = []
    for part in parts:
        if part.isdigit():
            converted.append("".join(DIGIT_WORDS[digit] for digit in part))
        else:
            converted.append(part[:1].upper() + part[1:])
    value = "".join(converted)
    return value


def safe_macro_name(*parts: Any) -> str:
    value = "".join(macro_case(str(part)) for part in parts if str(part).strip())
    return value or "PaperMetric"


def numeric_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return float(value)
        return None
    text = str(value).strip()
    if not text or text in {"??", "NaN", "nan", "None"}:
        return None
    try:
        val = float(text)
        return val if math.isfinite(val) else None
    except ValueError:
        return None


def format_metric(value: float, digits: int = 2) -> str:
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if value != 0 and abs(value) < 0.01:
        return f"{value:.2e}"
    return f"{value:.{digits}f}"


def walk_results(obj: Any, source: Path, inherited: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    inherited = dict(inherited or {})
    rows: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        local = dict(inherited)
        for key in ["experiment_id", "experiment", "dataset", "method", "metric", "seed", "split", "status"]:
            if key in obj and obj[key] not in (None, ""):
                local[key] = obj[key]
        if any(key in obj for key in ["value", "mean", "score", "result"]):
            row = dict(local)
            row.update(obj)
            row["_source_file"] = str(source)
            rows.append(row)
        for key in ["results", "metrics", "rows", "records", "summary"]:
            if key in obj:
                rows.extend(walk_results(obj[key], source, local))
        if "by_dataset" in obj and isinstance(obj["by_dataset"], dict):
            for dataset, payload in obj["by_dataset"].items():
                child = dict(local)
                child["dataset"] = dataset
                rows.extend(walk_results(payload, source, child))
        if "by_method" in obj and isinstance(obj["by_method"], dict):
            for method, payload in obj["by_method"].items():
                child = dict(local)
                child["method"] = method
                rows.extend(walk_results(payload, source, child))
    elif isinstance(obj, list):
        for item in obj:
            rows.extend(walk_results(item, source, inherited))
    return rows


def load_result_rows(project_dir: Path) -> list[dict[str, Any]]:
    candidates: list[Path] = []
    root_result = project_dir / "experiments" / "results.json"
    if root_result.exists():
        candidates.append(root_result)
    results_dir = project_dir / "experiments" / "results"
    if results_dir.exists():
        candidates.extend(path for path in sorted(results_dir.rglob("*.json")) if path.name not in SKIP_JSON_NAMES)
    rows: list[dict[str, Any]] = []
    for path in candidates:
        try:
            rows.extend(walk_results(json.loads(path.read_text(encoding="utf-8-sig")), path))
        except Exception as exc:
            rows.append({"_source_file": str(path), "status": "read_error", "error": str(exc)})
    return rows


def result_value(row: dict[str, Any]) -> float | None:
    for key in ["value", "mean", "score", "result"]:
        val = numeric_value(row.get(key))
        if val is not None:
            return val
    return None


def row_macro(row: dict[str, Any]) -> str:
    if row.get("macro"):
        return safe_macro_name(str(row["macro"]))
    exp = row.get("experiment_id") or row.get("experiment") or ""
    dataset = row.get("dataset") or ""
    method = row.get("method") or ""
    metric = row.get("metric") or ""
    return safe_macro_name(exp, dataset, method, metric)


def normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def plan_matches_row(plan: dict[str, Any], row: dict[str, Any]) -> bool:
    for key in ["experiment_id", "dataset", "metric", "method"]:
        plan_value = str(plan.get(key, "")).strip()
        if not plan_value:
            continue
        row_value = str(row.get(key, "")).strip()
        if not row_value:
            return False
        if normalized_key(plan_value) != normalized_key(row_value):
            return False
    return True


def build_macro_records(registry: dict[str, Any], rows: list[dict[str, Any]], digits: int) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = result_value(row)
        macro = row_macro(row)
        if not macro:
            continue
        existing = records.get(macro)
        source = row.get("_source_file")
        record = {
            "macro": macro,
            "value": value,
            "display": format_metric(value, digits) if value is not None else "??",
            "filled": value is not None,
            "source_file": source,
            "row": row,
            "status": row.get("status") or ("filled" if value is not None else "missing_value"),
        }
        if existing is None or (not existing["filled"] and record["filled"]):
            records[macro] = record

    for plan in registry.get("macro_plan", []) if isinstance(registry, dict) else []:
        macro = safe_macro_name(str(plan.get("macro") or "")) if plan.get("macro") else ""
        if not macro:
            macro = safe_macro_name(plan.get("experiment_id", ""), plan.get("dataset", ""), plan.get("method", ""), plan.get("metric", ""))
        if macro in records and records[macro]["filled"]:
            records[macro]["plan"] = plan
            continue
        best_row = None
        for row in rows:
            if plan_matches_row(plan, row) and result_value(row) is not None:
                best_row = row
                break
        if best_row is not None:
            value = result_value(best_row)
            records[macro] = {
                "macro": macro,
                "value": value,
                "display": format_metric(value, digits) if value is not None else "??",
                "filled": value is not None,
                "source_file": best_row.get("_source_file"),
                "row": best_row,
                "plan": plan,
                "status": "matched_from_plan",
            }
        else:
            records.setdefault(
                macro,
                {
                    "macro": macro,
                    "value": None,
                    "display": "??",
                    "filled": False,
                    "source_file": None,
                    "row": None,
                    "plan": plan,
                    "status": plan.get("status", "planned"),
                },
            )
    return sorted(records.values(), key=lambda item: item["macro"])


def write_tex(path: Path, records: list[dict[str, Any]]) -> None:
    lines = [
        "% Auto-generated by paper-writing/scripts/collect_paper_results.py",
        "% Do not edit by hand. Source metadata lives in experiments/paper_numbers.json.",
        f"% Generated: {now_iso()}",
        "",
    ]
    for record in records:
        macro = record["macro"]
        display = record["display"]
        status = record.get("status", "")
        source = record.get("source_file") or "no source file"
        lines.append(f"% {macro}: {status}; source={source}")
        lines.append(f"\\providecommand{{\\{macro}}}{{??}}\\renewcommand{{\\{macro}}}{{{display}}}")
    lines.append("")
    ensure_dir(path.parent)
    path.write_text("\n".join(lines), encoding="utf-8")


def patch_main(project_dir: Path, rel_output: str) -> bool:
    main = project_dir / "main.tex"
    if not main.exists():
        return False
    text = main.read_text(encoding="utf-8", errors="ignore")
    if "results_numbers.tex" in text or rel_output.replace("\\", "/") in text.replace("\\", "/"):
        return False
    include = f"\\IfFileExists{{{rel_output}}}{{\\input{{{rel_output}}}}}{{}}\n"
    marker = "\\begin{document}"
    if marker in text:
        text = text.replace(marker, include + "\n" + marker, 1)
    else:
        text = include + text
    main.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect real experiment numbers into LaTeX macros.")
    parser.add_argument("project_dir")
    parser.add_argument("--output", default="results_numbers.tex")
    parser.add_argument("--digits", type=int, default=2)
    parser.add_argument("--patch-main", action="store_true", help="Insert an \\IfFileExists input hook into main.tex if missing.")
    args = parser.parse_args()

    project_dir = project_path(args.project_dir)
    registry = read_json(project_dir / "experiments" / "registry.json", default={}) or {}
    rows = load_result_rows(project_dir)
    records = build_macro_records(registry, rows, args.digits)
    output_path = project_dir / args.output
    write_tex(output_path, records)
    audit = {
        "generated_at": now_iso(),
        "source_rows": len(rows),
        "macro_count": len(records),
        "filled_count": sum(1 for item in records if item.get("filled")),
        "placeholder_count": sum(1 for item in records if not item.get("filled")),
        "output_tex": str(output_path),
        "records": records,
    }
    write_json(project_dir / "experiments" / "paper_numbers.json", audit)
    patched = patch_main(project_dir, args.output) if args.patch_main else False
    print(f"Wrote {output_path}")
    print(f"Wrote {project_dir / 'experiments' / 'paper_numbers.json'}")
    print(f"Macros: {audit['macro_count']} filled={audit['filled_count']} placeholders={audit['placeholder_count']}")
    if patched:
        print("Patched main.tex with results_numbers.tex input hook.")


if __name__ == "__main__":
    main()
