# Problem Timeline

## P01 Annotation Scarcity and Noisy Supervision

- First seen in local corpus: 2021
- Paper count: 83
- Count by year: 2021: 6, 2022: 16, 2023: 17, 2024: 26, 2025: 5, 2026: 13
- Canonical question: How can VMR/VTG learn with fewer, cheaper, or noisier temporal annotations?
- Root cause: Temporal boundary annotations are expensive and pseudo labels are often mismatched or imprecise.
- Representative papers:
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning (arXiv (Cornell University))
  - 2026 Beyond Caption-Based Queries in Video Moment Retrieval (CVPR 2026)
  - 2026 EvoGround: Self-Evolving Video Agents for Video Temporal Grounding (arXiv (Cornell University))
  - 2026 Finding Optimal Video Moment without Training: Gaussian Boundary Optimization for Weakly Supervised Video Grounding (arXiv (Cornell University))
  - 2026 GranAlign: Granularity-Aware Alignment Framework for Zero-shot Video Moment Retrieval (Open MIND)

## P02 Boundary Ambiguity and Localization Precision

- First seen in local corpus: 2021
- Paper count: 94
- Count by year: 2021: 14, 2022: 15, 2023: 19, 2024: 20, 2025: 5, 2026: 21
- Canonical question: How can models predict accurate temporal boundaries when event starts and ends are ambiguous?
- Root cause: Language-described events rarely have a single crisp temporal interval.
- Representative papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors (arXiv (Cornell University))
  - 2026 CVA: Context-aware Video-text Alignment for Video Temporal Grounding (CVPR 2026)
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval (ArXiv.org)
  - 2026 Fewer Steps, Better Performance: Efficient Cross-Modal Clip Trimming for Video Moment Retrieval Using Language (Proceedings of the AAAI Conference on Artificial Intelligence)
  - 2026 Finding Optimal Video Moment without Training: Gaussian Boundary Optimization for Weakly Supervised Video Grounding (arXiv (Cornell University))

## P03 Long-Video Evidence Sparsity and Efficient Selection

- First seen in local corpus: 2021
- Paper count: 82
- Count by year: 2021: 7, 2022: 9, 2023: 13, 2024: 21, 2025: 8, 2026: 24
- Canonical question: How can models find sparse evidence in long videos without wasting tokens or frames?
- Root cause: Relevant evidence is sparse while dense frame processing is expensive and noisy.
- Representative papers:
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization (arXiv (Cornell University))
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding (arXiv (Cornell University))
  - 2026 E.M.Ground: A Temporal Grounding Vid-LLM with Holistic Event Perception and Matching (arXiv (Cornell University))
  - 2026 EVIDENT: Routing MLLM Adaptation through Entity-Grounded Visual Evidence for Cross-Domain Video Temporal Grounding (arXiv (Cornell University))
  - 2026 Fewer Steps, Better Performance: Efficient Cross-Modal Clip Trimming for Video Moment Retrieval Using Language (Proceedings of the AAAI Conference on Artificial Intelligence)

## P05 Multi-Moment, Compositional, and Complex Query Grounding

- First seen in local corpus: 2021
- Paper count: 73
- Count by year: 2021: 12, 2022: 10, 2023: 14, 2024: 20, 2025: 1, 2026: 16
- Canonical question: How can systems ground queries that refer to multiple moments, relations, or multi-hop evidence?
- Root cause: Single-interval retrieval is insufficient for compositional or multi-event user intent.
- Representative papers:
  - 2026 Beyond Caption-Based Queries for Video Moment Retrieval (arXiv (Cornell University))
  - 2026 Beyond Caption-Based Queries in Video Moment Retrieval (CVPR 2026)
  - 2026 CoSTL: Comprehensive Spatial-Temporal Representation Learning for Moment Retrieval and Highlight Detection (ArXiv.org)
  - 2026 Event-aware Video Corpus Moment Retrieval (arXiv (Cornell University))
  - 2026 EvoGround: Self-Evolving Video Agents for Video Temporal Grounding (arXiv (Cornell University))

## P06 Cross-Modal Semantic Alignment Gap

- First seen in local corpus: 2021
- Paper count: 152
- Count by year: 2021: 24, 2022: 20, 2023: 25, 2024: 53, 2025: 4, 2026: 26
- Canonical question: How can language, visual, audio, and temporal representations stay semantically aligned?
- Root cause: Video-language representations often align global semantics but miss fine temporal evidence.
- Representative papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding (arXiv (Cornell University))
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval (ArXiv.org)
  - 2026 AuViRe: Audio-visual Speech Representation Reconstruction for Deepfake Temporal Localization (ArXiv.org)
  - 2026 CVA: Context-aware Video-text Alignment for Video Temporal Grounding (CVPR 2026)
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval (ArXiv.org)

## P07 LLM Temporal Reasoning and Time Output Instability

- First seen in local corpus: 2021
- Paper count: 79
- Count by year: 2021: 1, 2022: 3, 2023: 8, 2024: 21, 2025: 8, 2026: 38
- Canonical question: How can Video/Multimodal LLMs reason about time and output reliable temporal spans?
- Root cause: LLMs reason fluently but have weak temporal localization, unstable time formats, and hallucinated evidence.
- Representative papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding (arXiv (Cornell University))
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning (arXiv (Cornell University))
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization (arXiv (Cornell University))
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding (arXiv (Cornell University))
  - 2026 Dr.V : A Hierarchical Perception-Temporal-Cognition Framework to Diagnose Video Hallucination by Fine-Grained Spatial-Temporal Grounding (International Journal of Computer Vision)

## P08 Domain Shift and Generalization

