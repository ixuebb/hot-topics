# Transfer Opportunities

## 1. Query-Conditioned Evidence Sufficiency Testing for Invalid Moment Queries  
Score: 7.6

- Target problem: P04 Query Ambiguity, Invalid Queries, and Open-Set Retrieval
- Transfer method: M02 Query-Conditioned Frame/Clip Selection
- Current usage in target cluster: 0
- Rationale: Query-Conditioned Frame/Clip Selection has been used in adjacent settings, while Query Ambiguity, Invalid Queries, and Open-Set Retrieval shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
  - 2026 Learning to Refuse: Refusal-Aware Reinforcement Fine-Tuning for Hard-Irrelevant Queries in Video Temporal Grounding
  - 2026 Not All Inputs Are Valid: Towards Open-Set Video Moment Retrieval using Language
- Method evidence papers:
  - 2026 Fewer Steps, Better Performance: Efficient Cross-Modal Clip Trimming for Video Moment Retrieval Using Language
  - 2026 GroundVTS: Visual Token Sampling in Multimodal Large Language Models for Video Temporal Grounding
  - 2026 Rethinking Weakly-Supervised Video Temporal Grounding From a Game Perspective

## 2. Boundary Refinement and Temporal Clustering for Uncertainty, Calibration, and Rejection  
Score: 7.4

- Target problem: P12 Uncertainty, Calibration, and Rejection
- Transfer method: M05 Boundary Refinement and Temporal Clustering
- Current usage in target cluster: 0
- Rationale: Boundary Refinement and Temporal Clustering has been used in adjacent settings, while Uncertainty, Calibration, and Rejection shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Start with a small frozen-feature diagnostic and one public benchmark before scaling to full training.
- Target evidence papers:
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 Improving Temporal Localization in Vision-Language Video Anomaly Detection
  - 2025 Uncertainty-quantified Rollout Policy Adaptation for Unlabelled Cross-domain Video Temporal Grounding
- Method evidence papers:
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
  - 2026 Fewer Steps, Better Performance: Efficient Cross-Modal Clip Trimming for Video Moment Retrieval Using Language
  - 2026 Finding Optimal Video Moment without Training: Gaussian Boundary Optimization for Weakly Supervised Video Grounding

## 3. Open-Set or Refusal-Aware Modeling for Uncertainty, Calibration, and Rejection  
Score: 7.4

- Target problem: P12 Uncertainty, Calibration, and Rejection
- Transfer method: M07 Open-Set or Refusal-Aware Modeling
- Current usage in target cluster: 0
- Rationale: Open-Set or Refusal-Aware Modeling has been used in adjacent settings, while Uncertainty, Calibration, and Rejection shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Start with a small frozen-feature diagnostic and one public benchmark before scaling to full training.
- Target evidence papers:
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 Improving Temporal Localization in Vision-Language Video Anomaly Detection
  - 2025 Uncertainty-quantified Rollout Policy Adaptation for Unlabelled Cross-domain Video Temporal Grounding
- Method evidence papers:
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
  - 2026 Grounding is All You Need? Dual Temporal Grounding for Video Dialog
  - 2026 Learning Consistent Temporal Grounding between Related Tasks in Sports Coaching

## 4. Evidence-Calibrated Open-Set Temporal Grounding  
Score: 7.22

- Target problem: P04 Query Ambiguity, Invalid Queries, and Open-Set Retrieval
- Transfer method: M06 Uncertainty, Evidential Learning, and Calibration
- Current usage in target cluster: 0
- Rationale: Uncertainty, Evidential Learning, and Calibration has been used in adjacent settings, while Query Ambiguity, Invalid Queries, and Open-Set Retrieval shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
  - 2026 Learning to Refuse: Refusal-Aware Reinforcement Fine-Tuning for Hard-Irrelevant Queries in Video Temporal Grounding
  - 2026 Not All Inputs Are Valid: Towards Open-Set Video Moment Retrieval using Language
