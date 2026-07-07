# Peer Review Simulation

## Reviewers

Use 3-5 independent personas:

- R1 Experimentalist: statistical rigor, baselines, replication.
- R2 Theorist: definitions, formalism, taxonomy.
- R3 Perfectionist: writing quality, figures, formatting.
- R4 Synthesizer: cross-cutting analysis and gap identification.
- R5 Newcomer: accessibility, definitions, examples.

## Scoring Dimensions

Score each 1-10:

- Novelty.
- Comprehensiveness.
- Clarity.
- Technical depth.
- Experimental validation.

Final score is the median reviewer overall score.

Calibration:

- 6.0: workshop-quality complete draft.
- 7.0: main-conference borderline/weak accept.
- 8.0: strong accept.
- 9.0: oral-level.

## Anti-Inflation

- First review round is capped at 7.0.
- Score may increase at most 1.5 per round.
- At least one unresolved weakness must remain until final.
- Reviewers must cite concrete evidence from the manuscript.

## Output

Save JSON as `reviews/review_round_<N>.json`. Include:

- `round`.
- `median_score`.
- `recommendation`.
- `reviewers`.
- Each reviewer has strengths and weaknesses.
- Weaknesses have severity, type, evidence, suggestion.
- `previous_fix_regression_check`.

After saving, run `route_review.py`.

