---
name: paper-writing
description: Autonomous scientific paper and survey writing workflow for Codex. Use when the user wants to plan, write, compile, review, and iteratively improve a research paper, especially long-form survey papers with literature search, BibTeX management, experiments, figures, tables, peer-review simulation, quality gates, and multi-round autonomous revision.
---

# Paper Writing

## Purpose

Use this skill to run a strict local paper-production workflow. Treat every paper as a resumable project with state, artifacts, gates, review history, and version snapshots.

This skill recreates the public `paper_writing` workflow: literature survey, paper structure, experiment design, figures/tables, and peer-review simulation. Internal infrastructure from the original system is replaced by local scripts and Codex-driven iteration.

## First Step

For a new paper, initialize a project before writing:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\init_project.py <workspace>\projects\<slug> --title "<paper title>" --topic "<topic>" --audience "<target venue or audience>"
```

Then start the loop:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\next_iteration.py <workspace>\projects\<slug> --advance
```

For original research, create the PaperGuru-style research and experiment control files before drafting results-facing prose:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\build_research_brief.py <workspace>\projects\<slug>
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\init_experiment_registry.py <workspace>\projects\<slug> --domain vmr
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\collect_paper_results.py <workspace>\projects\<slug> --patch-main
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\generate_paper_figures.py <workspace>\projects\<slug>
```

Read the generated `iteration_brief.md`, execute the required work, run relevant scripts, then compile, review, route weaknesses, run gates, and snapshot.

## Iteration Contract

Never skip the state machine. Each iteration must do the following:

1. Run `next_iteration.py --advance` and follow its required subskills.
2. Update or create the expected artifacts for that iteration.
3. Run automated checks that correspond to the work performed.
4. Compile LaTeX whenever manuscript files changed.
5. Run or update peer-review simulation at review iterations.
6. Run `gate_check.py` and inspect failures.
7. Run `snapshot_version.py` after meaningful progress.

Stop only when one of these is true:

- Latest median review score is at least the project target and all gates pass.
- Score improvement is at most 0.3 for two consecutive review rounds.
- Maximum iteration count is reached.

## Subskills

Use the reference files only when needed:

- Literature survey: read `references/literature.md`. For durable online-to-local paper libraries, also read `references/literature_library.md` and use `harvest_literature_library.py` plus `search_local_library.py`. Use `search_openalex.py`, `search_semantic_scholar.py`, `search_literature.py`, `upgrade_venues.py`, `score_lqs.py`, and `verify_bib.py`.
- Fine-grained idea mining: use `build_finegrained_idea_graph.py` for bottom-up paper analysis. It reads Abstract and Introduction evidence only, extracts motivation chains and atomic problem/method units, separates adjacent tasks, derives data-dependent taxonomies, and generates evidence-traceable transfer ideas. Run `--sanity-only --strict` before the full `--strict` rebuild. Keep `build_idea_graph.py` only for legacy coarse-file compatibility.
- Paper structure and logic: read `references/structure.md`.
- Experiment design: read `references/experiment.md`.
- Figures and tables: read `references/figures_tables.md`.
- Peer review and weakness routing: read `references/peer_review.md` and use `route_review.py`.
- Full workflow and gates: read `references/workflow_gates.md`.

## Required Project Artifacts

Every project must keep this shape:

```text
topic.yaml
state.json
research_brief.md
research_brief.json
iteration_brief.md
main.tex
results_numbers.tex
refs/
  raw_candidates.jsonl
  scored_candidates.jsonl
  citation_plan.jsonl
  references.bib
  verification_report.json
sections/
story/
  00_research_brief.md
code/
experiments/
  registry.json
  run_queue.md
  preregister.md
  results.json
  results/
  logs/
  paper_numbers.json
figures/
  figure_manifest.json
