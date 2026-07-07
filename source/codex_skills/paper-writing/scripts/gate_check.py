from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from workflow_common import count_bib_entries, load_latest_review, plain_text_from_tex, read_json, read_jsonl, read_state, write_json


def pass_fail(passed: bool, metrics: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    return {"passed": passed, "metrics": metrics, "failures": failures}


ORIGINAL_RESEARCH_QUALITY_DEFAULTS = {
    "min_pages": 7,
    "max_pages": 7,
    "min_words": 5500,
    "min_intro_words": 900,
    "min_related_work_words": 800,
    "min_method_words": 1200,
    "min_experiments_words": 1000,
    "min_analysis_words": 600,
    "min_limitations_words": 150,
    "min_conclusion_words": 120,
    "min_citation_commands": 20,
    "min_intro_citation_commands": 3,
    "min_related_work_citation_commands": 8,
    "min_equation_blocks": 3,
    "min_algorithm_blocks": 1,
    "min_figure_mentions": 4,
    "min_table_mentions": 3,
    "min_avg_paragraph_words": 80,
    "min_long_paragraphs": 12,
    "max_overfull_hboxes": 12,
    "max_overfull_pt": 25.0,
}


def strip_tex_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


def tex_to_plain_text(text: str) -> str:
    text = strip_tex_comments(text)
    text = re.sub(r"\\(?:cite|citep|citet|citealp|parencite|textcite|autocite)\w*\*?(?:\[[^\]]*\])*\{[^}]*\}", " ", text)
    text = re.sub(r"\\(begin|end)\{[^}]+\}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])*(?:\{([^{}]*)\})?", r" \1 ", text)
    text = re.sub(r"[{}$&#_^~\\]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z][A-Za-z0-9\-']*", text))


def body_sources(project_dir: Path) -> list[tuple[str, str]]:
    main = project_dir / "main.tex"
    section_files = sorted((project_dir / "sections").glob("*.tex"))
    if not main.exists():
        return []
    main_text = main.read_text(encoding="utf-8", errors="ignore")
    abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", main_text, re.S | re.I)
    sources: list[tuple[str, str]] = []
    if abstract_match:
        sources.append(("abstract", abstract_match.group(1)))
    if section_files:
        sources.extend((str(path.relative_to(project_dir)), path.read_text(encoding="utf-8", errors="ignore")) for path in section_files)
    else:
        sources.append(("main.tex", main_text))
    return sources


def all_tex_text(project_dir: Path, include_tables: bool = True) -> str:
    paths = [project_dir / "main.tex", *sorted((project_dir / "sections").glob("*.tex"))]
    if include_tables:
        paths.extend(sorted((project_dir / "tables").glob("*.tex")))
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in paths if path.exists())


def infer_section_key(name: str, raw: str) -> str:
    title_match = re.search(r"\\section\*?\{([^}]+)\}", raw, re.I)
    label = f"{name} {title_match.group(1) if title_match else ''}".lower()
    if "abstract" in label:
        return "abstract"
    if "intro" in label:
        return "introduction"
    if "related" in label or "prior work" in label:
        return "related_work"
    if "method" in label or "approach" in label or "model" in label:
        return "method"
    if "experiment" in label or "evaluation" in label:
        return "experiments"
    if "analysis" in label or "ablation" in label:
        return "analysis"
    if "limitation" in label:
        return "limitations"
    if "conclusion" in label:
        return "conclusion"
    if "reproduc" in label or "checklist" in label:
        return "reproducibility"
    return "other"


def citation_command_count(raw: str) -> int:
    return len(re.findall(r"\\(?:cite|citep|citet|citealp|parencite|textcite|autocite)\w*\*?(?:\[[^\]]*\])*\{[^}]+\}", raw))


def citation_key_count(raw: str) -> int:
    total = 0
    for match in re.findall(r"\\(?:cite|citep|citet|citealp|parencite|textcite|autocite)\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}", raw):
        total += len([key for key in match.split(",") if key.strip()])
    return total


def paragraph_word_counts(sources: list[tuple[str, str]]) -> list[int]:
    counts: list[int] = []
    for _, raw in sources:
        for paragraph in re.split(r"\n\s*\n", strip_tex_comments(raw)):
            words = count_words(tex_to_plain_text(paragraph))
            if words >= 20:
                counts.append(words)
    return counts


