from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from workflow_common import ensure_dir, now_iso, project_path, read_json, read_state, write_json, write_state


def detect_domain(state: dict[str, Any], requested: str | None) -> str:
    if requested:
        return requested
    project = state.get("project", {})
    text = " ".join(str(project.get(key, "")) for key in ["title", "topic", "scope", "angle", "audience"]).lower()
    if any(term in text for term in ["video moment", "temporal video grounding", "natural language video localization", "vmr"]):
        return "vmr"
    return "generic"


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


def slugify_macro(text: str) -> str:
    parts = re.findall(r"[A-Za-z]+|[0-9]+", text)
    if not parts:
        return "Metric"
    converted: list[str] = []
    for part in parts:
        if part.isdigit():
            converted.append("".join(DIGIT_WORDS[digit] for digit in part))
        else:
            converted.append(part[:1].upper() + part[1:])
    return "".join(converted)


def vmr_registry(slug: str, remote_base: str) -> dict[str, Any]:
    datasets = ["Charades-STA", "ActivityNet Captions", "TACoS", "QVHighlights"]
    baselines = ["Moment-DETR", "QD-DETR", "UniVTG", "EaTR", "CG-DETR", "TR-DETR"]
    metrics = ["R@1 IoU=0.3", "R@1 IoU=0.5", "R@1 IoU=0.7", "mIoU", "mAP"]
    remote_dir = f"{remote_base.rstrip('/')}/{slug}"
    return {
        "version": 1,
        "generated_at": now_iso(),
        "domain": "vmr",
        "remote": {
            "base_dir": remote_dir,
            "results_dir": f"{remote_dir}/experiments/results",
            "logs_dir": f"{remote_dir}/experiments/logs",
            "figures_dir": f"{remote_dir}/figures",
            "notes": "Keep all remote data, code, checkpoints, and logs under the data disk path.",
        },
        "macro_plan": [
            {
                "macro": f"{slugify_macro(dataset)}{slugify_macro(metric)}",
                "experiment_id": "E1",
                "dataset": dataset,
                "metric": metric,
                "method": "OURS",
                "status": "planned",
                "description": f"OURS on {dataset}, {metric}",
            }
            for dataset in datasets[:3]
            for metric in ["R@1 IoU=0.5", "R@1 IoU=0.7", "mIoU"]
        ],
        "experiments": [
            {
                "id": "E1",
                "name": "Main VMR comparison",
                "status": "planned",
                "claim": "The proposed method improves calibrated temporal localization on standard VMR benchmarks.",
                "purpose": "Compare the proposed method against strong supervised VMR baselines under the same feature/backbone protocol.",
                "datasets": datasets[:3],
                "baselines": baselines,
                "metrics": metrics[:4],
                "controls": ["same video features", "same train/val/test splits", "same evaluation script", "three seeds when feasible"],
                "commands": [
                    f"cd {remote_dir}",
                    "python -m experiments.run_vmr --exp E1 --dataset charades_sta --method ours --seed 0",
                    "python -m experiments.run_vmr --exp E1 --dataset activitynet_captions --method ours --seed 0",
                    "python -m experiments.run_vmr --exp E1 --dataset tacos --method ours --seed 0",
                    "python scripts/evaluate_vmr.py --exp E1 --write-json experiments/results/E1_metrics.json",
                ],
                "expected_outputs": [
                    "experiments/results/E1_metrics.json",
                    "experiments/logs/E1_*.log",
                    "tables/main_results.tex",
                ],
                "paper_targets": ["Main results table", "Experiments section", "Abstract only after real results exist"],
            },
            {
                "id": "E2",
                "name": "Component ablation",
                "status": "planned",
                "claim": "Each proposed component contributes separately to localization or calibration.",
                "purpose": "Remove event decomposition, distributional targets, ambiguity-aware negatives, and calibration at inference.",
                "datasets": ["Charades-STA", "ActivityNet Captions"],
                "baselines": ["OURS full", "no event decomposition", "deterministic boundary target", "no ambiguity negatives", "uncalibrated inference"],
                "metrics": ["R@1 IoU=0.5", "R@1 IoU=0.7", "mIoU", "ECE or calibration error"],
                "controls": ["same seed grid as E1", "same checkpoint budget", "same evaluation script"],
                "commands": [
                    f"cd {remote_dir}",
                    "python -m experiments.run_vmr --exp E2 --ablation no_event --seed 0",
                    "python -m experiments.run_vmr --exp E2 --ablation deterministic_target --seed 0",
                    "python -m experiments.run_vmr --exp E2 --ablation no_ambiguity_negatives --seed 0",
                    "python scripts/evaluate_vmr.py --exp E2 --write-json experiments/results/E2_metrics.json",
                ],
                "expected_outputs": ["experiments/results/E2_metrics.json", "tables/ablation_results.tex"],
                "paper_targets": ["Ablation table", "Analysis section"],
            },
            {
                "id": "E3",
                "name": "Robustness and ambiguity",
                "status": "planned",
                "claim": "The method is more robust under ambiguous queries, long videos, and noisy boundaries.",
                "purpose": "Stratify performance by query length, duration, boundary uncertainty, and long-video setting.",
                "datasets": ["QVHighlights", "Ego4D-NLQ"],
                "baselines": ["QD-DETR", "UniVTG", "CG-DETR", "OURS"],
                "metrics": ["stratified R@1 IoU=0.5", "mIoU", "highlight mAP", "boundary error"],
                "controls": ["predefined strata", "no post-hoc bin changes without logging"],
                "commands": [
                    f"cd {remote_dir}",
                    "python -m experiments.run_vmr --exp E3 --dataset qvhighlights --seed 0",
                    "python -m experiments.analyze_ambiguity --predictions experiments/results/E3_predictions.jsonl --out experiments/results/E3_robustness.json",
                ],
                "expected_outputs": ["experiments/results/E3_robustness.json", "figures/timeline_cases.pdf", "figures/boundary_error_hist.pdf"],
                "paper_targets": ["Robustness table", "Qualitative cases", "Error analysis"],
            },
            {
                "id": "E4",
                "name": "Efficiency and reproducibility",
                "status": "planned",
                "claim": "The method's improvement, if any, is not explained by an impractical compute increase.",
                "purpose": "Record parameters, training time, inference latency, feature assumptions, and reproducibility costs.",
                "datasets": ["Charades-STA"],
                "baselines": ["QD-DETR", "OURS"],
                "metrics": ["parameters", "train GPU hours", "inference clips/sec", "peak memory"],
                "controls": ["same hardware", "same batch size", "same feature cache"],
                "commands": [
                    f"cd {remote_dir}",
                    "python scripts/profile_vmr.py --methods qd_detr ours --write-json experiments/results/E4_efficiency.json",
                ],
                "expected_outputs": ["experiments/results/E4_efficiency.json", "tables/efficiency_results.tex"],
                "paper_targets": ["Efficiency paragraph", "Reproducibility checklist"],
            },
        ],
    }


