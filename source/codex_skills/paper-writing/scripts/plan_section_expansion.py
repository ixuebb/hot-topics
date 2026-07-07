from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

from workflow_common import ensure_dir, read_json, read_jsonl, read_state, write_json, write_state


SECTION_FILES = {
    "introduction": "sections/01_introduction.tex",
    "related_work": "sections/02_related_work.tex",
    "method": "sections/04_method.tex",
    "experiments": "sections/05_experiments.tex",
    "analysis": "sections/06_analysis_ablation.tex",
    "limitations": "sections/07_limitations.tex",
    "conclusion": "sections/08_conclusion.tex",
}


SECTION_LABELS = {
    "introduction": "Introduction",
    "related_work": "Related Work",
    "method": "Method",
    "experiments": "Experiments",
    "analysis": "Analysis / Ablation",
    "limitations": "Limitations",
    "conclusion": "Conclusion",
}


SECTION_THRESHOLD_KEYS = {
    "introduction": "min_intro_words",
    "related_work": "min_related_work_words",
    "method": "min_method_words",
    "experiments": "min_experiments_words",
    "analysis": "min_analysis_words",
    "limitations": "min_limitations_words",
    "conclusion": "min_conclusion_words",
}


SECTION_PROMPTS = {
    "introduction": [
        "Open with the concrete VMR failure mode: natural-language queries often under-specify temporal boundaries.",
        "Explain why single annotated intervals are a brittle supervision target rather than treating the issue as annotation noise only.",
        "Contrast DREAM against DETR-style localization, event-aware grounding, and Video-LLM timestamp grounding.",
        "End with crisp contributions that are experimentally testable, not survey-style promises.",
    ],
    "related_work": [
        "Organize by technical pressure points, not by a flat list: DETR-style VMR, event/query decomposition, uncertainty and boundary ambiguity, Video-LLM grounding, and datasets/evaluation.",
        "Each paragraph should name the limitation that motivates DREAM.",
        "Do not overclaim that prior work ignores ambiguity; state the narrower gap in supervised distributional boundary training and ambiguity-aware negatives.",
    ],
    "method": [
        "Give the formal problem definition before modules.",
        "Add one algorithm block for training and inference.",
        "Explain event atom extraction, boundary target construction, distributional loss, ambiguity-aware negatives, and inference calibration as connected components.",
        "State what is implementation-essential versus optional engineering choice.",
    ],
    "experiments": [
        "Keep results as planned/placeholders until real runs exist.",
        "Write the evaluation protocol like an AAAI paper: datasets, baselines, metrics, implementation, main table schema, and statistical plan.",
        "Tie every planned experiment to a falsifiable claim in the method.",
        "Mention the remote AutoDL data-disk constraint only in reproducibility or experiment logistics, not as a headline contribution.",
    ],
    "analysis": [
        "Describe ablations, robustness, calibration, qualitative cases, and error analysis that would diagnose the method.",
        "Use table references to explain what each planned row will prove or refute.",
        "Be explicit that no conclusion is claimed before execution.",
    ],
    "limitations": [
        "Acknowledge supervision ambiguity, data preprocessing, feature dependence, event parser brittleness, and compute constraints.",
        "Keep it concise but substantive.",
    ],
    "conclusion": [
        "Restate the research hypothesis and what evidence is still required.",
        "Avoid claiming empirical success before experiments run.",
    ],
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def safe_name(section: str) -> str:
    return section.replace("_", "-")


def citation_candidates(project_dir: Path) -> list[dict[str, Any]]:
    rows = read_jsonl(project_dir / "refs" / "citation_plan.jsonl")
    if rows:
        return rows
    bib = read_text(project_dir / "refs" / "references.bib")
    candidates: list[dict[str, Any]] = []
    for item in re.split(r"\n@", bib):
        match_key = re.match(r"(?:@\w+\{)?([^,\s]+)", item)
        match_title = re.search(r"title\s*=\s*\{([^{}]+)\}", item, re.I)
        if match_key and match_title:
            candidates.append({"bib_key": match_key.group(1), "title": match_title.group(1), "depth": "B", "lqs": 0})
    return candidates


def select_citations(candidates: list[dict[str, Any]], section: str, limit: int = 12) -> list[dict[str, Any]]:
    patterns = {
        "introduction": r"moment|temporal|ground|detr|llm|dataset|highlight|uncertain|boundary",
        "related_work": r".*",
        "method": r"event|concept|decompos|uncertain|boundary|gmm|evidential|calibrat|detr",
        "experiments": r"moment|qd|univtg|eatr|cg|tr-detr|sim-detr|qvhighlights|charades|activitynet|tacos",
        "analysis": r"boundary|uncertain|calibrat|imprecise|ranking|fuzzy|evidential|gmm",
        "limitations": r"llm|dataset|weakly|zero-shot|imprecise|open-world",
        "conclusion": r"moment|temporal|ground|boundary",
    }
    pattern = re.compile(patterns.get(section, r".*"), re.I)
    scored = []
    for row in candidates:
        title = str(row.get("title", ""))
        depth = str(row.get("depth", "C"))
        score = float(row.get("lqs") or 0)
        if pattern.search(title):
            score += 2
        if depth == "A":
            score += 2
        elif depth == "B":
            score += 1
        scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:limit]]


