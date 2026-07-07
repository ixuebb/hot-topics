from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from workflow_common import ensure_dir, now_iso, project_path, read_json, read_jsonl, read_state, write_json, write_state


def parse_topic_yaml(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    current_key: str | None = None
    block_lines: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if current_key and (raw.startswith("  ") or not raw.strip()):
            block_lines.append(raw[2:] if raw.startswith("  ") else raw)
            continue
        if current_key:
            out[current_key] = "\n".join(block_lines).strip()
            current_key = None
            block_lines = []
        match = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", raw)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if value == "|":
            current_key = key
            block_lines = []
        else:
            out[key] = value.strip('"').strip("'")
    if current_key:
        out[current_key] = "\n".join(block_lines).strip()
    return out


def first_nonempty(*values: Any, default: str = "TBD") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def detect_domain(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ["video moment", "temporal video grounding", "natural language video localization", "vmr"]):
        return "vmr"
    return "generic"


def vmr_defaults() -> dict[str, Any]:
    return {
        "research_questions": [
            "RQ1: Does the proposed training or inference mechanism improve temporal localization under standard VMR metrics?",
            "RQ2: Does the method improve boundary calibration on ambiguous or multi-event queries?",
            "RQ3: Which component is responsible for any gain, and does it transfer across datasets?",
            "RQ4: What are the computational and annotation-cost trade-offs?",
        ],
        "datasets": ["Charades-STA", "ActivityNet Captions", "TACoS", "QVHighlights", "Ego4D-NLQ"],
        "baselines": ["Moment-DETR", "QD-DETR", "UniVTG", "EaTR", "CG-DETR", "TR-DETR"],
        "metrics": ["R@1 IoU=0.3", "R@1 IoU=0.5", "R@1 IoU=0.7", "mIoU", "mAP", "highlight mAP"],
    }


def generic_defaults() -> dict[str, Any]:
    return {
        "research_questions": [
            "RQ1: What falsifiable claim does the proposed method make?",
            "RQ2: Which controlled comparison isolates the proposed mechanism?",
            "RQ3: How robust is the result to data, seed, and hyperparameter changes?",
            "RQ4: What cost or failure mode would change the conclusion?",
        ],
        "datasets": ["Dataset 1", "Dataset 2"],
        "baselines": ["Strong baseline 1", "Strong baseline 2", "Recent baseline 3"],
        "metrics": ["Primary metric", "Secondary metric", "Efficiency metric"],
    }


def load_registry(project_dir: Path) -> dict[str, Any]:
    return read_json(project_dir / "experiments" / "registry.json", default={}) or {}


def summarize_refs(project_dir: Path) -> tuple[int, list[str]]:
    citation_plan = read_jsonl(project_dir / "refs" / "citation_plan.jsonl")
    bib = project_dir / "refs" / "references.bib"
    bib_count = len(re.findall(r"@\w+\s*\{", bib.read_text(encoding="utf-8", errors="ignore"))) if bib.exists() else 0
    anchors: list[str] = []
    for row in citation_plan:
        title = first_nonempty(row.get("title"), row.get("citation_key"), default="")
        depth = first_nonempty(row.get("depth"), row.get("citation_depth"), default="")
        if title and depth in {"A", "B", "C"}:
            anchors.append(f"{depth}: {title}")
        if len(anchors) >= 12:
            break
    return bib_count, anchors


def format_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- TBD"


def registry_experiment_lines(registry: dict[str, Any]) -> list[str]:
    experiments = registry.get("experiments") if isinstance(registry, dict) else None
    if not isinstance(experiments, list) or not experiments:
        return ["- E1: Main comparison, not initialized.", "- E2: Ablation, not initialized.", "- E3: Robustness, not initialized."]
    lines: list[str] = []
    for item in experiments:
        if not isinstance(item, dict):
            continue
        eid = first_nonempty(item.get("id"), default="EX")
        purpose = first_nonempty(item.get("purpose"), item.get("claim"), default="TBD")
        status = first_nonempty(item.get("status"), default="planned")
        metrics = ", ".join(str(x) for x in item.get("metrics", [])[:5]) if isinstance(item.get("metrics"), list) else "TBD"
        lines.append(f"- {eid} ({status}): {purpose} Metrics: {metrics}.")
    return lines or ["- No valid experiments found in registry.json."]


def build_markdown(project_dir: Path, state: dict[str, Any], force_domain: str | None = None) -> str:
    topic = parse_topic_yaml(project_dir / "topic.yaml")
    project = state.get("project", {})
    title = first_nonempty(project.get("title"), topic.get("title"))
    topic_text = first_nonempty(project.get("topic"), topic.get("topic"))
    audience = first_nonempty(project.get("audience"), topic.get("audience"))
    scope = first_nonempty(project.get("scope"), topic.get("scope"))
    angle = first_nonempty(project.get("angle"), topic.get("angle"))
    method_name = first_nonempty(project.get("method_name"), state.get("selected_method_name"), topic.get("method"), default="TBD")
    domain = force_domain or detect_domain(" ".join([title, topic_text, audience, scope, angle, method_name]))
    defaults = vmr_defaults() if domain == "vmr" else generic_defaults()
    registry = load_registry(project_dir)
    bib_count, ref_anchors = summarize_refs(project_dir)
    idea_bank = project_dir / "idea_bank.md"
    idea_note = "See idea_bank.md for candidate ideas and objections." if idea_bank.exists() else "Idea bank is not present yet."
    prereg = project_dir / "experiments" / "preregister.md"
    prereg_note = "Preregistration exists and must remain upstream of results." if prereg.exists() else "Preregistration has not been written yet."

    return f"""# Research Brief

Generated: {now_iso()}

## Working Title

{title}

## Topic And Venue

- Topic: {topic_text}
- Audience / venue: {audience}
- Scope: {scope}
- Angle: {angle}
- Paper type: {first_nonempty(project.get("paper_type"), default="survey")}
- Target score: {first_nonempty(project.get("target_score"), state.get("stop_rules", {}).get("target_score"))}
- Target pages: {first_nonempty(project.get("target_pages"))}

## Method Hypothesis

Method name: {method_name}

The manuscript must be written around a falsifiable mechanism, not a survey-style catalogue. The central claim should be phrased so that one experiment can support it and one credible negative result can weaken it. Claims that depend on real measurements must stay as planned or placeholder text until collected by the results pipeline.

## Research Questions

{format_list(defaults["research_questions"])}

## Datasets

{format_list(defaults["datasets"])}

## Baselines

{format_list(defaults["baselines"])}

## Metrics

{format_list(defaults["metrics"])}

## Experiment Matrix

{chr(10).join(registry_experiment_lines(registry))}

## Evidence And Citation State

- Verified BibTeX entries currently counted: {bib_count}
- Citation plan anchors:
{format_list(ref_anchors)}

## Writing Rules

- Write dense IMRAD-style prose with connected paragraphs, not a list of mini-notes.
- Use the contribution list sparingly; most sections should be flowing prose.
- Every factual claim needs a citation, a result macro, or an explicit planned/untested qualifier.
- Tables should consume macros from results_numbers.tex once results exist.
- Negative or failed experiments must be recorded and may change the thesis.

## Experiment Integrity

- {prereg_note}
- Results may only enter the paper through experiments/results artifacts and collect_paper_results.py.
- Do not manually type performance numbers into LaTeX tables unless they are also recorded in the source JSON.
- Failed runs, partial runs, and unavailable data should remain visible in story/ and experiments/logs/.

## Current Idea Context

{idea_note}

## Deliverables

- research_brief.md and story/00_research_brief.md stay current.
- experiments/registry.json defines the experiment queue.
- experiments/run_queue.md lists commands that can run on local or remote hardware.
- results_numbers.tex contains auto-generated metric macros.
- figures/figure_manifest.json records generated figure provenance.
- gate_report.json must pass before declaring the paper submission-ready.
"""


def build_yaml_like(project_dir: Path, state: dict[str, Any], markdown: str) -> dict[str, Any]:
    project = state.get("project", {})
    domain = detect_domain(markdown)
    defaults = vmr_defaults() if domain == "vmr" else generic_defaults()
    return {
        "generated_at": now_iso(),
        "project_dir": str(project_dir),
        "title": project.get("title"),
        "topic": project.get("topic"),
        "audience": project.get("audience"),
        "paper_type": project.get("paper_type", "survey"),
        "domain": domain,
        "research_questions": defaults["research_questions"],
        "datasets": defaults["datasets"],
        "baselines": defaults["baselines"],
        "metrics": defaults["metrics"],
        "integrity_rules": [
            "No fabricated results.",
            "No uncited factual claims.",
            "Result numbers must flow through source artifacts and results_numbers.tex.",
            "Negative results must be recorded rather than hidden.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a PaperGuru-style research brief for a paper project.")
    parser.add_argument("project_dir")
    parser.add_argument("--domain", choices=["generic", "vmr"], default=None)
    parser.add_argument("--no-story-copy", action="store_true", help="Do not mirror the brief into story/00_research_brief.md.")
    args = parser.parse_args()

    project_dir = project_path(args.project_dir)
    state = read_state(project_dir)
    markdown = build_markdown(project_dir, state, force_domain=args.domain)
    brief_path = project_dir / "research_brief.md"
    brief_path.write_text(markdown, encoding="utf-8")
    if not args.no_story_copy:
        story_dir = ensure_dir(project_dir / "story")
        (story_dir / "00_research_brief.md").write_text(markdown, encoding="utf-8")
    write_json(project_dir / "research_brief.json", build_yaml_like(project_dir, state, markdown))
    state["latest_research_brief"] = str(brief_path)
    state.setdefault("next_actions", [])
    action = "Keep research_brief.md current before drafting, running experiments, or reviewing."
    if action not in state["next_actions"]:
        state["next_actions"].append(action)
    write_state(project_dir, state)
    print(f"Wrote {brief_path}")
    if not args.no_story_copy:
        print(f"Wrote {project_dir / 'story' / '00_research_brief.md'}")


if __name__ == "__main__":
    main()