def generic_registry(slug: str, remote_base: str) -> dict[str, Any]:
    remote_dir = f"{remote_base.rstrip('/')}/{slug}"
    return {
        "version": 1,
        "generated_at": now_iso(),
        "domain": "generic",
        "remote": {
            "base_dir": remote_dir,
            "results_dir": f"{remote_dir}/experiments/results",
            "logs_dir": f"{remote_dir}/experiments/logs",
            "figures_dir": f"{remote_dir}/figures",
        },
        "macro_plan": [],
        "experiments": [
            {
                "id": "E1",
                "name": "Main comparison",
                "status": "planned",
                "claim": "Primary method claim.",
                "purpose": "Compare the proposed method against strong baselines under controlled conditions.",
                "datasets": ["Dataset 1", "Dataset 2"],
                "baselines": ["Baseline 1", "Baseline 2", "Baseline 3"],
                "metrics": ["Primary metric", "Secondary metric"],
                "controls": ["same data split", "same budget", "same evaluation script"],
                "commands": [f"cd {remote_dir}", "python experiments/run_main.py --write-json experiments/results/E1_metrics.json"],
                "expected_outputs": ["experiments/results/E1_metrics.json", "tables/main_results.tex"],
                "paper_targets": ["Main results table"],
            },
            {
                "id": "E2",
                "name": "Ablation",
                "status": "planned",
                "claim": "Component-level contribution claim.",
                "purpose": "Remove each component and measure effect.",
                "datasets": ["Dataset 1"],
                "baselines": ["full", "minus component A", "minus component B"],
                "metrics": ["Primary metric"],
                "controls": ["same budget", "same seed"],
                "commands": [f"cd {remote_dir}", "python experiments/run_ablation.py --write-json experiments/results/E2_metrics.json"],
                "expected_outputs": ["experiments/results/E2_metrics.json", "tables/ablation_results.tex"],
                "paper_targets": ["Ablation table"],
            },
            {
                "id": "E3",
                "name": "Robustness",
                "status": "planned",
                "claim": "Robustness claim.",
                "purpose": "Test under perturbation, longer inputs, or harder strata.",
                "datasets": ["Dataset 2"],
                "baselines": ["strong baseline", "OURS"],
                "metrics": ["Primary metric", "robustness metric"],
                "controls": ["predefined strata"],
                "commands": [f"cd {remote_dir}", "python experiments/run_robustness.py --write-json experiments/results/E3_metrics.json"],
                "expected_outputs": ["experiments/results/E3_metrics.json", "figures/robustness_curve.pdf"],
                "paper_targets": ["Robustness analysis"],
            },
        ],
    }