- Method evidence papers:
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 Improving Temporal Localization in Vision-Language Video Anomaly Detection
  - 2026 Retrieving Any Relevant Moments: Benchmark and Models for Generalized Moment Retrieval

## 5. LLM Reasoning for Query Ambiguity, Invalid Queries, and Open-Set Retrieval  
Score: 6.4

- Target problem: P04 Query Ambiguity, Invalid Queries, and Open-Set Retrieval
- Transfer method: M08 LLM Reasoning, Agentic Workflows, or RL Post-Training
- Current usage in target cluster: 1
- Rationale: LLM Reasoning, Agentic Workflows, or RL Post-Training has been used in adjacent settings, while Query Ambiguity, Invalid Queries, and Open-Set Retrieval shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
  - 2026 Learning to Refuse: Refusal-Aware Reinforcement Fine-Tuning for Hard-Irrelevant Queries in Video Temporal Grounding
  - 2026 Not All Inputs Are Valid: Towards Open-Set Video Moment Retrieval using Language
- Method evidence papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization

## 6. Benchmark or Dataset Construction for Query Ambiguity, Invalid Queries, and Open-Set Retrieval  
Score: 6.4

- Target problem: P04 Query Ambiguity, Invalid Queries, and Open-Set Retrieval
- Transfer method: M14 Benchmark or Dataset Construction
- Current usage in target cluster: 2
- Rationale: Benchmark or Dataset Construction has been used in adjacent settings, while Query Ambiguity, Invalid Queries, and Open-Set Retrieval shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
  - 2026 Learning to Refuse: Refusal-Aware Reinforcement Fine-Tuning for Hard-Irrelevant Queries in Video Temporal Grounding
  - 2026 Not All Inputs Are Valid: Towards Open-Set Video Moment Retrieval using Language
- Method evidence papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Beyond Caption-Based Queries for Video Moment Retrieval

## 7. Query-Conditioned Frame/Clip Selection for Boundary Ambiguity and Localization Precision  
Score: 5.8

- Target problem: P02 Boundary Ambiguity and Localization Precision
- Transfer method: M02 Query-Conditioned Frame/Clip Selection
- Current usage in target cluster: 15
- Rationale: Query-Conditioned Frame/Clip Selection has been used in adjacent settings, while Boundary Ambiguity and Localization Precision shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 CVA: Context-aware Video-text Alignment for Video Temporal Grounding
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
- Method evidence papers:
  - 2026 Fewer Steps, Better Performance: Efficient Cross-Modal Clip Trimming for Video Moment Retrieval Using Language
  - 2026 GroundVTS: Visual Token Sampling in Multimodal Large Language Models for Video Temporal Grounding
  - 2026 Rethinking Weakly-Supervised Video Temporal Grounding From a Game Perspective

## 8. Weak-Supervision and Pseudo-Label Correction for Boundary Ambiguity and Localization Precision  
Score: 5.8

- Target problem: P02 Boundary Ambiguity and Localization Precision
- Transfer method: M13 Weak-Supervision and Pseudo-Label Correction
- Current usage in target cluster: 11
- Rationale: Weak-Supervision and Pseudo-Label Correction has been used in adjacent settings, while Boundary Ambiguity and Localization Precision shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 CVA: Context-aware Video-text Alignment for Video Temporal Grounding
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
- Method evidence papers:
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Mining Forgery Traces from Reconstruction Error: A Weakly Supervised Framework for Multimodal Deepfake Temporal Localization
  - 2026 Multi-proposal collaboration and multi-task training for weakly-supervised video moment retrieval

## 9. Object/Event/Spatio-Temporal Modules for Boundary Ambiguity and Localization Precision  
Score: 5.8

- Target problem: P02 Boundary Ambiguity and Localization Precision
- Transfer method: M15 Object/Event/Spatio-Temporal Modules
- Current usage in target cluster: 22
- Rationale: Object/Event/Spatio-Temporal Modules has been used in adjacent settings, while Boundary Ambiguity and Localization Precision shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 CVA: Context-aware Video-text Alignment for Video Temporal Grounding
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
- Method evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding

