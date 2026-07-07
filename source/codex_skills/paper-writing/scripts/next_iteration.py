from __future__ import annotations

import argparse
from pathlib import Path

from workflow_common import append_history, load_latest_review, now_iso, project_path, read_json, read_state, write_state


ITERATION_PLAN = {
    1: {
        "phase": "phase_1_draft",
        "target": "6.0",
        "subskills": ["paper_structure"],
        "actions": [
            "Create manuscript skeleton and section files.",
            "Write abstract placeholder, introduction gap, background definitions, and roadmap.",
            "Ensure main.tex compiles with placeholder sections.",
        ],
        "expected_artifacts": ["main.tex", "sections/*.tex", "build/compile_report.json"],
    },
    2: {
        "phase": "phase_1_draft",
        "target": "6.0",
        "subskills": ["literature_survey"],
        "actions": [
            "Generate 20-30 keyword queries covering every taxonomy cell.",
            "Run search_literature.py for recall.",
            "Run score_lqs.py for LQS scoring and initial BibTeX.",
        ],
        "expected_artifacts": ["refs/raw_candidates.jsonl", "refs/scored_candidates.jsonl", "refs/references.bib"],
    },
    3: {
        "phase": "phase_1_draft",
        "target": "6.0",
        "subskills": ["paper_structure", "figures_tables"],
        "actions": [
            "Write core method-family sections with Claim-Evidence-Implication paragraphs.",
            "Create at least two structural figures or taxonomy tables.",
            "Cite A/B references in every core section.",
        ],
        "expected_artifacts": ["sections/03_*.tex", "sections/04_*.tex", "figures/* or tables/*.tex"],
    },
    4: {
        "phase": "phase_1_draft",
        "target": "6.0",
        "subskills": ["literature_survey", "paper_structure"],
        "actions": [
            "Finalize A/B/C/D citation depth plan.",
            "Upgrade arXiv-only references through DBLP/OpenReview when possible.",
            "Write benchmarks, future work, and conclusion sections.",
        ],
        "expected_artifacts": ["refs/citation_plan.jsonl", "sections/07_*.tex", "sections/08_*.tex"],
    },
    5: {
        "phase": "phase_1_draft",
        "target": "6.0",
        "subskills": ["literature_survey", "peer_review_simulation"],
        "actions": [
            "Run verify_bib.py.",
            "Compile the PDF.",
            "Write review_round_1.json with 3-5 reviewer personas.",
            "Run route_review.py.",
        ],
        "expected_artifacts": ["refs/verification_report.json", "reviews/review_round_1.json"],
    },
    6: {
        "phase": "phase_1_draft",
        "target": "6.0",
        "subskills": ["routed_fixes"],
        "actions": [
            "Fix the routed weaknesses from review round 1.",
            "Recompile and run gate_check.py.",
            "Snapshot the resulting version.",
        ],
        "expected_artifacts": ["reviews/routing_plan_round_1.json", "gate_report.json", "snapshots/v001"],
    },
    7: {
        "phase": "phase_2_deep_improvement",
        "target": "7.5-8.0",
        "subskills": ["experiment_design"],
        "actions": [
            "Write preregister.md before any experiment execution.",
            "Run the smallest falsifiable pilot study that supports a specific paper claim.",
            "Save results.json and experiment_summary.md.",
        ],
        "expected_artifacts": ["experiments/preregister.md", "experiments/results.json", "experiments/experiment_summary.md"],
    },
    8: {
        "phase": "phase_2_deep_improvement",
        "target": "7.5-8.0",
        "subskills": ["figures_tables", "paper_structure"],
        "actions": [
            "Convert experiment results into tables and vector figures.",
            "Integrate findings into the manuscript with limitations.",
            "Ensure captions state conclusions, not only descriptions.",
        ],
        "expected_artifacts": ["figures/*.pdf", "tables/*.tex", "sections/*experiment*.tex"],
    },
    9: {
        "phase": "phase_2_deep_improvement",
        "target": "7.5-8.0",
        "subskills": ["peer_review_simulation"],
        "actions": [
            "Compile the PDF.",
            "Write the next review_round_N.json.",
            "Run route_review.py and gate_check.py.",
        ],
        "expected_artifacts": ["reviews/review_round_2.json", "reviews/routing_plan_round_2.json", "gate_report.json"],
    },
}


SPRINT_PLAN = {
    "phase": "phase_3_sprint",
    "target": "8.5+",
    "subskills": ["peer_review_simulation", "routed_fixes"],
    "actions": [
        "Run review or inspect the latest routing plan.",
        "Fix all Major weaknesses first and no more than three Minor weaknesses per iteration.",
        "Recompile, run gate_check.py, and snapshot.",
        "Stop only when stop rules pass.",
    ],
    "expected_artifacts": ["reviews/review_round_N.json", "reviews/routing_plan_round_N.json", "gate_report.json", "snapshots/vNNN"],
}