def make_packet(
    project_dir: Path,
    section: str,
    current_words: int,
    target_words: int,
    citations: list[dict[str, Any]],
) -> str:
    path = project_dir / SECTION_FILES[section]
    current = read_text(path)
    gap = max(0, target_words - current_words)
    paragraph_target = max(1, math.ceil(target_words / 150))
    lines = [
        f"# Expansion Packet: {SECTION_LABELS[section]}",
        "",
        f"File: `{SECTION_FILES[section]}`",
        f"Current words: {current_words}",
        f"Target words: {target_words}",
        f"Gap to fill: {gap}",
        f"Target paragraph count: {paragraph_target} paragraphs, mostly 100-180 words each.",
        "",
        "## Non-Negotiable Rules",
        "",
        "- Write as an AAAI original research paper, not a survey or blog.",
        "- Do not fabricate experimental results, dataset metrics, SOTA claims, or reviewer conclusions.",
        "- Important claims need citations, preregistered experiments, or explicit planned-status language.",
        "- Prefer Claim-Evidence-Implication and Compare-Contrast paragraphs over short outline prose.",
        "- Preserve LaTeX labels used elsewhere unless intentionally updating all references.",
        "",
        "## Section Tasks",
    ]
    lines.extend(f"- {item}" for item in SECTION_PROMPTS.get(section, []))
    lines.extend(["", "## Citation Candidates"])
    for row in citations:
        key = row.get("bib_key")
        title = row.get("title")
        depth = row.get("depth", "")
        lqs = row.get("lqs", "")
        lines.append(f"- `\\cite{{{key}}}` ({depth}, LQS {lqs}): {title}")
    if section == "experiments":
        prereg = read_text(project_dir / "experiments" / "preregister.md")
        todo = read_text(project_dir / "experiments" / "todo_runs.md")
        lines.extend(
            [
                "",
                "## Experiment Context",
                "",
                "Use these files as the source of truth:",
                "",
                "- `experiments/preregister.md`",
                "- `experiments/todo_runs.md`",
                "",
                "Preregistration excerpt:",
                "",
                "```markdown",
                prereg[:2500],
                "```",
                "",
                "Executable-plan excerpt:",
                "",
                "```markdown",
                todo[:2500],
                "```",
            ]
        )
    lines.extend(["", "## Current Section Text", "", "```latex", current.strip(), "```", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create per-section expansion context packets from gate failures.")
    parser.add_argument("project_dir")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    report = read_json(project_dir / "gate_report.json", default={})
    submission = report.get("gates", {}).get("submission_quality", {})
    metrics = submission.get("metrics", {})
    thresholds = metrics.get("thresholds", {})
    section_words = metrics.get("section_words", {})
    candidates = citation_candidates(project_dir)

    out_dir = ensure_dir(project_dir / "writing_context" / "section_packets")
    plan_rows: list[dict[str, Any]] = []
    for section, threshold_key in SECTION_THRESHOLD_KEYS.items():
        target = int(thresholds.get(threshold_key, 0) or 0)
        current = int(section_words.get(section, 0) or 0)
        if target <= 0:
            continue
        gap = max(0, target - current)
        citations = select_citations(candidates, section)
        packet_path = out_dir / f"{safe_name(section)}.md"
        packet_path.write_text(make_packet(project_dir, section, current, target, citations), encoding="utf-8")
        plan_rows.append(
            {
                "section": section,
                "label": SECTION_LABELS[section],
                "file": SECTION_FILES[section],
                "current_words": current,
                "target_words": target,
                "gap": gap,
                "packet": str(packet_path.relative_to(project_dir)),
            }
        )

    total_current = int(metrics.get("total_words", 0) or 0)
    min_words = int(thresholds.get("min_words", 0) or 0)
    plan_lines = [
        "# Section Expansion Plan",
        "",
        f"Total current words: {total_current}",
        f"Total target words: {min_words}",
        f"Total gap: {max(0, min_words - total_current)}",
        "",
        "## Expansion Order",
        "",
        "1. Introduction: establish the problem gap and contributions.",
        "2. Related Work: weave citations and position the novelty.",
        "3. Method: add formalism and algorithm block.",
        "4. Experiments: turn preregistration into a full AAAI protocol without fabricating results.",
        "5. Analysis/Ablation: describe diagnostic tests and expected table logic without claiming outcomes.",
        "6. Limitations and Conclusion: make them concise but complete.",
        "",
        "## Section Budgets",
        "",
        "| Section | Current | Target | Gap | Packet |",
        "|---|---:|---:|---:|---|",
    ]
    for row in plan_rows:
        plan_lines.append(
            f"| {row['label']} | {row['current_words']} | {row['target_words']} | {row['gap']} | `{row['packet']}` |"
        )
    plan_lines.extend(
        [
            "",
            "## Mandatory Use",
            "",
            "Before rewriting any section, open its packet and use the citation candidates and section tasks.",
            "Do not rewrite the whole paper in one pass. Expand one or two sections, compile, run gate_check.py, then continue.",
        ]
    )
    plan_path = project_dir / "writing_context" / "expansion_plan.md"
    plan_path.write_text("\n".join(plan_lines) + "\n", encoding="utf-8")
    write_json(project_dir / "writing_context" / "expansion_plan.json", plan_rows)

    try:
        state = read_state(project_dir)
        state["latest_expansion_plan"] = str(plan_path)
        state["next_actions"] = [
            f"Expand {row['label']} using {row['packet']} until it reaches {row['target_words']} words."
            for row in plan_rows
            if row["gap"] > 0
        ][:6]
        write_state(project_dir, state)
    except Exception:
        pass

    print(f"Wrote expansion plan: {plan_path}")
    for row in plan_rows:
        print(f"- {row['label']}: {row['current_words']} -> {row['target_words']} ({row['packet']})")


if __name__ == "__main__":
    main()
