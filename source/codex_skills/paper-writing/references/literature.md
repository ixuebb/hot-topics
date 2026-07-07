# Literature Survey

## Pipeline

Use five stages: Local Library Harvest, Recall, Score, Classify, Upgrade.

## Stage 0: Local Library Harvest

When the task requires reusable literature assets, first build or refresh a local paper library. Read `references/literature_library.md`.

Default VMR command:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\harvest_literature_library.py --out-dir "D:\syz_autopaper\auto_idea\video moment retrieval\download_paper" --vmr-defaults --sources cvf,neurips,semantic_scholar,openalex,arxiv --max-results 25 --limit-papers 120 --year-min 2017
```

Before writing related work or benchmark comparisons, search the local library:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\search_local_library.py --library-dir "D:\syz_autopaper\auto_idea\video moment retrieval\download_paper" --query "<claim, method, benchmark, or baseline>"
```

This stage materializes metadata, BibTeX, open PDFs, abstracts, introductions, figure assets, table assets, captions, and searchable text. It complements, but does not replace, citation scoring and BibTeX verification.

## Stage 1: Recall

Create 20-30 keyword queries for a full survey. Each taxonomy cell needs at least three query variants:

- Core terms.
- Synonyms.
- Method names or benchmark names.

Run:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\search_semantic_scholar.py <project_dir> --query "<query>" --limit 20
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\search_literature.py <project_dir> --query "<query>" --max-results 25
```

For many queries, write one query per line and pass `--queries-file`.

Target raw candidates:

- Short paper: 80-150.
- Full survey: 200-500.

## Stage 2: LQS Scoring

Run:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\score_lqs.py <project_dir>
```

Weights:

- Recency: 30%.
- Citation impact: 25%.
- Venue: 20%.
- Institution: 10%.
- Acceptance: 15%.

Thresholds:

- LQS >= 7.0: must-cite.
- 5.0 <= LQS < 7.0: conditional.
- LQS < 5.0: drop.

## Stage 3: Citation Depth

Assign depth in `refs/citation_plan.jsonl`:

- A: 1-3 paragraphs, section protagonist.
- B: 2-5 sentences, important insight.
- C: one contextual sentence.
- D: dropped.

Before writing, assign `taxonomy_cell` and `intended_use` for A/B references.

## Stage 4: Venue Upgrade

For arXiv-only entries, search DBLP, OpenReview, conference pages, and author pages. If accepted, update:

- BibTeX entry type.
- Venue or booktitle.
- Acceptance status.
- URL if better canonical source exists.

Do not mark a paper accepted without source evidence.

Local helper:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\upgrade_venues.py <project_dir>
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\score_lqs.py <project_dir>
```

`upgrade_venues.py` queries Semantic Scholar and DBLP, writes `refs/enriched_candidates.jsonl`, updates `raw_candidates.jsonl`, and records source evidence in each enriched row. Rerun LQS afterward so citation impact and accepted venues affect scoring.

## Verification

Run:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\verify_bib.py <project_dir>
```

Fix duplicate keys, missing titles/authors/years, and planned references missing from BibTeX.