ORIGINAL_RESEARCH_PLAN = {
    1: {
        "phase": "phase_0_idea_discovery",
        "target": "idea selected",
        "subskills": ["literature_survey", "paper_structure"],
        "actions": [
            "Research recent domain papers and required baselines.",
            "Generate refs/raw_candidates.jsonl, scored_candidates.jsonl, references.bib, and citation_plan.jsonl.",
            "Write idea_bank.md with at least 8 experimentally testable ideas.",
            "Select the strongest idea and write it into topic.yaml and state.json.",
            "Run build_research_brief.py to create research_brief.md and story/00_research_brief.md.",
        ],
        "expected_artifacts": ["refs/*.jsonl", "refs/references.bib", "idea_bank.md", "topic.yaml", "state.json", "research_brief.md", "story/00_research_brief.md"],
    },
    2: {
        "phase": "phase_1_method_proposal",
        "target": "6.0",
        "subskills": ["paper_structure"],
        "actions": [
            "Create AAAI original research manuscript skeleton.",
            "Write problem gap, method name, formal problem definition, and training/inference objective.",
            "Do not write survey-style method-family sections.",
        ],
        "expected_artifacts": ["main.tex", "sections/01_*.tex", "sections/04_method.tex"],
    },
    3: {
        "phase": "phase_2_experiment_design",
        "target": "6.5",
        "subskills": ["experiment_design"],
        "actions": [
            "Write experiments/preregister.md before any results.",
            "Run init_experiment_registry.py to create experiments/registry.json, E1/E2/E3 docs, and experiments/run_queue.md.",
            "Create executable experiment plan over 2-3 standard VMR datasets.",
            "Create experiments/todo_runs.md if data or GPU are unavailable.",
        ],
        "expected_artifacts": ["experiments/preregister.md", "experiments/registry.json", "experiments/run_queue.md", "experiments/todo_runs.md", "experiments/results.json"],
    },
    4: {
        "phase": "phase_3_writing",
        "target": "7.0",
        "subskills": ["paper_structure", "figures_tables"],
        "actions": [
            "Draft AAAI-style manuscript sections: Abstract, Introduction, Related Work, Method, Experiments, Analysis, Limitations, Conclusion, Reproducibility Checklist.",
            "Add method figure placeholder, main results table schema, ablation schema, and qualitative/error analysis schema.",
            "Run collect_paper_results.py so tables consume results_numbers.tex macros instead of hand-typed numbers.",
            "Run generate_paper_figures.py; if no data exists yet, keep figures/figure_plan.md and figure_manifest.json as planned-only provenance.",
            "Compile after writing.",
        ],
        "expected_artifacts": ["sections/*.tex", "figures/*", "tables/*.tex", "results_numbers.tex", "experiments/paper_numbers.json", "figures/figure_manifest.json", "build/compile_report.json"],
    },
    5: {
        "phase": "phase_4_review",
        "target": "7.5",
        "subskills": ["peer_review_simulation"],
        "actions": [
            "Write reviews/review_round_1.json with AAAI AC, VMR expert, experimentalist, skeptical reviewer, and Stanford-style mentor.",
            "Run route_review.py.",
            "Run gate_check.py.",
        ],
        "expected_artifacts": ["reviews/review_round_1.json", "reviews/routing_plan_round_1.json", "gate_report.json"],
    },
    6: {
        "phase": "phase_5_autonomous_iteration",
        "target": "8.0",
        "subskills": ["routed_fixes", "peer_review_simulation"],
        "actions": [
            "Fix Major weaknesses from routing plan first.",
            "Recompile, rerun gate_check.py, write next review if substantial changes were made.",
            "Refresh research_brief.md, results_numbers.tex, and figure_manifest.json after any experiment or result change.",
            "Snapshot the version.",
        ],
        "expected_artifacts": ["reviews/routing_plan_round_1.json", "gate_report.json", "snapshots/vNNN"],
    },
}

ORIGINAL_SPRINT_PLAN = {
    "phase": "phase_5_autonomous_iteration",
    "target": "8.0+",
    "subskills": ["peer_review_simulation", "routed_fixes"],
    "actions": [
        "Review the manuscript as AAAI original research, not a survey.",
        "Fix fatal novelty, baseline, experiment, reproducibility, and clarity issues.",
        "Run plan_section_expansion.py when submission_quality fails, then expand sections from writing_context/section_packets rather than rewriting the whole paper in one pass.",
        "Run build_research_brief.py if the research story, thesis, or experimental plan changed.",
        "Run init_experiment_registry.py when experiments are missing a registry, run queue, commands, or paper-target mapping.",
        "Run refresh_artifacts.ps1 after remote jobs, then collect_paper_results.py and generate_paper_figures.py to update macros and figures from real artifacts.",
        "Inspect submission_quality in gate_report.json and fix page count, word budget, citation density, formalism, figure/table narrative, AAAI template, and layout overflow failures.",
        "Maintain truthful experiment status: no fabricated results.",
        "Compile, gate-check, route weaknesses, and snapshot.",
    ],
    "expected_artifacts": ["research_brief.md", "experiments/registry.json", "experiments/run_queue.md", "results_numbers.tex", "experiments/paper_numbers.json", "figures/figure_manifest.json", "reviews/review_round_N.json", "reviews/routing_plan_round_N.json", "gate_report.json", "snapshots/vNNN"],
}