## 10. Boundary Refinement and Temporal Clustering for Long-Video Evidence Sparsity and Efficient Selection  
Score: 5.8

- Target problem: P03 Long-Video Evidence Sparsity and Efficient Selection
- Transfer method: M05 Boundary Refinement and Temporal Clustering
- Current usage in target cluster: 9
- Rationale: Boundary Refinement and Temporal Clustering has been used in adjacent settings, while Long-Video Evidence Sparsity and Efficient Selection shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding
  - 2026 E.M.Ground: A Temporal Grounding Vid-LLM with Holistic Event Perception and Matching
- Method evidence papers:
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
  - 2026 Fewer Steps, Better Performance: Efficient Cross-Modal Clip Trimming for Video Moment Retrieval Using Language
  - 2026 Finding Optimal Video Moment without Training: Gaussian Boundary Optimization for Weakly Supervised Video Grounding

## 11. Refusal-Aware Long-Video Moment Retrieval under Insufficient Evidence  
Score: 5.8

- Target problem: P03 Long-Video Evidence Sparsity and Efficient Selection
- Transfer method: M07 Open-Set or Refusal-Aware Modeling
- Current usage in target cluster: 4
- Rationale: Open-Set or Refusal-Aware Modeling has been used in adjacent settings, while Long-Video Evidence Sparsity and Efficient Selection shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding
  - 2026 E.M.Ground: A Temporal Grounding Vid-LLM with Holistic Event Perception and Matching
- Method evidence papers:
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
  - 2026 Grounding is All You Need? Dual Temporal Grounding for Video Dialog
  - 2026 Learning Consistent Temporal Grounding between Related Tasks in Sports Coaching

## 12. Query-Conditioned Frame/Clip Selection for Multi-Moment, Compositional, and Complex Query Grounding  
Score: 5.8

- Target problem: P05 Multi-Moment, Compositional, and Complex Query Grounding
- Transfer method: M02 Query-Conditioned Frame/Clip Selection
- Current usage in target cluster: 4
- Rationale: Query-Conditioned Frame/Clip Selection has been used in adjacent settings, while Multi-Moment, Compositional, and Complex Query Grounding shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 Beyond Caption-Based Queries for Video Moment Retrieval
  - 2026 Beyond Caption-Based Queries in Video Moment Retrieval
  - 2026 CoSTL: Comprehensive Spatial-Temporal Representation Learning for Moment Retrieval and Highlight Detection
- Method evidence papers:
  - 2026 Fewer Steps, Better Performance: Efficient Cross-Modal Clip Trimming for Video Moment Retrieval Using Language
  - 2026 GroundVTS: Visual Token Sampling in Multimodal Large Language Models for Video Temporal Grounding
  - 2026 Rethinking Weakly-Supervised Video Temporal Grounding From a Game Perspective

## 13. Agentic Decomposition for Multi-Moment Video Grounding  
Score: 5.8

- Target problem: P05 Multi-Moment, Compositional, and Complex Query Grounding
- Transfer method: M08 LLM Reasoning, Agentic Workflows, or RL Post-Training
- Current usage in target cluster: 10
- Rationale: LLM Reasoning, Agentic Workflows, or RL Post-Training has been used in adjacent settings, while Multi-Moment, Compositional, and Complex Query Grounding shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 Beyond Caption-Based Queries for Video Moment Retrieval
  - 2026 Beyond Caption-Based Queries in Video Moment Retrieval
  - 2026 CoSTL: Comprehensive Spatial-Temporal Representation Learning for Moment Retrieval and Highlight Detection
- Method evidence papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization

## 14. Memory for Multi-Moment, Compositional, and Complex Query Grounding  
Score: 5.8

