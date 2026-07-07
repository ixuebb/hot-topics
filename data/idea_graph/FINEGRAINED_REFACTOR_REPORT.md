# Fine-Grained Idea Graph Refactor Report

## Result

The backend now builds the graph bottom-up:

```text
Abstract / Introduction evidence
  -> intro motivation chain
  -> atomic problem and method units
  -> micro problem and method clusters
  -> data-derived top-level families
  -> evidence-traceable transfer ideas
```

Legacy Pxx/Mxx labels are retained only as optional hints. They do not drive clustering, problem-method links, opportunity scoring, or idea generation.

## Modified Code

- `C:\Users\SunYu\.codex\skills\paper-writing\scripts\build_finegrained_idea_graph.py`
- `C:\Users\SunYu\.codex\skills\paper-writing\SKILL.md`
- `D:\自动化论文平台\projects\vmr_idea_dashboard\app.js`
- `D:\自动化论文平台\projects\vmr_idea_dashboard\styles.css`

The legacy `build_idea_graph.py` remains unchanged for compatibility with the old coarse files.

## Full-Library Output

- Deduplicated papers processed: 300
- Core VMR/VTG papers: 235
- Adjacent-task papers: 65
- Atomic problem units: 983
- Atomic method units: 835
- Preserved illustrative examples: 722
- Core micro problem clusters: 145
- Adjacent micro problem clusters: 80
- Micro method clusters: 229
- Data-derived core problem families: 12
- Data-derived adjacent problem families: 15
- Data-derived method families: 10
- Fine-grained idea opportunities: 60
- Strict quality gate: passed
- Quality errors: 0
- Quality warnings: 0

The current count of 12 core top-level families is an output of the final clustering run, not a fixed taxonomy. It may change when the paper library or atomic units change.

## Sanity Checks

### ActPrompt

- Core task: Video Moment Retrieval
- Problems:
  - Image-pretrained VLMs miss action-sensitive objects.
  - End-to-end VLM adaptation on long raw videos is computationally impractical.
- Methods:
  - Preliminary in-domain feature adaptation with pairwise ranking and contrastive pretext tasks.
  - Action-Cue-Injected prompt learning with video-guided and verb-guided prompts.
  - Context-aware Temporal Prompt Learning over selected action-sensitive regions.
- Preserved example: drinking coffee, with attention to the mug and hand.

### Adaptive Evidential Learning / DEMR

- Core task: Video Moment Retrieval
- Problems:
  - NMS-based deterministic inference forces hard selection under missing evidence.
  - Vanilla DER miscalibrates uncertainty after multimodal evidence fusion.
- Methods:
  - Deep Evidential Regression baseline.
  - RFF, Query Reconstruction, and Geom regularization.
- Preserved example: the woman-cooking query when the woman is absent from frames.

### CVA

- Core task: Video Temporal Grounding
- Problems:
  - Query-agnostic content mixing creates semantic false negatives.
  - Boundary representations shift under diversified context.
- Methods:
  - Query-aware Context Diversification with CLIP relevance filtering.
  - Context-invariant Boundary Discrimination.
  - Context-enhanced Transformer Encoder.
- Preserved Figure 1 replacement-clip example.

### ClipTBP

- Core task: Video Moment Retrieval
- Problems:
  - Independent snippet learning ignores relationships among multiple answers.
  - Similar distractors and short gaps become overly broad boundaries.
- Methods:
  - Clip-level similarity with positive answer pairs and hard negatives.
  - Main and auxiliary boundary losses with inside-outside discrimination.
- Preserved pink-haired woman repeated-segment example.

### AuViRe

- Adjacent task: Temporal Forgery Localization
- Problems:
  - Video-level classification cannot localize short manipulated intervals.
  - Multimodal detectors underuse subtle audio-visual speech inconsistencies.
- Methods:
  - Audio-visual speech representation reconstruction.
  - Reconstruction-discrepancy encoding for frame-level forgery localization.
- It is excluded from core VMR problem statistics but remains available as a transfer source.

## Example Fine-Grained Idea

`FI048`, score `9.25`:

- Target micro problem: Query-agnostic content mixing creates semantically false negatives.
- Source micro method: Reconstruction-discrepancy encoding for frame-level forgery localization.
- Shared mechanism: Cross-modal discrepancy can identify semantically inconsistent replacement clips.
- Direct graph coverage: zero existing links between these two micro nodes.
- Source evidence includes AuViRe.
- Target evidence includes CVA.
- Minimal experiment: use CVA on Charades-STA and QVHighlights, add a reconstruction-discrepancy signal for replacement clips, keep extracted features fixed, and report R@1/mIoU plus a false-negative-specific diagnostic.
- Main reviewer risks: direct module transplantation, incompatible supervision, and average gains hiding failure-specific behavior.

## New Graph Files

- `paper_micro_cards_index.json`
- `intro_motivation_chains.json`
- `micro_problem_clusters.json`
- `adjacent_micro_problem_clusters.json`
- `micro_method_clusters.json`
- `emergent_problem_taxonomy.json`
- `adjacent_problem_taxonomy.json`
- `emergent_method_taxonomy.json`
- `micro_problem_method_matrix.csv`
- `adjacent_task_papers.json`
- `idea_opportunities_finegrained.json`
- `finegrained_quality_report.json`
- `README_FINEGRAINED.md`

## Frontend

Open:

```text
http://127.0.0.1:8765/
```

The frontend now supports:

- Dynamic top-level family -> micro problem navigation.
- Failure mode, root cause, timeline, linked micro methods, and evidence papers.
- Paper task scope, motivation chain, limitations, examples, atomic problems, atomic methods, figures, and tables.
- A separate adjacent-task view.
- Fine-grained idea reasoning, technical sketch, minimum experiment, evidence papers, and reviewer attack points.

## Remaining Limitations

- Generic extraction is deterministic and evidence-grounded, but it is not equivalent to expert manual reading for every paper.
- PDF text extraction can still introduce noisy line breaks or headers; contaminated clusters are filtered from idea ranking, but the underlying card remains reviewable.
- Top-level family names are generated from dominant failure facets and discriminative terms; occasional names may still need human renaming for publication-facing use.
- Idea scores are opportunity heuristics, not predicted acceptance probability.
- Before implementing an idea, inspect its linked evidence, source method assumptions, dataset compatibility, and closest recent baselines.