def latest_gate_passed(project_dir: Path) -> bool:
    report = read_json(project_dir / "gate_report.json", default={})
    return bool(report.get("all_passed"))


def gate_failure_lines(project_dir: Path, limit: int = 20) -> list[str]:
    report = read_json(project_dir / "gate_report.json", default={})
    lines: list[str] = []
    for gate_name, gate in report.get("gates", {}).items():
        if gate.get("passed"):
            continue
        for failure in gate.get("failures", []):
            lines.append(f"- {gate_name}: {failure}")
            if len(lines) >= limit:
                return lines
    return lines


def should_stop(state: dict, project_dir: Path) -> tuple[bool, str]:
    rules = state.get("stop_rules", {})
    scores = [float(item["median_score"]) for item in state.get("score_history", []) if "median_score" in item]
    if scores and scores[-1] >= float(rules.get("target_score", 8.5)) and latest_gate_passed(project_dir):
        return True, "target_score_and_all_gates_passed"
    min_plateau_iteration = 5 if state.get("project", {}).get("paper_type") == "original_research" else 0
    if len(scores) >= 3 and int(state.get("iteration", 0)) >= min_plateau_iteration:
        delta1 = scores[-1] - scores[-2]
        delta2 = scores[-2] - scores[-3]
        if delta1 <= float(rules.get("plateau_delta", 0.3)) and delta2 <= float(rules.get("plateau_delta", 0.3)):
            return True, "score_plateau"
    if int(state.get("iteration", 0)) >= int(rules.get("max_iterations", 12)):
        return True, "max_iterations"
    return False, ""


def render_brief(state: dict, plan: dict, iteration: int, blocking_failures: list[str] | None = None) -> str:
    lines = [
        f"# Iteration {iteration} Brief",
        "",
        f"Phase: {plan['phase']}",
        f"Target score: {plan['target']}",
        f"Generated: {now_iso()}",
        "",
        "## Required Subskills",
    ]
    lines.extend(f"- {item}" for item in plan["subskills"])
    lines.extend(["", "## Actions"])
    lines.extend(f"- {item}" for item in plan["actions"])
    lines.extend(["", "## Expected Artifacts"])
    lines.extend(f"- {item}" for item in plan["expected_artifacts"])
    if blocking_failures:
        lines.extend(["", "## Blocking Gate Failures"])
        lines.extend(blocking_failures)
    lines.extend(["", "## Mandatory Checks", "- Compile LaTeX if manuscript changed.", "- Run gate_check.py.", "- Snapshot after meaningful progress."])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Advance or inspect the autonomous paper-writing iteration state.")
    parser.add_argument("project_dir")
    parser.add_argument("--advance", action="store_true", help="Advance to the next iteration and write iteration_brief.md.")
    parser.add_argument("--record-score", type=float, default=None, help="Record a median review score for the current iteration.")
    parser.add_argument("--review-file", default=None, help="Review file associated with --record-score.")
    parser.add_argument("--summary", default="", help="Optional iteration summary.")
    args = parser.parse_args()

    project_dir = project_path(args.project_dir)
    state = read_state(project_dir)

    if args.record_score is not None:
        append_history(
            state,
            "score_history",
            {
                "iteration": state.get("iteration", 0),
                "median_score": args.record_score,
                "review_file": args.review_file,
                "summary": args.summary,
            },
        )
        write_state(project_dir, state)

    stop, reason = should_stop(state, project_dir)
    if stop:
        state["status"] = "complete" if reason == "target_score_and_all_gates_passed" else "stopped"
        state["stop_reason"] = reason
        write_state(project_dir, state)
        print(f"STOP: {reason}")
        return

    next_iter = int(state.get("iteration", 0)) + 1 if args.advance else int(state.get("iteration", 0)) + 1
    paper_type = state.get("project", {}).get("paper_type", "survey")
    if paper_type == "original_research":
        plan = ORIGINAL_RESEARCH_PLAN.get(next_iter, ORIGINAL_SPRINT_PLAN)
    else:
        plan = ITERATION_PLAN.get(next_iter, SPRINT_PLAN)
    if args.advance:
        state["iteration"] = next_iter
        state["phase"] = plan["phase"]
        state["status"] = "active"
        state["next_actions"] = plan["actions"]
        append_history(state, "iteration_history", {"iteration": next_iter, "phase": plan["phase"], "target": plan["target"]})
        write_state(project_dir, state)
        (project_dir / "iteration_brief.md").write_text(render_brief(state, plan, next_iter, gate_failure_lines(project_dir)), encoding="utf-8")

    review_path, review = load_latest_review(project_dir)
    if review and review.get("median_score") is not None:
        print(f"Latest review: {review_path.name} median_score={review.get('median_score')}")
    print(render_brief(state, plan, next_iter, gate_failure_lines(project_dir)))


if __name__ == "__main__":
    main()