- Target problem: P05 Multi-Moment, Compositional, and Complex Query Grounding
- Transfer method: M09 Memory, Graph, or Structure Alignment
- Current usage in target cluster: 11
- Rationale: Memory, Graph, or Structure Alignment has been used in adjacent settings, while Multi-Moment, Compositional, and Complex Query Grounding shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 Beyond Caption-Based Queries for Video Moment Retrieval
  - 2026 Beyond Caption-Based Queries in Video Moment Retrieval
  - 2026 CoSTL: Comprehensive Spatial-Temporal Representation Learning for Moment Retrieval and Highlight Detection
- Method evidence papers:
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
  - 2026 Keeping the Evidence Chain: Semantic Evidence Allocation for Training-Free Token Pruning in Video Temporal Grounding
  - 2026 MASRA: MLLM-Assisted Semantic-Relational Consistent Alignment for Video Temporal Grounding

## 15. Object/Event/Spatio-Temporal Modules for Multi-Moment, Compositional, and Complex Query Grounding  
Score: 5.8

- Target problem: P05 Multi-Moment, Compositional, and Complex Query Grounding
- Transfer method: M15 Object/Event/Spatio-Temporal Modules
- Current usage in target cluster: 13
- Rationale: Object/Event/Spatio-Temporal Modules has been used in adjacent settings, while Multi-Moment, Compositional, and Complex Query Grounding shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 Beyond Caption-Based Queries for Video Moment Retrieval
  - 2026 Beyond Caption-Based Queries in Video Moment Retrieval
  - 2026 CoSTL: Comprehensive Spatial-Temporal Representation Learning for Moment Retrieval and Highlight Detection
- Method evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding

## 16. Memory for Cross-Modal Semantic Alignment Gap  
Score: 5.8

- Target problem: P06 Cross-Modal Semantic Alignment Gap
- Transfer method: M09 Memory, Graph, or Structure Alignment
- Current usage in target cluster: 14
- Rationale: Memory, Graph, or Structure Alignment has been used in adjacent settings, while Cross-Modal Semantic Alignment Gap shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Start with a small frozen-feature diagnostic and one public benchmark before scaling to full training.
- Target evidence papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 AuViRe: Audio-visual Speech Representation Reconstruction for Deepfake Temporal Localization
- Method evidence papers:
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
  - 2026 Keeping the Evidence Chain: Semantic Evidence Allocation for Training-Free Token Pruning in Video Temporal Grounding
  - 2026 MASRA: MLLM-Assisted Semantic-Relational Consistent Alignment for Video Temporal Grounding

## 17. Open-Set or Refusal-Aware Modeling for LLM Temporal Reasoning and Time Output Instability  
Score: 5.8

- Target problem: P07 LLM Temporal Reasoning and Time Output Instability
- Transfer method: M07 Open-Set or Refusal-Aware Modeling
- Current usage in target cluster: 3
- Rationale: Open-Set or Refusal-Aware Modeling has been used in adjacent settings, while LLM Temporal Reasoning and Time Output Instability shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use a VideoLLM temporal grounding benchmark; evaluate time-span accuracy, evidence consistency, and failure/refusal behavior.
- Target evidence papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
- Method evidence papers:
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
  - 2026 Grounding is All You Need? Dual Temporal Grounding for Video Dialog
  - 2026 Learning Consistent Temporal Grounding between Related Tasks in Sports Coaching

## 18. Memory for LLM Temporal Reasoning and Time Output Instability  
Score: 5.8

- Target problem: P07 LLM Temporal Reasoning and Time Output Instability
- Transfer method: M09 Memory, Graph, or Structure Alignment
- Current usage in target cluster: 9
- Rationale: Memory, Graph, or Structure Alignment has been used in adjacent settings, while LLM Temporal Reasoning and Time Output Instability shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use a VideoLLM temporal grounding benchmark; evaluate time-span accuracy, evidence consistency, and failure/refusal behavior.
- Target evidence papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
- Method evidence papers:
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
  - 2026 Keeping the Evidence Chain: Semantic Evidence Allocation for Training-Free Token Pruning in Video Temporal Grounding
  - 2026 MASRA: MLLM-Assisted Semantic-Relational Consistent Alignment for Video Temporal Grounding

