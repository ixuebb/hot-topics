# Experiment Design

## Required Order

1. Write `experiments/preregister.md`.
2. Run `init_experiment_registry.py` to create `experiments/registry.json`, E-numbered experiment docs, and `experiments/run_queue.md`.
3. Define hypothesis, variables, controls, expected results, statistical plan, commands, expected outputs, and paper target for each E-numbered experiment.
4. Execute the smallest falsifiable experiment.
5. Save logs and raw outputs under `experiments/logs/` and `experiments/results/`.
6. Save `experiments/results.json` or per-experiment JSON files.
7. Run `collect_paper_results.py` before integrating numbers into the paper.
8. Save `experiments/experiment_summary.md`.
9. Only then integrate into the paper.

## Preregistration Template

Include:

- Paper claim supported.
- Hypothesis.
- Independent variables.
- Dependent variables.
- Control variables.
- Dataset/task set.
- Models or systems tested.
- Number of trials.
- Statistical test or confidence interval.
- Failure criteria.

## Execution Scales

API-scale:

- 3-5 models.
- 2-3 conditions.
- 15-25 tasks.
- 3 trials.

Local/GPU-scale:

- Use a reproducible script.
- Save config, seed, logs, and metrics.
- Prefer small pilots before long runs.
- Every run must map to an experiment ID in `experiments/registry.json`.
- Keep remote project files under the data disk path specified in the registry, such as `/root/autodl-tmp/<project>`.
- Use `refresh_artifacts.ps1` to pull result artifacts back into the local paper project.

## Experiment Registry

Each original-research project should maintain:

```text
experiments/
  registry.json
  run_queue.md
  E1_main_*.md
  E2_ablation_*.md
  E3_robustness_*.md
  results/
  logs/
```

Every registry experiment needs:

- `id`, `name`, `claim`, and `purpose`.
- `datasets`, `baselines`, `metrics`, and `controls`.
- runnable `commands`.
- `expected_outputs` that include JSON result files.
- `paper_targets` that name the manuscript table, figure, or paragraph the experiment supports.

For VMR, default E-level structure is:

- E1 main comparison across Charades-STA, ActivityNet Captions, TACoS, and optionally QVHighlights.
- E2 component ablation.
- E3 robustness or ambiguity analysis.
- E4 efficiency and reproducibility.

## Iteration Triggers

- Ceiling effect: increase difficulty.
- Floor effect: reduce difficulty or inspect bugs.
- Non-significant result: increase trials or revise hypothesis.
- Surprise finding: design follow-up, but do not hide the original plan.

Maximum experiment redesigns per paper: 5.

## Results Schema

`experiments/results.json` should include:

```json
{
  "paper_claim": "Claim or section label",
  "hypothesis": "Falsifiable hypothesis",
  "trials": 3,
  "conditions": [],
  "metrics": [],
  "results": [],
  "statistics": {},
  "ceiling_floor_check": {},
  "limitations": []
}
```

Per-experiment result files may also use row records:

```json
{
  "experiment_id": "E1",
  "results": [
    {
      "macro": "CharadesStaR1Iou05",
      "dataset": "Charades-STA",
      "method": "OURS",
      "metric": "R@1 IoU=0.5",
      "value": 0.0,
      "seed": 0,
      "status": "real"
    }
  ]
}
```

Use `value` only for real measured values. Planned rows should omit `value` or set `status` to `planned`.
