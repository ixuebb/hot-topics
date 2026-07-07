# Local Literature Library

Use this workflow when a paper task needs durable literature research rather than one-off web search. It turns online search results into a local evidence library containing metadata, BibTeX, PDFs when legally available, abstracts, introductions, figure assets, table assets, captions, and searchable text.

Default VMR library:

```powershell
D:\syz_autopaper\auto_idea\video moment retrieval\download_paper
```

## How The Three Prompt Bundles Fit

- Literature investigation prompts become the reading and positioning layer: domain roadmap, paper priority, single-paper influence, and citation role.
- Systematic retrieval prompts become the search layer: query matrix, benchmark names, method aliases, author tracking, citation chasing, saturation checks, and blind-spot checks.
- Topic evaluation prompts become the idea gate: novelty scan, feasibility scan, comparison against obvious reviewer objections, and contribution positioning.

Do not paste those prompts verbatim into every run. Convert their requirements into concrete query files, search logs, paper folders, BibTeX, and notes that can be audited later.

## Output Contract

Each harvested paper folder should contain:

```text
<year>_<first-author>_<title-slug>_<hash>/
  metadata.json
  citation.bib
  paper.pdf                  # only when open-access/legal download succeeds
  abstract.md
  introduction.md
  full_text.txt              # extracted from the PDF when available
  extraction_report.json
  figures/
    captions.md
    embedded/
    pages/                   # full-page snapshots for pages mentioning figures
  tables/
    captions.md
    extracted/
      table_*.md
      table_*.csv
    pages/                   # full-page snapshots for pages mentioning tables
```

The library root also keeps:

```text
library_index.jsonl
search_manifest.json
```

## Harvest Command

For VMR, start with broad retrieval plus benchmark-specific queries:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\harvest_literature_library.py `
  --out-dir "D:\syz_autopaper\auto_idea\video moment retrieval\download_paper" `
  --vmr-defaults `
  --query "video moment retrieval QVHighlights" `
  --query "temporal video grounding recent benchmark" `
  --query "Charades-STA ActivityNet Captions TACoS temporal grounding" `
  --max-results 25 `
  --limit-papers 120 `
  --year-min 2017
```

Use `--from-candidates <project>\refs\raw_candidates.jsonl` when a project already has search results and you want to materialize those papers into the local library.

## Local Search Command

Search the local library before writing claims, related work, benchmark tables, or rebuttal-style positioning:

```powershell
python C:\Users\SunYu\.codex\skills\paper-writing\scripts\search_local_library.py `
  --library-dir "D:\syz_autopaper\auto_idea\video moment retrieval\download_paper" `
  --query "uncertainty temporal grounding distributional moment retrieval"
```

Add `--include-full-text` when exact phrasing or table mentions matter more than speed.

## Search Discipline

For every new topic, create at least these query groups:

- Core task names.
- Synonyms and older task names.
- Benchmark names and metric names.
- Recent method family names.
- Strong baseline names.
- Survey and challenge names.
- Key author or lab names.

Run multiple sources where possible: Semantic Scholar, OpenAlex, arXiv, DBLP/CVF/OpenReview manually when venue status matters. Google Scholar is useful for manual cross-checking, but do not rely on brittle scraping as an automated source.

Stop expanding only after two consecutive query groups produce no new A/B-priority papers, or after the remaining results are duplicates, unrelated, or clearly below the citation/venue/recency threshold.

## Integrity Rules

- Download only open-access PDFs or author-hosted PDFs that are publicly available.
- Never fabricate a PDF, BibTeX field, venue, table value, or figure.
- If PDF extraction misses a vector figure or complex table, keep the page snapshot and record the limitation in `extraction_report.json`.
- Verify benchmark numbers against paper tables before moving them into manuscript result tables.
- Keep local-library evidence separate from experimental result artifacts; local papers support citations and baselines, not new model claims.