## 19. Weak-Supervision and Pseudo-Label Correction for Domain Shift and Generalization  
Score: 5.8

- Target problem: P08 Domain Shift and Generalization
- Transfer method: M13 Weak-Supervision and Pseudo-Label Correction
- Current usage in target cluster: 13
- Rationale: Weak-Supervision and Pseudo-Label Correction has been used in adjacent settings, while Domain Shift and Generalization shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Start with a small frozen-feature diagnostic and one public benchmark before scaling to full training.
- Target evidence papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 AuViRe: Audio-visual Speech Representation Reconstruction for Deepfake Temporal Localization
- Method evidence papers:
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Mining Forgery Traces from Reconstruction Error: A Weakly Supervised Framework for Multimodal Deepfake Temporal Localization
  - 2026 Multi-proposal collaboration and multi-task training for weakly-supervised video moment retrieval

## 20. Pretraining for Spatio-Temporal and Object/Event-Level Grounding  
Score: 5.8

- Target problem: P10 Spatio-Temporal and Object/Event-Level Grounding
- Transfer method: M01 Pretraining, Pseudo-Labeling, and Data Generation
- Current usage in target cluster: 15
- Rationale: Pretraining, Pseudo-Labeling, and Data Generation has been used in adjacent settings, while Spatio-Temporal and Object/Event-Level Grounding shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use spatio-temporal grounding data or object-event annotations; evaluate whether the transferred module improves temporal localization with spatial evidence.
- Target evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding
- Method evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 AuViRe: Audio-visual Speech Representation Reconstruction for Deepfake Temporal Localization
  - 2026 EvoGround: Self-Evolving Video Agents for Video Temporal Grounding

## 21. Memory for Spatio-Temporal and Object/Event-Level Grounding  
Score: 5.8

- Target problem: P10 Spatio-Temporal and Object/Event-Level Grounding
- Transfer method: M09 Memory, Graph, or Structure Alignment
- Current usage in target cluster: 12
- Rationale: Memory, Graph, or Structure Alignment has been used in adjacent settings, while Spatio-Temporal and Object/Event-Level Grounding shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use spatio-temporal grounding data or object-event annotations; evaluate whether the transferred module improves temporal localization with spatial evidence.
- Target evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding
- Method evidence papers:
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
  - 2026 Keeping the Evidence Chain: Semantic Evidence Allocation for Training-Free Token Pruning in Video Temporal Grounding
  - 2026 MASRA: MLLM-Assisted Semantic-Relational Consistent Alignment for Video Temporal Grounding

## 22. Multi-Modal Fusion and Feature Enhancement for Spatio-Temporal and Object/Event-Level Grounding  
Score: 5.8

- Target problem: P10 Spatio-Temporal and Object/Event-Level Grounding
- Transfer method: M12 Multi-Modal Fusion and Feature Enhancement
- Current usage in target cluster: 18
- Rationale: Multi-Modal Fusion and Feature Enhancement has been used in adjacent settings, while Spatio-Temporal and Object/Event-Level Grounding shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use spatio-temporal grounding data or object-event annotations; evaluate whether the transferred module improves temporal localization with spatial evidence.
- Target evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding
- Method evidence papers:
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 AuViRe: Audio-visual Speech Representation Reconstruction for Deepfake Temporal Localization
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding

## 23. LLM Reasoning for Dataset, Benchmark, and Evaluation Mismatch  
Score: 5.8

- Target problem: P11 Dataset, Benchmark, and Evaluation Mismatch
- Transfer method: M08 LLM Reasoning, Agentic Workflows, or RL Post-Training
- Current usage in target cluster: 24
- Rationale: LLM Reasoning, Agentic Workflows, or RL Post-Training has been used in adjacent settings, while Dataset, Benchmark, and Evaluation Mismatch shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Start with a small frozen-feature diagnostic and one public benchmark before scaling to full training.
- Target evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 AuViRe: Audio-visual Speech Representation Reconstruction for Deepfake Temporal Localization
  - 2026 Beyond Caption-Based Queries for Video Moment Retrieval