- First seen in local corpus: 2021
- Paper count: 63
- Count by year: 2021: 3, 2022: 9, 2023: 10, 2024: 22, 2025: 3, 2026: 16
- Canonical question: How can methods generalize across datasets, domains, video styles, and unseen query distributions?
- Root cause: Dataset-specific priors and annotation styles cause brittle cross-domain transfer.
- Representative papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding (arXiv (Cornell University))
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval (ArXiv.org)
  - 2026 AuViRe: Audio-visual Speech Representation Reconstruction for Deepfake Temporal Localization (ArXiv.org)
  - 2026 Beyond Caption-Based Queries for Video Moment Retrieval (arXiv (Cornell University))
  - 2026 Beyond Caption-Based Queries in Video Moment Retrieval (CVPR 2026)

## P09 Scalability and Corpus-Level Retrieval

- First seen in local corpus: 2021
- Paper count: 45
- Count by year: 2021: 8, 2022: 9, 2023: 8, 2024: 15, 2026: 5
- Canonical question: How can retrieval scale from one video to large corpora or real-world open pools?
- Root cause: Searching many long videos introduces retrieval, memory, and ranking bottlenecks.
- Representative papers:
  - 2026 Event-aware Video Corpus Moment Retrieval (arXiv (Cornell University))
  - 2026 GenSpan: Generation-Calibrated Motion Span Priors for Multi-Verb Video Corpus Moment Retrieval (arXiv (Cornell University))
  - 2026 Grounding is All You Need? Dual Temporal Grounding for Video Dialog (arXiv (Cornell University))
  - 2026 SARL-STG: A Spatially Aware Reinforcement Learning Framework for Refining MLLMs in Spatio-Temporal Video Grounding (CVPR 2026)
  - 2026 TimeLens: Rethinking Video Temporal Grounding with Multimodal LLMs (CVPR 2026)

## P10 Spatio-Temporal and Object/Event-Level Grounding

- First seen in local corpus: 2021
- Paper count: 77
- Count by year: 2021: 6, 2022: 10, 2023: 7, 2024: 22, 2025: 4, 2026: 28
- Canonical question: How can temporal grounding incorporate objects, regions, events, or spatial evidence?
- Root cause: Temporal moments are often defined by object interactions and spatial evidence, not only clip-level semantics.
- Representative papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors (arXiv (Cornell University))
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning (arXiv (Cornell University))
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding (arXiv (Cornell University))
  - 2026 CoSTL: Comprehensive Spatial-Temporal Representation Learning for Moment Retrieval and Highlight Detection (ArXiv.org)
  - 2026 Dr.V : A Hierarchical Perception-Temporal-Cognition Framework to Diagnose Video Hallucination by Fine-Grained Spatial-Temporal Grounding (International Journal of Computer Vision)

## P11 Dataset, Benchmark, and Evaluation Mismatch

- First seen in local corpus: 2021
- Paper count: 100
- Count by year: 2021: 11, 2022: 17, 2023: 9, 2024: 30, 2025: 6, 2026: 27
- Canonical question: Are current datasets, metrics, and evaluation protocols measuring the right temporal grounding ability?
- Root cause: Existing benchmarks may not reflect real user queries, long videos, invalid queries, or annotation ambiguity.
- Representative papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors (arXiv (Cornell University))
  - 2026 AuViRe: Audio-visual Speech Representation Reconstruction for Deepfake Temporal Localization (ArXiv.org)
  - 2026 Beyond Caption-Based Queries for Video Moment Retrieval (arXiv (Cornell University))
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization (arXiv (Cornell University))
  - 2026 CVA: Context-aware Video-text Alignment for Video Temporal Grounding (CVPR 2026)

## P12 Uncertainty, Calibration, and Rejection

- First seen in local corpus: 2021
- Paper count: 9
- Count by year: 2021: 1, 2023: 2, 2024: 3, 2025: 1, 2026: 2
- Canonical question: How can models know when temporal evidence is uncertain and calibrate or reject predictions?
- Root cause: Hard deterministic predictions hide ambiguity, weak evidence, and confidence errors.
- Representative papers:
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval (ArXiv.org)
  - 2026 Improving Temporal Localization in Vision-Language Video Anomaly Detection (Journal of Innovative Image Processing)
  - 2025 Uncertainty-quantified Rollout Policy Adaptation for Unlabelled Cross-domain Video Temporal Grounding (NeurIPS 2025)
  - 2024 Beyond Uncertainty: Evidential Deep Learning for Robust Video Temporal Grounding (arXiv (Cornell University))
  - 2024 FlashVTG: Feature Layering and Adaptive Score Handling Network for Video Temporal Grounding (arXiv (Cornell University))

## P04 Query Ambiguity, Invalid Queries, and Open-Set Retrieval

- First seen in local corpus: 2023
- Paper count: 12
- Count by year: 2023: 2, 2024: 7, 2026: 3
- Canonical question: How should systems behave when the query is ambiguous, invalid, underspecified, or has no matching moment?
- Root cause: Benchmarks often assume every query is valid, but real users issue uncertain or impossible queries.
- Representative papers:
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval (ArXiv.org)
  - 2026 Learning to Refuse: Refusal-Aware Reinforcement Fine-Tuning for Hard-Irrelevant Queries in Video Temporal Grounding (CVPR 2026)
  - 2026 Not All Inputs Are Valid: Towards Open-Set Video Moment Retrieval using Language (arXiv)
  - 2024 Context-Guided Spatio-Temporal Video Grounding (CVPR 2024)
  - 2024 End-to-End Dense Video Grounding via Parallel Regression (arXiv (Cornell University))