def write_experiment_docs(project_dir: Path, registry: dict[str, Any], overwrite: bool) -> None:
    exp_dir = ensure_dir(project_dir / "experiments")
    for exp in registry.get("experiments", []):
        eid = exp["id"]
        path = exp_dir / f"{eid}_{re.sub(r'[^A-Za-z0-9]+', '_', exp['name']).strip('_').lower()}.md"
        if path.exists() and not overwrite:
            continue
        lines = [
            f"# {eid} - {exp['name']}",
            "",
            f"Status: {exp.get('status', 'planned')}",
            "",
            "## Claim",
            "",
            exp.get("claim", "TBD"),
            "",
            "## Purpose",
            "",
            exp.get("purpose", "TBD"),
            "",
            "## Datasets",
            "",
            *[f"- {item}" for item in exp.get("datasets", [])],
            "",
            "## Baselines",
            "",
            *[f"- {item}" for item in exp.get("baselines", [])],
            "",
            "## Metrics",
            "",
            *[f"- {item}" for item in exp.get("metrics", [])],
            "",
            "## Controls",
            "",
            *[f"- {item}" for item in exp.get("controls", [])],
            "",
            "## Commands",
            "",
            "```bash",
            *exp.get("commands", []),
            "```",
            "",
            "## Expected Outputs",
            "",
            *[f"- {item}" for item in exp.get("expected_outputs", [])],
            "",
            "## Paper Targets",
            "",
            *[f"- {item}" for item in exp.get("paper_targets", [])],
            "",
            "## Integrity Notes",
            "",
            "- Do not move metrics into the paper until the JSON output exists.",
            "- Failed and partial runs remain part of the audit trail.",
            "- Any protocol deviation must be logged before interpreting the result.",
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")


def write_run_queue(project_dir: Path, registry: dict[str, Any]) -> None:
    lines = [
        "# Experiment Run Queue",
        "",
        f"Generated: {now_iso()}",
        "",
        "Run these under the configured project directory. Remote runs should stay under the data disk path recorded in experiments/registry.json.",
        "",
    ]
    for exp in registry.get("experiments", []):
        lines.extend(
            [
                f"## {exp['id']} - {exp['name']}",
                "",
                f"Status: {exp.get('status', 'planned')}",
                "",
                "```bash",
                *exp.get("commands", []),
                "```",
                "",
                "Expected outputs:",
                *[f"- {item}" for item in exp.get("expected_outputs", [])],
                "",
            ]
        )
    (project_dir / "experiments" / "run_queue.md").write_text("\n".join(lines), encoding="utf-8")


def update_results_json(project_dir: Path, registry: dict[str, Any]) -> None:
    results_path = project_dir / "experiments" / "results.json"
    if results_path.exists():
        return
    datasets = sorted({dataset for exp in registry.get("experiments", []) for dataset in exp.get("datasets", [])})
    baselines = sorted({baseline for exp in registry.get("experiments", []) for baseline in exp.get("baselines", [])})
    ablations = [exp["name"] for exp in registry.get("experiments", []) if "ablation" in exp["name"].lower()]
    robustness = [exp["name"] for exp in registry.get("experiments", []) if "robust" in exp["name"].lower()]
    write_json(
        results_path,
        {
            "status": "planned",
            "planned": True,
            "paper_claim": "See experiments/registry.json.",
            "linked_claim": "Experiment registry links each run to a paper claim.",
            "datasets": datasets,
            "baselines": baselines,
            "ablations": ablations,
            "robustness": robustness,
            "efficiency": {"planned": True, "experiment_id": "E4"},
            "results": [],
            "statistics": {},
            "ceiling_floor_check": {},
            "notes": "No result values are recorded yet. Use collect_paper_results.py after real runs complete.",
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a PaperGuru-style experiment registry and run queue.")
    parser.add_argument("project_dir")
    parser.add_argument("--domain", choices=["generic", "vmr"], default=None)
    parser.add_argument("--remote-base", default="/root/autodl-tmp/autopaper", help="Remote data-disk base directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing registry and per-experiment docs.")
    args = parser.parse_args()

    project_dir = project_path(args.project_dir)
    state = read_state(project_dir)
    slug = str(state.get("project", {}).get("slug") or project_dir.name)
    domain = detect_domain(state, args.domain)
    registry_path = project_dir / "experiments" / "registry.json"
    if registry_path.exists() and not args.force:
        registry = read_json(registry_path, default={})
    else:
        registry = vmr_registry(slug, args.remote_base) if domain == "vmr" else generic_registry(slug, args.remote_base)
        ensure_dir(registry_path.parent)
        write_json(registry_path, registry)

    write_experiment_docs(project_dir, registry, overwrite=args.force)
    write_run_queue(project_dir, registry)
    update_results_json(project_dir, registry)
    state["latest_experiment_registry"] = str(registry_path)
    state.setdefault("next_actions", [])
    action = "Use experiments/registry.json and experiments/run_queue.md as the source of truth for experiment execution."
    if action not in state["next_actions"]:
        state["next_actions"].append(action)
    write_state(project_dir, state)
    print(f"Wrote {registry_path}")
    print(f"Wrote {project_dir / 'experiments' / 'run_queue.md'}")


if __name__ == "__main__":
    main()
