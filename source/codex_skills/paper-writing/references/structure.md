# Paper Structure and Logic

## Survey Architecture

Default section plan:

1. Introduction: hook, gap, contributions, roadmap.
2. Background: definitions, problem setup, taxonomy overview.
3. Core family 1: methods, evidence, critical assessment.
4. Core family 2: methods, evidence, critical assessment.
5. Core family 3: methods, evidence, critical assessment.
6. Cross-cutting analysis or taxonomy synthesis.
7. Benchmarks and experiments.
8. Future directions.
9. Conclusion.

The exact number may change, but the paper must keep this logic.

## Paragraph Patterns

Use one of these patterns intentionally:

- Claim-Evidence-Implication: assert, cite or measure, explain why it matters.
- Compare-Contrast: method A, method B, difference, trade-off.
- Concession-Rebuttal: acknowledge strength, identify limitation.
- Funnel: broad context, narrow gap, this paper's position.

For `original_research`, do not treat these patterns as optional polish. The manuscript must be expanded section by section until it reaches the submission-quality budgets enforced by `gate_check.py`: Introduction 900+ words, Related Work 800+ words, Method 1200+ words, Experiments 1000+ words, Analysis/Ablation 600+ words, Limitations 150+ words, and Conclusion 120+ words. A section that satisfies the heading checklist but misses its budget is still incomplete.

## Taxonomy Rules

- Prefer multi-axis matrices over flat lists.
- Make the taxonomy as MECE as possible.
- Empty cells are useful if they become gap analysis.
- Methods that span cells should be discussed as taxonomy tension.

## Formal Claims

Use `Conjecture`, `Observation`, or `Hypothesis` by default. Avoid `Theorem` unless a proof is actually present.

Hedge ladder:

- Strong: demonstrates.
- Medium: suggests.
- Weak: may, could, we hypothesize.

Rule: claim strength must not exceed evidence strength.

## Related Work Differentiation

Include a table comparing this survey with existing surveys. "More recent" is not enough; the paper needs a new taxonomy, new synthesis angle, new experiment, or new cross-benchmark analysis.