tables/
reviews/
build/
snapshots/
```

If an artifact is missing, create the smallest truthful version needed for the current iteration. Do not fabricate citations, venues, experiment results, or review scores.

## PaperGuru-Style Research Loop

For original research, the manuscript should be downstream of a research-control loop rather than a one-shot drafting prompt:

1. `research_brief.md` is the high-context source of truth: method hypothesis, RQs, datasets, baselines, metrics, risks, and evidence rules.
2. `experiments/registry.json` defines E1/E2/E3/E4 experiment IDs, claims, commands, expected outputs, and paper targets.
3. Remote or local runs write logs and JSON metrics under `experiments/results/` and `experiments/logs/`.
4. `collect_paper_results.py` converts real result artifacts into `results_numbers.tex` and `experiments/paper_numbers.json`.
5. `generate_paper_figures.py` converts real prediction/history artifacts into data-backed figures and `figures/figure_manifest.json`.
6. LaTeX tables reference result macros from `results_numbers.tex`; do not hand-type performance numbers into the paper.
7. `story/*.md` records planning, failures, diagnosis, and rescue attempts so later writing has continuity.

If experiments are still planned-only, the macro file may contain `??`, but the audit trail must make that status explicit.

## Strict Gates

Run:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\gate_check.py <project_dir>
```

Gate failures must become concrete next actions. Do not declare the paper finished with failing gates.

For `original_research` projects, `gate_check.py` enforces submission-quality gates in addition to artifact existence:

- compiled PDF page count reaches the project target, normally at least 7 pages for AAAI-style papers;
- manuscript body reaches at least 5,500 words unless overridden in `state.json`;
- Introduction, Related Work, Method, Experiments, Analysis, Limitations, and Conclusion each meet section word budgets;
- citation weaving, formal equations, algorithm/pseudocode, figure mentions, and table mentions meet minimum density;
- AAAI targets must use an AAAI style/package and anonymous submission marker;
- severe LaTeX overfull boxes fail the gate.
- research pipeline artifacts must exist: `research_brief.md`, `story/00_research_brief.md`, `experiments/registry.json`, `experiments/run_queue.md`, `results_numbers.tex`, `experiments/paper_numbers.json`, and `figures/figure_manifest.json`.

These failures are blockers. Keep iterating until `submission_quality` passes or truthfully document the remaining blocker.

When `submission_quality` fails because the manuscript is short or shallow, do not rewrite the full paper in one pass. Generate section-specific writing context first:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\plan_section_expansion.py <project_dir>
```

Then open `writing_context/expansion_plan.md` and the relevant `writing_context/section_packets/*.md` files. Expand one or two sections at a time against their word budgets, citations, paragraph tasks, and evidence constraints. Compile and run `gate_check.py` after each expansion pass.

## Review Format

Peer review output must be JSON in `reviews/review_round_<N>.json`:

```json
{
  "round": 1,
  "median_score": 6.5,
  "recommendation": "Borderline",
  "reviewers": [
    {
      "persona": "R1 Experimentalist",
      "overall_score": 6.0,
      "dimension_scores": {
        "novelty": 6,
        "comprehensiveness": 7,
        "clarity": 6,
        "technical_depth": 6,
        "experimental_validation": 4
      },
      "strengths": [],
      "weaknesses": [
        {
          "severity": "Major",
          "type": "Experiment not rigorous",
          "evidence": "The pilot study lacks repeated trials.",
          "suggestion": "Add at least three trials and report mean plus standard deviation."
        }
      ]
    }
  ],
  "previous_fix_regression_check": []
}
```

After writing review JSON, run:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\route_review.py <project_dir>
```

## Compilation

When manuscript files changed:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\SunYu\.codex\skills\paper-writing\scripts\compile_latex.ps1 -ProjectDir <project_dir>
```

Read `build/compile_report.json`. Fix compile errors and undefined references before continuing.

## Remote Results Refresh

When experiments run on a remote GPU machine, keep all code, datasets, checkpoints, and logs under the remote data disk, for example `/root/autodl-tmp/<project>`. Refresh local artifacts with:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\SunYu\.codex\skills\paper-writing\scripts\refresh_artifacts.ps1 -ProjectDir <project_dir> -RemoteHost <user@host> -Port <port> -RemoteDir /root/autodl-tmp/<project> -Compile
```

This pulls result/log/figure artifacts, regenerates `results_numbers.tex`, updates `figures/figure_manifest.json`, and optionally recompiles.

## Sources and Integrity

- Use web search or source APIs for current papers and venue status.
- When the user asks to preserve literature for reuse, harvest open papers into the local literature library before writing: default VMR path `D:\syz_autopaper\auto_idea\video moment retrieval\download_paper`.
- Prefer arXiv/OpenAlex/Semantic Scholar/DBLP/OpenReview for bibliographic metadata.
- Every cited item must exist in `refs/references.bib`.
- Every important claim must be backed by a citation, result, or explicitly labeled conjecture.
- Experiments must be pre-registered before execution.
- Claims may not be stronger than the evidence.

## Fine-Grained Idea Graph

For the VMR local library, validate the five regression papers first:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\build_finegrained_idea_graph.py `
  --sanity-only --strict `
  --out-dir "D:\syz_autopaper\auto_idea\video moment retrieval\idea_graph"
```

Then rebuild the complete graph:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\build_finegrained_idea_graph.py `
  --strict `
  --out-dir "D:\syz_autopaper\auto_idea\video moment retrieval\idea_graph"
```

The inference hierarchy is:

```text
Introduction evidence
  -> atomic problem/method units
  -> micro problem/method clusters
  -> data-derived top-level families
  -> fine-grained transfer opportunities
```

Legacy Pxx/Mxx labels may be retained as hints, but must not drive clustering, linking, opportunity scoring, or idea generation. Related Work must not be used as primary extraction evidence.
