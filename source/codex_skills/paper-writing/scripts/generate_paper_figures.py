from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from workflow_common import ensure_dir, now_iso, project_path, write_json


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                obj["_source_file"] = str(path)
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def get_interval(row: dict[str, Any], prefix: str) -> tuple[float, float] | None:
    candidates = [
        (f"{prefix}_start", f"{prefix}_end"),
        (f"{prefix}Start", f"{prefix}End"),
        (f"{prefix}_s", f"{prefix}_e"),
    ]
    for a, b in candidates:
        start = as_float(row.get(a))
        end = as_float(row.get(b))
        if start is not None and end is not None and end >= start:
            return start, end
    for key in [prefix, f"{prefix}_moment", f"{prefix}_interval", f"{prefix}_span"]:
        value = row.get(key)
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            start = as_float(value[0])
            end = as_float(value[1])
            if start is not None and end is not None and end >= start:
                return start, end
    return None


def collect_prediction_rows(project_dir: Path) -> list[dict[str, Any]]:
    results_dir = project_dir / "experiments" / "results"
    paths = []
    if results_dir.exists():
        paths.extend(sorted(results_dir.rglob("*pred*.jsonl")))
        paths.extend(sorted(results_dir.rglob("*case*.jsonl")))
    rows: list[dict[str, Any]] = []
    for path in paths:
        for row in read_jsonl(path):
            gt = get_interval(row, "gt") or get_interval(row, "target") or get_interval(row, "gold")
            pred = get_interval(row, "pred") or get_interval(row, "prediction")
            if gt and pred:
                row["_gt"] = gt
                row["_pred"] = pred
                rows.append(row)
    return rows


