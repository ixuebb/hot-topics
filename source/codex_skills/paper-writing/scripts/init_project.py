from __future__ import annotations

import argparse
from pathlib import Path

from workflow_common import WORKFLOW_VERSION, copy_tree, ensure_dir, now_iso, slugify, write_json


def build_topic_yaml(args: argparse.Namespace, slug: str) -> str:
    return "\n".join(
        [
            f"slug: {slug}",
            f"title: {args.title}",
            f"topic: {args.topic}",
            f"scope: {args.scope}",
            f"angle: {args.angle}",
            f"audience: {args.audience}",
            f"paper_type: {args.paper_type}",
            f"method_name: {args.method_name}",
            f"target_score: {args.target_score}",
            f"target_pages: {args.target_pages}",
            "notes: |",
            "  Initialized by Codex paper-writing workflow.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a strict autonomous paper-writing project.")
    parser.add_argument("project_dir", help="Target project directory.")
    parser.add_argument("--title", required=True, help="Working title.")
    parser.add_argument("--topic", required=True, help="Research topic.")
    parser.add_argument("--scope", default="Survey paper", help="Scope answer for Phase 0.")
    parser.add_argument("--angle", default="New taxonomy plus critical synthesis", help="Angle answer for Phase 0.")
    parser.add_argument("--audience", default="Top-tier ML/AI research audience", help="Audience answer for Phase 0.")
    parser.add_argument("--slug", default=None, help="Project slug. Defaults to title slug.")
    parser.add_argument("--paper-type", choices=["survey", "original_research"], default="survey", help="Workflow mode.")
    parser.add_argument("--method-name", default="", help="Optional named method for original research.")
    parser.add_argument("--target-score", type=float, default=8.5, help="Final median review target.")
    parser.add_argument("--target-pages", type=int, default=50, help="Expected final PDF pages.")
    parser.add_argument("--max-iterations", type=int, default=12, help="Hard stop iteration count.")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    slug = args.slug or slugify(args.title)
    ensure_dir(project_dir)

    skill_dir = Path(__file__).resolve().parents[1]
    template_dir = skill_dir / "assets" / "latex_survey_template"
    copy_tree(template_dir, project_dir)

    for rel in [
        "refs",
        "sections",
        "story",
        "code",
        "experiments",
        "experiments/results",
        "experiments/logs",
        "figures",
        "tables",
        "reviews",
        "build",
        "snapshots",
    ]:
        ensure_dir(project_dir / rel)

    (project_dir / "refs" / "raw_candidates.jsonl").touch(exist_ok=True)
    (project_dir / "refs" / "scored_candidates.jsonl").touch(exist_ok=True)
    (project_dir / "refs" / "citation_plan.jsonl").touch(exist_ok=True)
    if not (project_dir / "refs" / "references.bib").exists():
        (project_dir / "refs" / "references.bib").write_text("% Add verified BibTeX entries here.\n", encoding="utf-8")
    if not (project_dir / "results_numbers.tex").exists():
        (project_dir / "results_numbers.tex").write_text(
            "% Auto-generated result macros will be written by collect_paper_results.py.\n",
            encoding="utf-8",
        )
    if not (project_dir / "experiments" / "README.md").exists():
        (project_dir / "experiments" / "README.md").write_text(
            "\n".join(
                [
                    "# Experiments",
                    "",
                    "Use init_experiment_registry.py to create the executable experiment matrix.",
                    "Use collect_paper_results.py to convert real results into results_numbers.tex.",
                    "Use generate_paper_figures.py to create data-backed figures from result artifacts.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    (project_dir / "topic.yaml").write_text(build_topic_yaml(args, slug), encoding="utf-8")

    state = {
        "workflow_version": WORKFLOW_VERSION,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "status": "initialized",
        "phase": "phase_0_topic_selection",
        "iteration": 0,
        "current_version": 0,
        "project": {
            "slug": slug,
            "title": args.title,
            "topic": args.topic,
            "scope": args.scope,
            "angle": args.angle,
            "audience": args.audience,
            "paper_type": args.paper_type,
            "method_name": args.method_name,
            "target_score": args.target_score,
            "target_pages": args.target_pages,
        },
        "stop_rules": {
            "target_score": args.target_score,
            "plateau_delta": 0.3,
            "plateau_rounds": 2,
            "max_iterations": args.max_iterations,
        },
        "score_history": [],
        "gate_history": [],
        "iteration_history": [],
        "next_actions": [
            "Run next_iteration.py --advance.",
            "Run build_research_brief.py and init_experiment_registry.py for original research projects.",
            "Follow iteration_brief.md.",
            "Compile and gate-check before snapshotting.",
        ],
    }
    write_json(project_dir / "state.json", state)

    print(f"Initialized paper project: {project_dir}")
    print(f"Next: python {skill_dir / 'scripts' / 'next_iteration.py'} {project_dir} --advance")


if __name__ == "__main__":
    main()