def pdf_page_count(project_dir: Path, compile_report: dict[str, Any]) -> int | None:
    pdf_value = compile_report.get("pdf")
    pdf_path = Path(pdf_value) if pdf_value else project_dir / "build" / "main.pdf"
    if not pdf_path.is_absolute():
        pdf_path = project_dir / pdf_path
    if pdf_path.exists() and shutil.which("pdfinfo"):
        try:
            result = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, timeout=10)
            match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.M)
            if match:
                return int(match.group(1))
        except Exception:
            pass
    tail = str(compile_report.get("output_tail", ""))
    match = re.search(r"Output written on .*?\((\d+)\s+pages?", tail, re.S | re.I)
    return int(match.group(1)) if match else None


def log_layout_metrics(project_dir: Path) -> dict[str, Any]:
    log_path = project_dir / "build" / "main.log"
    log = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
    overfull_values = [float(value) for value in re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log)]
    return {
        "overfull_hbox_count": len(overfull_values),
        "max_overfull_pt": max(overfull_values) if overfull_values else 0.0,
        "underfull_hbox_count": len(re.findall(r"Underfull \\hbox", log)),
    }


def quality_thresholds(state: dict[str, Any]) -> dict[str, Any]:
    thresholds = dict(ORIGINAL_RESEARCH_QUALITY_DEFAULTS)
    project = state.get("project", {})
    if project.get("target_pages"):
        thresholds["min_pages"] = int(project["target_pages"])
        # AAAI main technical track page limits are normally stated for the
        # main paper body, with references allowed after the body. The compiled
        # PDF page count includes references, so allow a small bibliography
        # budget while still failing long manuscripts.
        thresholds["max_pages"] = int(project["target_pages"]) + int(project.get("reference_page_budget", 2))
        if int(project["target_pages"]) <= 7:
            thresholds["min_words"] = min(int(thresholds.get("min_words", 4200)), 3800)
            thresholds["min_intro_words"] = min(int(thresholds.get("min_intro_words", 700)), 450)
            thresholds["min_method_words"] = min(int(thresholds.get("min_method_words", 900)), 900)
            thresholds["min_experiments_words"] = min(int(thresholds.get("min_experiments_words", 600)), 500)
            thresholds["min_analysis_words"] = min(int(thresholds.get("min_analysis_words", 300)), 260)
            thresholds["min_limitations_words"] = min(int(thresholds.get("min_limitations_words", 100)), 100)
            thresholds["min_conclusion_words"] = min(int(thresholds.get("min_conclusion_words", 80)), 80)
            thresholds["min_long_paragraphs"] = min(int(thresholds.get("min_long_paragraphs", 8)), 8)
    configured = state.get("quality_gates", {})
    if isinstance(configured, dict):
        thresholds.update(configured.get("submission_quality", {}))
        thresholds.update(configured.get("original_research", {}))
    return thresholds


