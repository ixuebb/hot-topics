from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from workflow_common import load_latest_review, read_state, write_json, write_state


ROUTES = [
    (re.compile(r"too short|underdeveloped|thin manuscript|page count|word count|not enough deep paragraphs|paragraphs are too short", re.I), "paper_structure", "Expand the underdeveloped sections to the original-research section budgets before changing claims."),
    (re.compile(r"citation weaving|citation density|sparse citation|unsupported claim|problem-gap support|related work.*dense", re.I), "literature_survey", "Add targeted A/B citations and weave them into Introduction, Related Work, and Method paragraphs."),
    (re.compile(r"formalism|equation|objective|algorithm|pseudocode|problem definition", re.I), "paper_structure", "Strengthen the method with formal problem definition, objectives, and algorithm/pseudocode blocks."),
    (re.compile(r"AAAI style|AAAI template|double-blind|anonymous|layout|format|overfull|overflow|PDF quality", re.I), "paper_structure", "Fix AAAI template, anonymous submission metadata, and layout overflow before content polishing."),
    (re.compile(r"figure narrative|table narrative|main result table|ablation table|qualitative|error analysis", re.I), "figures_tables", "Add or revise conclusion-bearing figures/tables and reference them from the text."),
    (re.compile(r"citation coverage|insufficient citation|missing citation", re.I), "literature_survey", "Run targeted search and assign A/B references to weak taxonomy cells."),
    (re.compile(r"arxiv-only|preprint|venue", re.I), "literature_survey", "Upgrade arXiv entries via DBLP/OpenReview and replace BibTeX entries when accepted venues exist."),
    (re.compile(r"recent paper|2025|2026|outdated", re.I), "literature_survey", "Run focused recent-paper search and update references.bib."),
    (re.compile(r"structure unclear|organization|flow|transition", re.I), "paper_structure", "Reorganize sections and add explicit transitions."),
    (re.compile(r"analysis lacks depth|shallow|critical", re.I), "paper_structure", "Add Critical Assessment paragraphs with trade-offs and limitations."),
    (re.compile(r"table.*incomparable|comparison|delta", re.I), "figures_tables", "Regroup tables and add normalized metrics or delta columns."),
    (re.compile(r"missing visualization|figure|visual", re.I), "figures_tables", "Add a self-contained figure with a conclusion-bearing caption."),
    (re.compile(r"error bar|std|standard deviation|confidence", re.I), "figures_tables", "Add mean plus std, confidence intervals, or error bars."),
    (re.compile(r"taxonomy|not novel|classification", re.I), "paper_structure", "Redesign taxonomy as a multi-axis matrix and discuss empty cells."),
    (re.compile(r"claim.*strong|overclaim|unsupported", re.I), "paper_structure", "Downgrade claim strength using hedge language and evidence alignment."),
    (re.compile(r"no experiment|missing experiment|validation", re.I), "experiment_design", "Design a minimal pilot study tied to a specific claim."),
    (re.compile(r"experiment.*rigor|trial|baseline|ablation|statistical", re.I), "experiment_design", "Add trials, baselines, ablations, and statistical reporting."),
]


def weakness_text(item: dict[str, Any]) -> str:
    return " ".join(str(item.get(key, "")) for key in ["type", "evidence", "suggestion", "severity"])


def route_one(weakness: dict[str, Any]) -> dict[str, Any]:
    text = weakness_text(weakness)
    for pattern, target, action in ROUTES:
        if pattern.search(text):
            return {"target": target, "action": action, "weakness": weakness}
    return {"target": "paper_structure", "action": "Inspect weakness and make the smallest manuscript fix that addresses it.", "weakness": weakness}


def main() -> None:
    parser = argparse.ArgumentParser(description="Route peer-review weaknesses back to paper-writing subskills.")
    parser.add_argument("project_dir")
    parser.add_argument("--review-file", default=None)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if args.review_file:
        review_path = Path(args.review_file)
        import json

        review = json.loads(review_path.read_text(encoding="utf-8"))
    else:
        review_path, review = load_latest_review(project_dir)
        if not review_path or not review:
            raise SystemExit("No review_round_N.json found.")

    weaknesses = []
    for reviewer in review.get("reviewers", []):
        for weakness in reviewer.get("weaknesses", []):
            item = dict(weakness)
            item["reviewer"] = reviewer.get("persona")
            weaknesses.append(item)
    routed = [route_one(item) for item in weaknesses]
    major = [item for item in routed if str(item["weakness"].get("severity", "")).lower() == "major"]
    minor = [item for item in routed if item not in major]
    round_no = review.get("round") or re.findall(r"(\d+)", review_path.name)[-1]
    plan = {
        "review_file": str(review_path),
        "round": int(round_no),
        "priority_order": major + minor,
        "summary": {
            "total": len(routed),
            "major": len(major),
            "minor": len(minor),
            "targets": {target: sum(1 for item in routed if item["target"] == target) for target in sorted({item["target"] for item in routed})},
        },
    }
    out_path = project_dir / "reviews" / f"routing_plan_round_{int(round_no)}.json"
    write_json(out_path, plan)

    state = read_state(project_dir)
    state["latest_routing_plan"] = str(out_path)
    state["next_actions"] = [f"{item['target']}: {item['action']}" for item in plan["priority_order"][:5]]
    write_state(project_dir, state)

    print(f"Wrote routing plan: {out_path}")
    for item in plan["priority_order"][:10]:
        print(f"- {item['target']}: {item['action']}")


if __name__ == "__main__":
    main()