- Method evidence papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization

## 24. Uncertainty for Boundary Ambiguity and Localization Precision  
Score: 5.42

- Target problem: P02 Boundary Ambiguity and Localization Precision
- Transfer method: M06 Uncertainty, Evidential Learning, and Calibration
- Current usage in target cluster: 2
- Rationale: Uncertainty, Evidential Learning, and Calibration has been used in adjacent settings, while Boundary Ambiguity and Localization Precision shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 CVA: Context-aware Video-text Alignment for Video Temporal Grounding
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
- Method evidence papers:
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 Improving Temporal Localization in Vision-Language Video Anomaly Detection
  - 2026 Retrieving Any Relevant Moments: Benchmark and Models for Generalized Moment Retrieval

## 25. Uncertainty-Aware Sparse Evidence Selection for Long-Video Grounding  
Score: 5.42

- Target problem: P03 Long-Video Evidence Sparsity and Efficient Selection
- Transfer method: M06 Uncertainty, Evidential Learning, and Calibration
- Current usage in target cluster: 3
- Rationale: Uncertainty, Evidential Learning, and Calibration has been used in adjacent settings, while Long-Video Evidence Sparsity and Efficient Selection shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding
  - 2026 E.M.Ground: A Temporal Grounding Vid-LLM with Holistic Event Perception and Matching
- Method evidence papers:
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 Improving Temporal Localization in Vision-Language Video Anomaly Detection
  - 2026 Retrieving Any Relevant Moments: Benchmark and Models for Generalized Moment Retrieval

## 26. Uncertainty for LLM Temporal Reasoning and Time Output Instability  
Score: 5.42

- Target problem: P07 LLM Temporal Reasoning and Time Output Instability
- Transfer method: M06 Uncertainty, Evidential Learning, and Calibration
- Current usage in target cluster: 3
- Rationale: Uncertainty, Evidential Learning, and Calibration has been used in adjacent settings, while LLM Temporal Reasoning and Time Output Instability shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use a VideoLLM temporal grounding benchmark; evaluate time-span accuracy, evidence consistency, and failure/refusal behavior.
- Target evidence papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding
  - 2026 Agentic Spatio-Temporal Grounding via Collaborative Reasoning
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
- Method evidence papers:
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 Improving Temporal Localization in Vision-Language Video Anomaly Detection
  - 2026 Retrieving Any Relevant Moments: Benchmark and Models for Generalized Moment Retrieval

## 27. Uncertainty for Domain Shift and Generalization  
Score: 5.42

- Target problem: P08 Domain Shift and Generalization
- Transfer method: M06 Uncertainty, Evidential Learning, and Calibration
- Current usage in target cluster: 3
- Rationale: Uncertainty, Evidential Learning, and Calibration has been used in adjacent settings, while Domain Shift and Generalization shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Start with a small frozen-feature diagnostic and one public benchmark before scaling to full training.
- Target evidence papers:
  - 2026 ActPrompt: In-Domain Feature Adaptation via Action Cues for Video Temporal Grounding
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 AuViRe: Audio-visual Speech Representation Reconstruction for Deepfake Temporal Localization
- Method evidence papers:
  - 2026 Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval
  - 2026 Improving Temporal Localization in Vision-Language Video Anomaly Detection
  - 2026 Retrieving Any Relevant Moments: Benchmark and Models for Generalized Moment Retrieval

## 28. State-Space for Boundary Ambiguity and Localization Precision  
Score: 4.8

- Target problem: P02 Boundary Ambiguity and Localization Precision
- Transfer method: M11 State-Space, Mamba, or Efficient Sequence Modeling
- Current usage in target cluster: 3
- Rationale: State-Space, Mamba, or Efficient Sequence Modeling has been used in adjacent settings, while Boundary Ambiguity and Localization Precision shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 A Two-stage Transformer Framework for Temporal Localization of Distracted Driver Behaviors
  - 2026 CVA: Context-aware Video-text Alignment for Video Temporal Grounding
  - 2026 ClipTBP: Clip-Pair based Temporal Boundary Prediction with Boundary-Aware Learning for Moment Retrieval