def collect_history(project_dir: Path) -> list[dict[str, Any]]:
    results_dir = project_dir / "experiments" / "results"
    rows: list[dict[str, Any]] = []
    if not results_dir.exists():
        return rows
    for path in sorted(results_dir.rglob("*history*.jsonl")) + sorted(results_dir.rglob("*curve*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def safe_label(text: Any, limit: int = 70) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def plot_timeline_cases(rows: list[dict[str, Any]], out_path: Path, max_cases: int) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    selected = rows[:max_cases]
    fig_h = max(2.6, 1.0 + 0.78 * len(selected))
    fig, axes = plt.subplots(len(selected), 1, figsize=(7.0, fig_h), squeeze=False)
    for idx, row in enumerate(selected):
        ax = axes[idx, 0]
        gt_start, gt_end = row["_gt"]
        pred_start, pred_end = row["_pred"]
        duration = as_float(row.get("duration")) or max(gt_end, pred_end, 1.0)
        ax.set_xlim(0, duration)
        ax.set_ylim(0, 1)
        ax.broken_barh([(gt_start, gt_end - gt_start)], (0.58, 0.22), facecolors="#2f6f73", label="GT" if idx == 0 else None)
        ax.broken_barh([(pred_start, pred_end - pred_start)], (0.20, 0.22), facecolors="#c44e52", label="Pred" if idx == 0 else None)
        query = safe_label(row.get("query") or row.get("sentence") or row.get("caption") or row.get("video_id"))
        ax.set_title(query, fontsize=8, loc="left")
        ax.set_yticks([])
        ax.set_xlabel("time")
        ax.grid(axis="x", alpha=0.25)
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
    if selected:
        axes[0, 0].legend(loc="upper right", frameon=False, ncols=2)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return {"path": str(out_path), "type": "timeline_cases", "cases": len(selected), "source_files": sorted({row.get("_source_file", "") for row in selected})}


def plot_boundary_hist(rows: list[dict[str, Any]], out_path: Path) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    start_err = [row["_pred"][0] - row["_gt"][0] for row in rows]
    end_err = [row["_pred"][1] - row["_gt"][1] for row in rows]
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    ax.hist(start_err, bins=20, alpha=0.65, label="start error", color="#4c78a8")
    ax.hist(end_err, bins=20, alpha=0.65, label="end error", color="#f58518")
    ax.axvline(0, color="black", linewidth=0.9)
    ax.set_xlabel("prediction minus ground truth")
    ax.set_ylabel("count")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return {"path": str(out_path), "type": "boundary_error_hist", "rows": len(rows), "source_files": sorted({row.get("_source_file", "") for row in rows})}


def plot_metric_history(rows: list[dict[str, Any]], out_path: Path) -> dict[str, Any] | None:
    usable = []
    for row in rows:
        step = as_float(row.get("step") or row.get("epoch"))
        value = as_float(row.get("value") or row.get("mean") or row.get("score"))
        metric = row.get("metric")
        method = row.get("method") or row.get("run") or row.get("experiment_id")
        if step is not None and value is not None and metric and method:
            usable.append((str(metric), str(method), step, value, row))
    if not usable:
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    metric = usable[0][0]
    filtered = [item for item in usable if item[0] == metric]
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    for method in sorted({item[1] for item in filtered}):
        pairs = sorted((step, value) for _, m, step, value, _ in filtered if m == method)
        if not pairs:
            continue
        xs, ys = zip(*pairs)
        ax.plot(xs, ys, marker="o", linewidth=1.5, markersize=3, label=method)
    ax.set_xlabel("step" if any("step" in item[4] for item in filtered) else "epoch")
    ax.set_ylabel(metric)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return {"path": str(out_path), "type": "metric_history", "metric": metric, "rows": len(filtered), "source_files": sorted({item[4].get("_source_file", "") for item in filtered})}


def write_plan(project_dir: Path, reason: str) -> Path:
    path = project_dir / "figures" / "figure_plan.md"
    lines = [
        "# Figure Plan",
        "",
        f"Generated: {now_iso()}",
        "",
        f"Status: {reason}",
        "",
        "Expected data-driven figures:",
        "",
        "- timeline_cases.pdf from experiments/results/*pred*.jsonl or *case*.jsonl with gt/pred intervals.",
        "- boundary_error_hist.pdf from the same prediction files.",
        "- metric_history.pdf from experiments/results/*history*.jsonl or *curve*.jsonl.",
        "",
        "No figure should imply a result before the corresponding source file exists.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate paper-quality figures from real experiment artifacts.")
    parser.add_argument("project_dir")
    parser.add_argument("--max-cases", type=int, default=6)
    args = parser.parse_args()

    project_dir = project_path(args.project_dir)
    figures_dir = ensure_dir(project_dir / "figures")
    manifest: dict[str, Any] = {"generated_at": now_iso(), "figures": [], "status": "ready"}

    try:
        import matplotlib  # noqa: F401
    except Exception as exc:
        plan = write_plan(project_dir, f"matplotlib unavailable: {exc}")
        manifest["status"] = "blocked"
        manifest["figure_plan"] = str(plan)
        write_json(figures_dir / "figure_manifest.json", manifest)
        print(f"Wrote {figures_dir / 'figure_manifest.json'}")
        return

    prediction_rows = collect_prediction_rows(project_dir)
    if prediction_rows:
        manifest["figures"].append(plot_timeline_cases(prediction_rows, figures_dir / "timeline_cases.pdf", args.max_cases))
        manifest["figures"].append(plot_boundary_hist(prediction_rows, figures_dir / "boundary_error_hist.pdf"))

    history_rows = collect_history(project_dir)
    history_record = plot_metric_history(history_rows, figures_dir / "metric_history.pdf")
    if history_record:
        manifest["figures"].append(history_record)

    if not manifest["figures"]:
        plan = write_plan(project_dir, "no prediction or history artifacts found yet")
        manifest["status"] = "planned"
        manifest["figure_plan"] = str(plan)

    write_json(figures_dir / "figure_manifest.json", manifest)
    print(f"Wrote {figures_dir / 'figure_manifest.json'}")
    for item in manifest["figures"]:
        print(f"Generated {item['path']}")


if __name__ == "__main__":
    main()