def gate_literature(project_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    paper_type = state.get("project", {}).get("paper_type", "survey")
    scored = read_jsonl(project_dir / "refs" / "scored_candidates.jsonl")
    plan = read_jsonl(project_dir / "refs" / "citation_plan.jsonl")
    verification = read_json(project_dir / "refs" / "verification_report.json", default={})
    bib_count = count_bib_entries(project_dir / "refs" / "references.bib")
    target_pages = int(state.get("project", {}).get("target_pages", 50))
    if paper_type == "original_research":
        final_min = 30
        max_refs = 60
    else:
        final_min = max(80, target_pages * 3)
        max_refs = None
    current_year = 2026
    included = [row for row in scored if row.get("citation_depth") != "D"]
    within_1yr = [row for row in included if row.get("year") and current_year - int(row["year"]) <= 1]
    within_3yr = [row for row in included if row.get("year") and current_year - int(row["year"]) <= 3]
    accepted = [row for row in included if str(row.get("acceptance_status", "")).lower() == "accepted" or str(row.get("venue", "")).lower() not in {"arxiv", ""}]
    arxiv_only = [row for row in included if str(row.get("venue", "")).lower() == "arxiv"]
    key_terms = {
        "moment_detr": re.compile(r"moment[- ]?detr", re.I),
        "qd_detr": re.compile(r"qd[- ]?detr", re.I),
        "univtg": re.compile(r"univtg", re.I),
        "eatr": re.compile(r"\beatr\b|event[- ]?aware", re.I),
        "cg_detr": re.compile(r"cg[- ]?detr|correlat", re.I),
        "llm_grounding": re.compile(r"llava|large language model|video[- ]?llm|multimodal", re.I),
        "long_video_or_nlq": re.compile(r"long[- ]?video|ego4d|natural language quer", re.I),
        "boundary_uncertainty": re.compile(r"boundary|temporal localization|moment retrieval", re.I),
    }
    corpus = "\n".join(" ".join(str(row.get(k, "")) for k in ["title", "summary", "venue"]) for row in included)
    coverage = {name: bool(pattern.search(corpus)) for name, pattern in key_terms.items()}
    cells: dict[str, int] = {}
    for row in plan:
        if row.get("depth") in {"A", "B"}:
            cell = row.get("taxonomy_cell") or "unassigned"
            cells[cell] = cells.get(cell, 0) + 1
    metrics = {
        "paper_type": paper_type,
        "bib_count": bib_count,
        "final_min_references": final_min,
        "max_references": max_refs,
        "included_candidates": len(included),
        "within_1yr_ratio": round(len(within_1yr) / max(1, len(included)), 3),
        "within_3yr_ratio": round(len(within_3yr) / max(1, len(included)), 3),
        "accepted_ratio": round(len(accepted) / max(1, len(included)), 3),
        "arxiv_only_ratio": round(len(arxiv_only) / max(1, len(included)), 3),
        "verification_rate": verification.get("verification_rate", 0),
        "taxonomy_cells_with_ab_refs": cells,
        "vmr_coverage": coverage,
    }
    failures = []
    if paper_type == "original_research":
        if bib_count < final_min:
            failures.append("AAAI original research requires at least 30 high-relevance references.")
        if max_refs is not None and bib_count > max_refs:
            failures.append("AAAI original research should stay focused: references exceed 60.")
        if metrics["within_3yr_ratio"] < 0.45 and included:
            failures.append("Recent VMR coverage weak: within-3-year reference ratio below 45%.")
        missing = [name for name, present in coverage.items() if not present]
        if missing:
            failures.append(f"Missing required VMR literature coverage: {', '.join(missing)}.")
    else:
        if bib_count < 80:
            failures.append("Draft requires at least 80 references.")
        if state.get("phase") == "phase_3_sprint" and bib_count < final_min:
            failures.append(f"Final requires at least pages*3 references ({final_min}).")
        if metrics["within_1yr_ratio"] < 0.40 and included:
            failures.append("Within-1-year reference ratio below 40%.")
        if metrics["accepted_ratio"] < 0.30 and included:
            failures.append("Accepted reference ratio below 30%.")
        if metrics["arxiv_only_ratio"] > 0.60 and included:
            failures.append("arXiv-only reference ratio above 60%.")
        if not cells:
            failures.append("No A/B references assigned to taxonomy cells.")
    if metrics["verification_rate"] < 0.80:
        failures.append("BibTeX verification rate below 80% or verify_bib.py not run.")
    return pass_fail(not failures, metrics, failures)


def gate_experiment(project_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    paper_type = state.get("project", {}).get("paper_type", "survey")
    prereg = project_dir / "experiments" / "preregister.md"
    results = read_json(project_dir / "experiments" / "results.json", default={})
    todo_runs = project_dir / "experiments" / "todo_runs.md"
    todo_text = todo_runs.read_text(encoding="utf-8", errors="ignore") if todo_runs.exists() else ""
    current_remote = state.get("current_remote_experiment", {}) if isinstance(state.get("current_remote_experiment"), dict) else {}
    sync_audit_path = project_dir / str(current_remote.get("sync_audit", "experiments/dream_remote_sync_audit.json"))
    sync_audit = read_json(sync_audit_path, default={}) if sync_audit_path.exists() else {}
    status = str(results.get("status", "")).lower()
    planned_only = status in {"not_run", "planned", "pending", "todo", "unavailable"} or bool(results.get("planned"))
    has_executable_plan = todo_runs.exists() and len(todo_text.strip()) > 300 and bool(re.search(r"\b(python|bash|powershell|conda|pip|git|CUDA|dataset|metric|R@1|mIoU|mAP)\b", todo_text, re.I))
    metrics = {
        "paper_type": paper_type,
        "status": status or None,
        "planned_only": planned_only,
        "has_preregister": prereg.exists() and len(prereg.read_text(encoding="utf-8", errors="ignore").strip()) > 200,
        "has_results": bool(results),
        "trials": results.get("trials") or results.get("n_trials") or 0,
        "has_statistics": bool(results.get("statistics") or results.get("confidence_interval") or results.get("p_value")),
        "linked_claim": bool(results.get("linked_claim") or results.get("paper_claim")),
        "ceiling_floor_checked": bool(results.get("ceiling_floor_check")),
        "datasets": results.get("datasets", []),
        "baselines": results.get("baselines", []),
        "ablations": results.get("ablations", []),
        "robustness": results.get("robustness", []),
        "efficiency": results.get("efficiency", {}),
        "todo_runs_exists": todo_runs.exists(),
        "has_executable_plan": has_executable_plan,
        "current_remote_experiment": current_remote,
        "sync_audit_exists": sync_audit_path.exists(),
        "sync_audit_paper_ready": sync_audit.get("paper_ready") if sync_audit else None,
        "sync_audit_remote_state": sync_audit.get("remote", {}).get("state") if isinstance(sync_audit.get("remote"), dict) else None,
    }
    failures = []
    if not metrics["has_preregister"]:
        failures.append("Missing substantial experiments/preregister.md.")
    if not metrics["has_results"]:
        failures.append("Missing experiments/results.json.")
    if not metrics["linked_claim"]:
        failures.append("Experiment must link to a specific paper claim.")
    if paper_type == "original_research" and planned_only:
        if not metrics["has_executable_plan"]:
            failures.append("Planned-only original research requires executable experiments/todo_runs.md with commands, datasets, and metrics.")
        if len(metrics["datasets"]) < 2:
            failures.append("AAAI original research experiment plan needs at least 2 standard datasets.")
        if len(metrics["baselines"]) < 6:
            failures.append("AAAI original research experiment plan needs at least 6 strong baselines.")
        if len(metrics["ablations"]) < 4:
            failures.append("AAAI original research experiment plan needs at least 4 ablations.")
        if len(metrics["robustness"]) < 1:
            failures.append("AAAI original research experiment plan needs at least 1 robustness study.")
        if not metrics["efficiency"]:
            failures.append("AAAI original research experiment plan needs an efficiency analysis item.")
    else:
        if int(metrics["trials"] or 0) < 3:
            failures.append("Executed experiments require at least 3 trials.")
        if not metrics["has_statistics"]:
            failures.append("Executed experiments require p-value, confidence interval, or statistical summary.")
        if not metrics["ceiling_floor_checked"]:
            failures.append("Executed experiments must document ceiling/floor effect check.")
    if paper_type == "original_research" and current_remote:
        if not sync_audit_path.exists():
            failures.append("Declared full-backbone remote experiment requires experiments/dream_remote_sync_audit.json.")
        elif sync_audit.get("paper_ready") is not True:
            failures.append("Declared DREAM full-backbone experiment is not paper-ready; final metrics/log artifacts are not synced.")
    return pass_fail(not failures, metrics, failures)


def gate_structure(project_dir: Path) -> dict[str, Any]:
    state = read_state(project_dir)
    paper_type = state.get("project", {}).get("paper_type", "survey")
    main = project_dir / "main.tex"
    section_files = sorted((project_dir / "sections").glob("*.tex"))
    compile_report = read_json(project_dir / "build" / "compile_report.json", default={})
    text = " ".join(plain_text_from_tex(path) for path in section_files)
    line_violations = [str(path.relative_to(project_dir)) for path in section_files if len(path.read_text(encoding="utf-8", errors="ignore").splitlines()) > 300]
    metrics = {
        "paper_type": paper_type,
        "has_main_tex": main.exists(),
        "section_count": len(section_files),
        "compile_success": compile_report.get("success") is True,
        "undefined_refs": compile_report.get("undefined_references", 0),
        "line_violations": line_violations,
        "has_abstract_terms": bool(re.search(r"\babstract\b", main.read_text(encoding="utf-8", errors="ignore"), re.I)) if main.exists() else False,
        "has_conclusion": bool(re.search(r"\bconclusion\b", text, re.I)),
        "has_critical_assessment": bool(re.search(r"critical assessment|limitation|trade-?off|gap", text, re.I)),
        "has_formal_claim": bool(re.search(r"conjecture|observation|proposition|hypothesis", text, re.I)),
        "has_method_section": bool(re.search(r"\\section\{[^}]*Method|\\section\{[^}]*Approach", tex_text := "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in [main, *section_files] if path.exists()), re.I)),
        "has_experiment_section": bool(re.search(r"\\section\{[^}]*Experiment", tex_text, re.I)),
        "has_related_work": bool(re.search(r"\\section\{[^}]*Related Work", tex_text, re.I)),
        "has_limitations": bool(re.search(r"\\section\{[^}]*Limitation", tex_text, re.I)),
        "has_reproducibility": bool(re.search(r"Reproducibility Checklist|\\section\{[^}]*Reproduc", tex_text, re.I)),
    }
    failures = []
    if not metrics["has_main_tex"]:
        failures.append("Missing main.tex.")
    if metrics["section_count"] < 6:
        failures.append("Expected at least 6 section files.")
    if not metrics["compile_success"]:
        failures.append("LaTeX compile did not succeed or compile_latex.ps1 not run.")
    if metrics["undefined_refs"]:
        failures.append("Undefined LaTeX references detected.")
    if line_violations:
        failures.append("Some section .tex files exceed 300 lines.")
    if not metrics["has_conclusion"]:
        failures.append("Conclusion section missing.")
    if paper_type == "original_research":
        for key, label in [
            ("has_method_section", "Method section"),
            ("has_experiment_section", "Experiments section"),
            ("has_related_work", "Related Work section"),
            ("has_limitations", "Limitations section"),
            ("has_reproducibility", "Reproducibility Checklist"),
        ]:
            if not metrics[key]:
                failures.append(f"AAAI original research missing {label}.")
        if not metrics["has_formal_claim"]:
            failures.append("Need at least one formal hypothesis or problem definition.")
    else:
        if not metrics["has_critical_assessment"]:
            failures.append("Core manuscript lacks critical assessment language.")
        if not metrics["has_formal_claim"]:
            failures.append("Need at least one formal claim: conjecture, observation, proposition, or hypothesis.")
    return pass_fail(not failures, metrics, failures)


def gate_figures_tables(project_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    paper_type = state.get("project", {}).get("paper_type", "survey")
    figures = list((project_dir / "figures").glob("*.pdf")) + list((project_dir / "figures").glob("*.png"))
    all_tables = list((project_dir / "tables").glob("*.tex"))
    tex_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in [project_dir / "main.tex", *sorted((project_dir / "sections").glob("*.tex"))] if path.exists())
    used_table_names = set(re.findall(r"\\input\{tables/([^}]+)\}", tex_text))
    tables = [path for path in all_tables if path.stem in used_table_names or path.name in used_table_names]
    table_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in tables)
    figure_labels = re.findall(r"\\label\{(fig:[^}]+)\}", tex_text)
    table_labels = re.findall(r"\\label\{(tab:[^}]+)\}", tex_text + table_text)
    refs = set(re.findall(r"\\(?:ref|autoref|cref)\{([^}]+)\}", tex_text))
    metrics = {
        "paper_type": paper_type,
        "figure_count": len(figures),
        "table_count": len(tables),
        "unreferenced_figure_labels": sorted(set(figure_labels) - refs),
        "unreferenced_table_labels": sorted(set(table_labels) - refs),
        "uses_booktabs": "\\toprule" in table_text and "\\bottomrule" in table_text if tables else False,
        "has_vertical_table_lines": bool(re.search(r"\\begin\{tabular\}\{[^}]*\|", table_text)),
        "has_method_figure": bool(re.search(r"method|architecture|framework", tex_text, re.I)),
        "has_main_results": bool(re.search(r"main result|overall performance|r@1|miou|map", table_text + tex_text, re.I)),
        "has_ablation": bool(re.search(r"ablation", table_text + tex_text, re.I)),
        "has_qualitative_or_error": bool(re.search(r"qualitative|case study|error analysis|failure", table_text + tex_text, re.I)),
    }
    failures = []
    phase = state.get("phase")
    if paper_type == "original_research":
        if len(figures) < 1:
            failures.append("AAAI original research requires at least one method/architecture figure.")
        if len(tables) < 2:
            failures.append("AAAI original research requires at least main result and ablation/analysis tables.")
        for key, label in [
            ("has_method_figure", "method figure reference"),
            ("has_main_results", "main results table/text"),
            ("has_ablation", "ablation analysis"),
            ("has_qualitative_or_error", "qualitative or error analysis"),
        ]:
            if not metrics[key]:
                failures.append(f"AAAI original research missing {label}.")
    elif phase == "phase_3_sprint":
        if len(tables) < 10:
            failures.append("Full survey sprint gate expects at least 10 tables.")
        if len(figures) < 6:
            failures.append("Full survey sprint gate expects at least 6 figures.")
    else:
        if len(tables) + len(figures) < 2:
            failures.append("Draft requires at least 2 figures/tables.")
    if tables and not metrics["uses_booktabs"]:
        failures.append("Tables should use booktabs style.")
    if metrics["has_vertical_table_lines"]:
        failures.append("Tables must not use vertical lines.")
    if metrics["unreferenced_figure_labels"]:
        failures.append("Some figure labels are not referenced in text.")
    if metrics["unreferenced_table_labels"]:
        failures.append("Some table labels are not referenced in text.")
    return pass_fail(not failures, metrics, failures)


def gate_research_pipeline(project_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    paper_type = state.get("project", {}).get("paper_type", "survey")
    brief = project_dir / "research_brief.md"
    story_brief = project_dir / "story" / "00_research_brief.md"
    registry_path = project_dir / "experiments" / "registry.json"
    run_queue = project_dir / "experiments" / "run_queue.md"
    paper_numbers_path = project_dir / "experiments" / "paper_numbers.json"
    results_numbers = project_dir / "results_numbers.tex"
    figure_manifest_path = project_dir / "figures" / "figure_manifest.json"
    registry = read_json(registry_path, default={}) or {}
    paper_numbers = read_json(paper_numbers_path, default={}) or {}
    figure_manifest = read_json(figure_manifest_path, default={}) or {}
    experiments = registry.get("experiments", []) if isinstance(registry, dict) else []
    macro_plan = registry.get("macro_plan", []) if isinstance(registry, dict) else []
    story_files = sorted((project_dir / "story").glob("*.md")) if (project_dir / "story").exists() else []
    run_queue_text = run_queue.read_text(encoding="utf-8", errors="ignore") if run_queue.exists() else ""
    results_tex = results_numbers.read_text(encoding="utf-8", errors="ignore") if results_numbers.exists() else ""
    experiment_field_failures: list[str] = []
    for exp in (experiments if isinstance(experiments, list) else []):
        if not isinstance(exp, dict):
            experiment_field_failures.append("Experiment entry is not an object.")
            continue
        missing = [key for key in ["id", "name", "claim", "purpose", "datasets", "baselines", "metrics", "commands", "expected_outputs", "paper_targets"] if not exp.get(key)]
        if missing:
            experiment_field_failures.append(f"{exp.get('id', 'unknown')}: missing {', '.join(missing)}")
    metrics = {
        "paper_type": paper_type,
        "has_research_brief": brief.exists() and len(brief.read_text(encoding="utf-8", errors="ignore").strip()) > 800,
        "has_story_brief": story_brief.exists() and len(story_brief.read_text(encoding="utf-8", errors="ignore").strip()) > 800,
        "story_file_count": len(story_files),
        "has_registry": registry_path.exists(),
        "experiment_count": len(experiments) if isinstance(experiments, list) else 0,
        "macro_plan_count": len(macro_plan) if isinstance(macro_plan, list) else 0,
        "experiment_field_failures": experiment_field_failures,
        "has_run_queue": run_queue.exists() and bool(re.search(r"\b(python|bash|powershell|ssh|conda|pip)\b", run_queue_text, re.I)),
        "has_results_numbers_tex": results_numbers.exists(),
        "results_numbers_is_generated": "collect_paper_results.py" in results_tex or "Auto-generated" in results_tex,
        "has_paper_numbers_audit": paper_numbers_path.exists() and bool(paper_numbers),
        "paper_number_macros": paper_numbers.get("macro_count", 0) if isinstance(paper_numbers, dict) else 0,
        "paper_number_filled": paper_numbers.get("filled_count", 0) if isinstance(paper_numbers, dict) else 0,
        "paper_number_placeholders": paper_numbers.get("placeholder_count", 0) if isinstance(paper_numbers, dict) else 0,
        "has_figure_manifest": figure_manifest_path.exists() and bool(figure_manifest),
        "figure_manifest_status": figure_manifest.get("status") if isinstance(figure_manifest, dict) else None,
        "remote_base_dir": registry.get("remote", {}).get("base_dir") if isinstance(registry.get("remote"), dict) else None,
    }
    failures: list[str] = []
    if paper_type != "original_research":
        return pass_fail(True, metrics, failures)

    if not metrics["has_research_brief"]:
        failures.append("Missing substantial research_brief.md; run build_research_brief.py.")
    if not metrics["has_story_brief"]:
        failures.append("Missing story/00_research_brief.md; keep a research memory trail.")
    if metrics["story_file_count"] < 1:
        failures.append("Missing story/*.md research memory files.")
    if not metrics["has_registry"]:
        failures.append("Missing experiments/registry.json; run init_experiment_registry.py.")
    if metrics["experiment_count"] < 3:
        failures.append("Experiment registry needs at least E1 main, E2 ablation, and E3 robustness experiments.")
    if experiment_field_failures:
        failures.append("Experiment registry entries are incomplete: " + "; ".join(experiment_field_failures[:5]))
    if not metrics["has_run_queue"]:
        failures.append("Missing executable experiments/run_queue.md with commands.")
    if not metrics["has_results_numbers_tex"] or not metrics["results_numbers_is_generated"]:
        failures.append("Missing generated results_numbers.tex; run collect_paper_results.py.")
    if not metrics["has_paper_numbers_audit"]:
        failures.append("Missing experiments/paper_numbers.json source audit; run collect_paper_results.py.")
    if not metrics["has_figure_manifest"]:
        failures.append("Missing figures/figure_manifest.json; run generate_paper_figures.py.")
    return pass_fail(not failures, metrics, failures)


def gate_submission_quality(project_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    paper_type = state.get("project", {}).get("paper_type", "survey")
    thresholds = quality_thresholds(state)
    sources = body_sources(project_dir)
    raw_tex = all_tex_text(project_dir)
    main_text = (project_dir / "main.tex").read_text(encoding="utf-8", errors="ignore") if (project_dir / "main.tex").exists() else ""
    compile_report = read_json(project_dir / "build" / "compile_report.json", default={})
    paragraph_counts = paragraph_word_counts(sources)
    section_words: dict[str, int] = {}
    section_citations: dict[str, int] = {}
    for name, raw in sources:
        key = infer_section_key(name, raw)
        section_words[key] = section_words.get(key, 0) + count_words(tex_to_plain_text(raw))
        section_citations[key] = section_citations.get(key, 0) + citation_command_count(raw)
    target_text = " ".join(
        str(state.get("project", {}).get(key, ""))
        for key in ["audience", "target_venue", "scope", "topic", "title"]
    )
    target_is_aaai = bool(re.search(r"\bAAAI\b", target_text, re.I))
    aaai_template_pattern = r"\\usepackage(?:\[[^\]]*\])?\{aaai\d*|\\documentclass(?:\[[^\]]*\])?\{aaai\d*"
    figure_mentions = len(re.findall(r"\\(?:ref|autoref|cref)\{fig:[^}]+\}|(?:Figure|Fig\.)\s*\d+", raw_tex, re.I))
    table_mentions = len(re.findall(r"\\(?:ref|autoref|cref)\{tab:[^}]+\}|Table\s*\d+", raw_tex, re.I))
    equation_blocks = len(re.findall(r"\\begin\{(?:equation|align|alignat|gather|multline)\*?\}|\\\[|\$\$", raw_tex))
    algorithm_blocks = len(re.findall(r"\\begin\{(?:algorithm|algorithmic|algorithm2e)\*?\}", raw_tex, re.I))
    layout = log_layout_metrics(project_dir)
    avg_para_words = round(sum(paragraph_counts) / max(1, len(paragraph_counts)), 1)
    metrics = {
        "paper_type": paper_type,
        "thresholds": thresholds,
        "pdf_pages": pdf_page_count(project_dir, compile_report),
        "total_words": sum(section_words.values()),
        "section_words": section_words,
        "paragraph_count": len(paragraph_counts),
        "avg_paragraph_words": avg_para_words,
        "median_paragraph_words": sorted(paragraph_counts)[len(paragraph_counts) // 2] if paragraph_counts else 0,
        "long_paragraphs_120w": sum(1 for value in paragraph_counts if value >= 120),
        "citation_commands": citation_command_count(raw_tex),
        "citation_keys": citation_key_count(raw_tex),
        "section_citation_commands": section_citations,
        "equation_blocks": equation_blocks,
        "algorithm_blocks": algorithm_blocks,
        "figure_mentions": figure_mentions,
        "table_mentions": table_mentions,
        "target_is_aaai": target_is_aaai,
        "uses_aaai_template": bool(re.search(aaai_template_pattern, main_text, re.I)),
        "anonymous_submission_marker": bool(re.search(r"anonymous|author\(s\) omitted|\\author\{\s*Anonymous", main_text, re.I)),
        **layout,
    }
    failures: list[str] = []
    if paper_type != "original_research":
        return pass_fail(True, metrics, failures)

    if metrics["pdf_pages"] is None:
        failures.append("Submission-quality gate requires a compiled PDF page count; run compile_latex.ps1 first.")
    elif int(metrics["pdf_pages"]) < int(thresholds["min_pages"]):
        failures.append(f"Original research manuscript is too short: {metrics['pdf_pages']} pages < {thresholds['min_pages']} required pages.")
    elif int(thresholds.get("max_pages") or 0) and int(metrics["pdf_pages"]) > int(thresholds["max_pages"]):
        failures.append(f"Original research manuscript exceeds target length: {metrics['pdf_pages']} pages > {thresholds['max_pages']} target pages.")
    if metrics["total_words"] < int(thresholds["min_words"]):
        failures.append(f"Original research manuscript is too thin: {metrics['total_words']} words < {thresholds['min_words']} required words.")
    section_requirements = [
        ("introduction", "min_intro_words", "Introduction"),
        ("related_work", "min_related_work_words", "Related Work"),
        ("method", "min_method_words", "Method"),
        ("experiments", "min_experiments_words", "Experiments"),
        ("analysis", "min_analysis_words", "Analysis/Ablation"),
        ("limitations", "min_limitations_words", "Limitations"),
        ("conclusion", "min_conclusion_words", "Conclusion"),
    ]
    for key, threshold_key, label in section_requirements:
        if section_words.get(key, 0) < int(thresholds[threshold_key]):
            failures.append(f"{label} is underdeveloped: {section_words.get(key, 0)} words < {thresholds[threshold_key]}.")
    if metrics["avg_paragraph_words"] < float(thresholds["min_avg_paragraph_words"]):
        failures.append(f"Paragraphs are too short on average: {metrics['avg_paragraph_words']} words < {thresholds['min_avg_paragraph_words']}.")
    if metrics["long_paragraphs_120w"] < int(thresholds["min_long_paragraphs"]):
        failures.append(f"Not enough deep paragraphs: {metrics['long_paragraphs_120w']} paragraphs >=120 words < {thresholds['min_long_paragraphs']}.")
    if metrics["citation_commands"] < int(thresholds["min_citation_commands"]):
        failures.append(f"Citation weaving is too sparse: {metrics['citation_commands']} citation commands < {thresholds['min_citation_commands']}.")
    if section_citations.get("introduction", 0) < int(thresholds["min_intro_citation_commands"]):
        failures.append("Introduction needs more cited problem-gap support.")
    if section_citations.get("related_work", 0) < int(thresholds["min_related_work_citation_commands"]):
        failures.append("Related Work needs denser citation weaving.")
    if equation_blocks < int(thresholds["min_equation_blocks"]):
        failures.append(f"Method formalism is weak: {equation_blocks} equation blocks < {thresholds['min_equation_blocks']}.")
    if algorithm_blocks < int(thresholds["min_algorithm_blocks"]):
        failures.append("Method needs at least one algorithm/pseudocode block.")
    if figure_mentions < int(thresholds["min_figure_mentions"]):
        failures.append(f"Figure narrative is too sparse: {figure_mentions} figure mentions < {thresholds['min_figure_mentions']}.")
    if table_mentions < int(thresholds["min_table_mentions"]):
        failures.append(f"Table narrative is too sparse: {table_mentions} table mentions < {thresholds['min_table_mentions']}.")
    if target_is_aaai and not metrics["uses_aaai_template"]:
        failures.append("AAAI target detected but main.tex does not use an AAAI style/package.")
    if target_is_aaai and not metrics["anonymous_submission_marker"]:
        failures.append("AAAI double-blind target needs an anonymous author marker in main.tex.")
    if metrics["overfull_hbox_count"] > int(thresholds["max_overfull_hboxes"]):
        failures.append(f"Too many overfull hboxes: {metrics['overfull_hbox_count']} > {thresholds['max_overfull_hboxes']}.")
    if metrics["max_overfull_pt"] > float(thresholds["max_overfull_pt"]):
        failures.append(f"Severe layout overflow: max overfull hbox {metrics['max_overfull_pt']}pt > {thresholds['max_overfull_pt']}pt.")
    return pass_fail(not failures, metrics, failures)


def gate_final_review(project_dir: Path, gates: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    review_path, review = load_latest_review(project_dir)
    target = float(state.get("stop_rules", {}).get("target_score", 8.5))
    score = review.get("median_score") if review else None
    prerequisite_names = ["literature", "experiment", "structure", "figures_tables", "research_pipeline", "submission_quality"]
    metrics = {
        "latest_review": str(review_path.name) if review_path else None,
        "median_score": score,
        "target_score": target,
        "prerequisite_gates": prerequisite_names,
        "prerequisite_gates_passed": all(gates[name]["passed"] for name in prerequisite_names),
        "regression_check_present": bool(review and "previous_fix_regression_check" in review),
    }
    failures = []
    if not review:
        failures.append("No review_round_N.json found.")
    if score is None or float(score) < target:
        failures.append("Latest median review score below target.")
    if not metrics["prerequisite_gates_passed"]:
        failures.append("One or more prerequisite gates failed.")
    if not metrics["regression_check_present"]:
        failures.append("Review must include previous_fix_regression_check.")
    return pass_fail(not failures, metrics, failures)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run strict quality gates for a paper project.")
    parser.add_argument("project_dir")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    state = read_state(project_dir)
    gates = {
        "literature": gate_literature(project_dir, state),
        "experiment": gate_experiment(project_dir, state),
        "structure": gate_structure(project_dir),
        "figures_tables": gate_figures_tables(project_dir, state),
        "research_pipeline": gate_research_pipeline(project_dir, state),
        "submission_quality": gate_submission_quality(project_dir, state),
    }
    gates["final_review"] = gate_final_review(project_dir, gates, state)
    report = {
        "all_passed": all(gate["passed"] for gate in gates.values()),
        "gates": gates,
    }
    write_json(project_dir / "gate_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