- Method evidence papers:
  - 2026 HieraMamba: Video Temporal Grounding via Hierarchical Anchor-Mamba Pooling
  - 2026 Mamba-based modulated fusion model for video moment retrieval
  - 2026 See More, Store Less: Memory-Efficient Resolution for Video Moment Retrieval

## 29. State-Space for Long-Video Evidence Sparsity and Efficient Selection  
Score: 4.8

- Target problem: P03 Long-Video Evidence Sparsity and Efficient Selection
- Transfer method: M11 State-Space, Mamba, or Efficient Sequence Modeling
- Current usage in target cluster: 4
- Rationale: State-Space, Mamba, or Efficient Sequence Modeling has been used in adjacent settings, while Long-Video Evidence Sparsity and Efficient Selection shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic.
- Target evidence papers:
  - 2026 Beyond Closed-Pool Video Retrieval: A Benchmark and Agent Framework for Real-World Video Search and Moment Localization
  - 2026 Bridging Time and Space: Decoupled Spatio-Temporal Alignment for Video Grounding
  - 2026 E.M.Ground: A Temporal Grounding Vid-LLM with Holistic Event Perception and Matching
- Method evidence papers:
  - 2026 HieraMamba: Video Temporal Grounding via Hierarchical Anchor-Mamba Pooling
  - 2026 Mamba-based modulated fusion model for video moment retrieval
  - 2026 See More, Store Less: Memory-Efficient Resolution for Video Moment Retrieval

## 30. Query-Conditioned Frame/Clip Selection for Scalability and Corpus-Level Retrieval  
Score: 4.8

- Target problem: P09 Scalability and Corpus-Level Retrieval
- Transfer method: M02 Query-Conditioned Frame/Clip Selection
- Current usage in target cluster: 3
- Rationale: Query-Conditioned Frame/Clip Selection has been used in adjacent settings, while Scalability and Corpus-Level Retrieval shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Start with a small frozen-feature diagnostic and one public benchmark before scaling to full training.
- Target evidence papers:
  - 2026 Event-aware Video Corpus Moment Retrieval
  - 2026 GenSpan: Generation-Calibrated Motion Span Priors for Multi-Verb Video Corpus Moment Retrieval
  - 2026 Grounding is All You Need? Dual Temporal Grounding for Video Dialog
- Method evidence papers:
  - 2026 Fewer Steps, Better Performance: Efficient Cross-Modal Clip Trimming for Video Moment Retrieval Using Language
  - 2026 GroundVTS: Visual Token Sampling in Multimodal Large Language Models for Video Temporal Grounding
  - 2026 Rethinking Weakly-Supervised Video Temporal Grounding From a Game Perspective

## 31. State-Space for Scalability and Corpus-Level Retrieval  
Score: 3.8

- Target problem: P09 Scalability and Corpus-Level Retrieval
- Transfer method: M11 State-Space, Mamba, or Efficient Sequence Modeling
- Current usage in target cluster: 3
- Rationale: State-Space, Mamba, or Efficient Sequence Modeling has been used in adjacent settings, while Scalability and Corpus-Level Retrieval shares a compatible failure mode but shows limited usage of this method in the current local corpus.
- Minimal experiment: Start with a small frozen-feature diagnostic and one public benchmark before scaling to full training.
- Target evidence papers:
  - 2026 Event-aware Video Corpus Moment Retrieval
  - 2026 GenSpan: Generation-Calibrated Motion Span Priors for Multi-Verb Video Corpus Moment Retrieval
  - 2026 Grounding is All You Need? Dual Temporal Grounding for Video Dialog
- Method evidence papers:
  - 2026 HieraMamba: Video Temporal Grounding via Hierarchical Anchor-Mamba Pooling
  - 2026 Mamba-based modulated fusion model for video moment retrieval
  - 2026 See More, Store Less: Memory-Efficient Resolution for Video Moment Retrieval
