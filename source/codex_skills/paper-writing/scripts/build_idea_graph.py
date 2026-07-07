from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_LIBRARY_DIR = Path(r"D:\syz_autopaper\auto_idea\video moment retrieval\download_paper")
DEFAULT_OUT_DIR = Path(r"D:\syz_autopaper\auto_idea\video moment retrieval\idea_graph")


PROBLEM_CLUSTERS: list[dict[str, Any]] = [
    {
        "id": "P01",
        "name": "Annotation Scarcity and Noisy Supervision",
        "canonical_question": "How can VMR/VTG learn with fewer, cheaper, or noisier temporal annotations?",
        "root_cause": "Temporal boundary annotations are expensive and pseudo labels are often mismatched or imprecise.",
        "keywords": [
            "annotation", "annotations", "unlabeled", "unlabelled", "pseudo", "weakly-supervised",
            "weak supervision", "without training", "zero-shot", "few-shot", "label", "labels",
            "pretraining", "dataset construction",
        ],
    },
    {
        "id": "P02",
        "name": "Boundary Ambiguity and Localization Precision",
        "canonical_question": "How can models predict accurate temporal boundaries when event starts and ends are ambiguous?",
        "root_cause": "Language-described events rarely have a single crisp temporal interval.",
        "keywords": [
            "boundary", "boundaries", "temporal boundary", "precise", "precision", "granularity",
            "coarse-to-fine", "localization error", "timestamp", "time stamp", "iou", "duration",
        ],
    },
    {
        "id": "P03",
        "name": "Long-Video Evidence Sparsity and Efficient Selection",
        "canonical_question": "How can models find sparse evidence in long videos without wasting tokens or frames?",
        "root_cause": "Relevant evidence is sparse while dense frame processing is expensive and noisy.",
        "keywords": [
            "long video", "long-form", "hour-long", "long videos", "frame sampling", "sampling",
            "tokens", "token", "efficient", "memory", "clip trimming", "frame selection",
            "evidence", "sparse", "dense sampling", "resolution",
        ],
    },
    {
        "id": "P04",
        "name": "Query Ambiguity, Invalid Queries, and Open-Set Retrieval",
        "canonical_question": "How should systems behave when the query is ambiguous, invalid, underspecified, or has no matching moment?",
        "root_cause": "Benchmarks often assume every query is valid, but real users issue uncertain or impossible queries.",
        "keywords": [
            "invalid", "open-set", "open set", "irrelevant", "hard-irrelevant", "refuse", "refusal",
            "ambiguous", "ambiguity", "underspecified", "not all inputs", "out-of-scope", "no answer",
        ],
    },
    {
        "id": "P05",
        "name": "Multi-Moment, Compositional, and Complex Query Grounding",
        "canonical_question": "How can systems ground queries that refer to multiple moments, relations, or multi-hop evidence?",
        "root_cause": "Single-interval retrieval is insufficient for compositional or multi-event user intent.",
        "keywords": [
            "multi-moment", "multiple moments", "one-to-many", "multi-hop", "compositional",
            "complex queries", "corpus moment", "moments", "related tasks", "event-aware", "event aware",
        ],
    },
    {
        "id": "P06",
        "name": "Cross-Modal Semantic Alignment Gap",
        "canonical_question": "How can language, visual, audio, and temporal representations stay semantically aligned?",
        "root_cause": "Video-language representations often align global semantics but miss fine temporal evidence.",
        "keywords": [
            "alignment", "align", "cross-modal", "cross modal", "semantic gap", "video-text",
            "vision-language", "audio-visual", "multimodal", "representation", "relevance score",
        ],
    },
    {
        "id": "P07",
        "name": "LLM Temporal Reasoning and Time Output Instability",
        "canonical_question": "How can Video/Multimodal LLMs reason about time and output reliable temporal spans?",
        "root_cause": "LLMs reason fluently but have weak temporal localization, unstable time formats, and hallucinated evidence.",
        "keywords": [
            "llm", "large language model", "multimodal large language", "mllm", "vlm", "reasoning",
            "chain", "agent", "agentic", "time output", "thinking", "hallucination", "video llm",
        ],
    },
    {
        "id": "P08",
        "name": "Domain Shift and Generalization",
        "canonical_question": "How can methods generalize across datasets, domains, video styles, and unseen query distributions?",
        "root_cause": "Dataset-specific priors and annotation styles cause brittle cross-domain transfer.",
        "keywords": [
            "generalization", "generalize", "cross-domain", "domain", "out-of-distribution",
            "distribution", "robust", "robustness", "transfer", "unseen", "zero-shot",
        ],
    },
    {
        "id": "P09",
        "name": "Scalability and Corpus-Level Retrieval",
        "canonical_question": "How can retrieval scale from one video to large corpora or real-world open pools?",
        "root_cause": "Searching many long videos introduces retrieval, memory, and ranking bottlenecks.",
        "keywords": [
            "corpus", "large-scale", "scalable", "retrieving any", "open pool", "benchmarking",
            "video corpus", "retrieval dataset", "real-world video retrieval", "memory-efficient",
        ],
    },
    {
        "id": "P10",
        "name": "Spatio-Temporal and Object/Event-Level Grounding",
        "canonical_question": "How can temporal grounding incorporate objects, regions, events, or spatial evidence?",
        "root_cause": "Temporal moments are often defined by object interactions and spatial evidence, not only clip-level semantics.",
        "keywords": [
            "spatio-temporal", "spatial-temporal", "spatial", "object", "object-centric",
            "region", "pixel-level", "tube", "event", "scene", "3d", "aerial",
        ],
    },
    {
        "id": "P11",
        "name": "Dataset, Benchmark, and Evaluation Mismatch",
        "canonical_question": "Are current datasets, metrics, and evaluation protocols measuring the right temporal grounding ability?",
        "root_cause": "Existing benchmarks may not reflect real user queries, long videos, invalid queries, or annotation ambiguity.",
        "keywords": [
            "benchmark", "dataset", "metric", "evaluation", "protocol", "statistics", "bias",
            "data", "real-world", "comparison of dataset", "highlight detection datasets",
        ],
    },
    {
        "id": "P12",
        "name": "Uncertainty, Calibration, and Rejection",
        "canonical_question": "How can models know when temporal evidence is uncertain and calibrate or reject predictions?",
        "root_cause": "Hard deterministic predictions hide ambiguity, weak evidence, and confidence errors.",
        "keywords": [
            "uncertainty", "uncertain", "evidential", "calibration", "confidence", "rejection",
            "risk", "abstain", "abstention", "reliable", "calibrated",
        ],
    },
]


METHOD_CLUSTERS: list[dict[str, Any]] = [
    {
        "id": "M01",
        "name": "Pretraining, Pseudo-Labeling, and Data Generation",
        "keywords": ["pretraining", "pseudo", "unlabeled", "dataset", "data construction", "synthetic", "self-training"],
    },
    {
        "id": "M02",
        "name": "Query-Conditioned Frame/Clip Selection",
        "keywords": ["frame selection", "sampling", "clip trimming", "token sampling", "important word", "selection", "rank and filter"],
    },
    {
        "id": "M03",
        "name": "Coarse-to-Fine or Hierarchical Localization",
        "keywords": ["coarse-to-fine", "hierarchical", "two-stage", "multi-scale", "pyramid", "refine", "refinement"],
    },
    {
        "id": "M04",
        "name": "Transformer/DETR-Style Proposal Decoding",
        "keywords": ["detr", "transformer", "proposal", "decoder", "anchor", "query decoder", "matching"],
    },
    {
        "id": "M05",
        "name": "Boundary Refinement and Temporal Clustering",
        "keywords": ["boundary", "cluster", "clustering", "temporal cluster", "duration-aware", "iou-aware", "span prior"],
    },
    {
        "id": "M06",
        "name": "Uncertainty, Evidential Learning, and Calibration",
        "keywords": ["uncertainty", "evidential", "calibration", "confidence", "rejection", "risk", "abstain"],
    },
    {
        "id": "M07",
        "name": "Open-Set or Refusal-Aware Modeling",
        "keywords": ["open-set", "invalid", "irrelevant", "refuse", "refusal", "no answer", "hard-irrelevant"],
    },
    {
        "id": "M08",
        "name": "LLM Reasoning, Agentic Workflows, or RL Post-Training",
        "keywords": ["llm", "mllm", "reasoning", "agent", "agentic", "reinforcement", "rl", "prompt", "chain"],
    },
    {
        "id": "M09",
        "name": "Memory, Graph, or Structure Alignment",
        "keywords": ["graph", "memory", "structure", "evidence chain", "semantic evidence", "relational", "consensus"],
    },
    {
        "id": "M10",
        "name": "Contrastive or Cross-Modal Alignment",
        "keywords": ["contrastive", "alignment", "align", "video-text", "cross-modal", "representation", "semantic"],
    },
    {
        "id": "M11",
        "name": "State-Space, Mamba, or Efficient Sequence Modeling",
        "keywords": ["mamba", "state-space", "linear", "efficient sequence", "memory-efficient"],
    },
    {
        "id": "M12",
        "name": "Multi-Modal Fusion and Feature Enhancement",
        "keywords": ["fusion", "multimodal", "audio-visual", "feature enhancement", "adapter", "visual token"],
    },
    {
        "id": "M13",
        "name": "Weak-Supervision and Pseudo-Label Correction",
        "keywords": ["weakly-supervised", "weak supervision", "pseudo label", "correction", "distillation", "teacher"],
    },
    {
        "id": "M14",
        "name": "Benchmark or Dataset Construction",
        "keywords": ["benchmark", "dataset", "data", "evaluation", "construct", "large-scale"],
    },
    {
        "id": "M15",
        "name": "Object/Event/Spatio-Temporal Modules",
        "keywords": ["object", "event", "spatio-temporal", "spatial-temporal", "region", "tube", "scene"],
    },
]


TRANSFER_COMPATIBILITY: dict[str, list[str]] = {
    "M01": ["P01", "P08", "P09", "P10", "P11"],
    "M02": ["P02", "P03", "P04", "P05", "P09"],
    "M03": ["P02", "P03", "P05", "P10"],
    "M04": ["P02", "P05", "P09", "P10"],
    "M05": ["P02", "P03", "P12"],
    "M06": ["P02", "P03", "P04", "P07", "P08", "P12"],
    "M07": ["P03", "P04", "P07", "P12"],
    "M08": ["P04", "P05", "P07", "P10", "P11"],
    "M09": ["P05", "P06", "P07", "P10"],
    "M10": ["P02", "P05", "P06", "P08", "P10"],
    "M11": ["P03", "P09", "P02"],
    "M12": ["P06", "P07", "P10", "P03"],
    "M13": ["P01", "P02", "P08", "P12"],
    "M14": ["P04", "P05", "P09", "P11"],
    "M15": ["P05", "P06", "P10", "P02"],
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def read_text(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text[:limit] if limit else text


def clean_text(text: str) -> str:
    text = re.sub(r"--- Page \d+ ---", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [part.strip() for part in parts if 30 <= len(part.strip()) <= 420]


def keyword_score(text: str, keywords: list[str]) -> int:
    lower = text.lower()
    score = 0
    for keyword in keywords:
        pattern = re.escape(keyword.lower())
        if " " in keyword or "-" in keyword:
            score += 3 * len(re.findall(pattern, lower))
        else:
            score += len(re.findall(rf"\b{pattern}\b", lower))
    return score


def evidence_sentence(sentences: list[str], keywords: list[str]) -> str:
    best = ""
    best_score = 0
    for sentence in sentences:
        score = keyword_score(sentence, keywords)
        if score > best_score:
            best = sentence
            best_score = score
    return best


def classify(text: str, clusters: list[dict[str, Any]], max_items: int, threshold: int = 2) -> list[dict[str, Any]]:
    sentences = split_sentences(text)
    scored = []
    for cluster in clusters:
        score = keyword_score(text, cluster["keywords"])
        if score >= threshold:
            scored.append(
                {
                    "id": cluster["id"],
                    "name": cluster["name"],
                    "score": score,
                    "evidence_sentence": evidence_sentence(sentences, cluster["keywords"]),
                }
            )
    scored.sort(key=lambda row: (-row["score"], row["id"]))
    return scored[:max_items]


def infer_task(title: str, text: str) -> str:
    lower = f"{title} {text}".lower()
    if "highlight" in lower and "moment" in lower:
        return "moment retrieval and highlight detection"
    if "spatio-temporal" in lower or "spatial-temporal" in lower:
        return "spatio-temporal video grounding"
    if "llm" in lower or "large language model" in lower or "mllm" in lower:
        return "LLM-based video temporal grounding"
    if "moment retrieval" in lower:
        return "video moment retrieval"
    if "temporal grounding" in lower or "video grounding" in lower:
        return "video temporal grounding"
    if "temporal localization" in lower:
        return "temporal localization"
    return "video-language temporal retrieval/localization"


def load_paper_dirs(library_dir: Path) -> list[Path]:
    out = []
    for paper_dir in sorted(path for path in library_dir.iterdir() if path.is_dir()):
        report = read_json(paper_dir / "repair_report.json", default={})
        if report.get("status") == "ok" and (paper_dir / "paper.pdf").exists():
            out.append(paper_dir)
    return out


def build_paper_card(paper_dir: Path) -> dict[str, Any]:
    metadata = read_json(paper_dir / "metadata.json", default={}) or {}
    title = metadata.get("title") or paper_dir.name
    year = int(metadata.get("year") or 0)
    abstract = clean_text(read_text(paper_dir / "abstract.md", limit=8000))
    introduction = clean_text(read_text(paper_dir / "introduction.md", limit=20000))
    full_fallback = clean_text(read_text(paper_dir / "full_text.txt", limit=12000))
    text = " ".join(part for part in [title, metadata.get("summary") or "", abstract, introduction or full_fallback] if part)
    problems = classify(text, PROBLEM_CLUSTERS, max_items=3, threshold=2)
    methods = classify(text, METHOD_CLUSTERS, max_items=4, threshold=2)
    if not problems:
        problems = [
            {
                "id": "P06",
                "name": "Cross-Modal Semantic Alignment Gap",
                "score": 0,
                "evidence_sentence": "",
            }
        ]
    return {
        "paper_id": paper_dir.name,
        "local_dir": str(paper_dir),
        "title": title,
        "year": year,
        "venue": metadata.get("venue") or "",
        "authors": metadata.get("authors") or [],
        "task": infer_task(title, text),
        "problems": problems,
        "methods": methods,
        "datasets": extract_dataset_mentions(text),
        "metrics": extract_metric_mentions(text),
        "domain_relevance": domain_relevance(title, text),
        "abstract_source": str(paper_dir / "abstract.md"),
        "introduction_source": str(paper_dir / "introduction.md"),
    }


def domain_relevance(title: str, text: str) -> dict[str, Any]:
    lower = f"{title} {text}".lower()
    positives = {
        "video": 4,
        "moment retrieval": 4,
        "video moment": 4,
        "temporal grounding": 4,
        "video grounding": 4,
        "video temporal": 3,
        "video-language": 3,
        "vision-language": 2,
        "multimodal": 2,
        "mllm": 2,
        "vlm": 2,
        "highlight detection": 3,
        "frame": 1,
        "clip": 1,
        "visual": 1,
    }
    negatives = [
        "quantum", "nuclear", "arrhythmia", "fiber", "fibers", "eavesdropping",
        "gravitational", "singularity", "speech diarization", "asr", "audio language",
        "micro-expression", "cucurbit", "time photonic",
    ]
    hits = [phrase for phrase in positives if phrase in lower]
    score = sum(positives[phrase] for phrase in hits)
    negative_hits = [phrase for phrase in negatives if phrase in lower]
    relevant = score >= 4 and not (negative_hits and score < 7)
    return {
        "is_video_vmr_related": relevant,
        "score": score,
        "positive_hits": hits,
        "negative_hits": negative_hits,
    }


def extract_dataset_mentions(text: str) -> list[str]:
    known = [
        "QVHighlights", "Charades-STA", "ActivityNet", "TACoS", "DiDeMo", "Ego4D",
        "QuerYD", "HiREST", "VideoITG", "MLVU", "LongVideoBench", "VideoMME",
        "Moment-10M", "MAD", "YouCook", "TVSum", "YouTube Highlights",
    ]
    lower = text.lower()
    return sorted({name for name in known if name.lower() in lower})


def extract_metric_mentions(text: str) -> list[str]:
    known = ["R@1", "R1", "mIoU", "IoU", "mAP", "NDCG", "Recall", "Hit@1", "MR", "HD"]
    lower = text.lower()
    return sorted({name for name in known if name.lower() in lower})


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_cards(cards: list[dict[str, Any]], out_dir: Path) -> None:
    card_dir = ensure_dir(out_dir / "paper_cards")
    if card_dir.exists():
        shutil.rmtree(card_dir)
        card_dir.mkdir(parents=True, exist_ok=True)
    for card in cards:
        write_json(card_dir / f"{card['paper_id']}.json", card)


def cluster_lookup(clusters: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {cluster["id"]: cluster for cluster in clusters}


def build_problem_clusters(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = cluster_lookup(PROBLEM_CLUSTERS)
    rows = []
    for problem_id, cluster in lookup.items():
        papers = [card for card in cards if any(problem["id"] == problem_id for problem in card["problems"])]
        if not papers:
            continue
        counts = Counter(str(card["year"]) for card in papers if card.get("year"))
        representative = sorted(
            [
                {
                    "title": card["title"],
                    "year": card["year"],
                    "venue": card.get("venue", ""),
                    "paper_id": card["paper_id"],
                    "evidence_sentence": next((p["evidence_sentence"] for p in card["problems"] if p["id"] == problem_id), ""),
                }
                for card in papers
            ],
            key=lambda row: (-int(row["year"] or 0), row["title"]),
        )[:8]
        method_counts = Counter(
            method["id"]
            for card in papers
            for method in card.get("methods", [])
        )
        rows.append(
            {
                "problem_id": problem_id,
                "name": cluster["name"],
                "canonical_question": cluster["canonical_question"],
                "root_cause": cluster["root_cause"],
                "first_seen_year": min(card["year"] for card in papers if card.get("year")),
                "paper_count": len(papers),
                "paper_count_by_year": dict(sorted(counts.items())),
                "representative_papers": representative,
                "dominant_methods": method_counts.most_common(8),
            }
        )
    rows.sort(key=lambda row: (-row["paper_count"], row["problem_id"]))
    return rows


def build_method_clusters(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = cluster_lookup(METHOD_CLUSTERS)
    rows = []
    for method_id, cluster in lookup.items():
        papers = [card for card in cards if any(method["id"] == method_id for method in card.get("methods", []))]
        if not papers:
            continue
        problem_counts = Counter(problem["id"] for card in papers for problem in card["problems"])
        rows.append(
            {
                "method_id": method_id,
                "name": cluster["name"],
                "first_seen_year": min(card["year"] for card in papers if card.get("year")),
                "paper_count": len(papers),
                "paper_count_by_year": dict(sorted(Counter(str(card["year"]) for card in papers).items())),
                "source_problems": problem_counts.most_common(8),
                "representative_papers": [
                    {"title": card["title"], "year": card["year"], "paper_id": card["paper_id"]}
                    for card in sorted(papers, key=lambda row: (-int(row["year"] or 0), row["title"]))[:8]
                ],
            }
        )
    rows.sort(key=lambda row: (-row["paper_count"], row["method_id"]))
    return rows


def write_matrix(cards: list[dict[str, Any]], out_dir: Path) -> dict[tuple[str, str], int]:
    problem_ids = [row["id"] for row in PROBLEM_CLUSTERS]
    method_ids = [row["id"] for row in METHOD_CLUSTERS]
    matrix: dict[tuple[str, str], int] = {}
    for problem_id in problem_ids:
        for method_id in method_ids:
            matrix[(problem_id, method_id)] = sum(
                any(problem["id"] == problem_id for problem in card["problems"])
                and any(method["id"] == method_id for method in card.get("methods", []))
                for card in cards
            )
    with (out_dir / "problem_method_matrix.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["problem_id", "problem_name", *method_ids])
        problem_names = {row["id"]: row["name"] for row in PROBLEM_CLUSTERS}
        for problem_id in problem_ids:
            writer.writerow([problem_id, problem_names[problem_id], *[matrix[(problem_id, method_id)] for method_id in method_ids]])
    return matrix


def problem_recency_score(cluster: dict[str, Any]) -> float:
    counts = {int(year): count for year, count in cluster["paper_count_by_year"].items()}
    first = int(cluster["first_seen_year"])
    score = 0.0
    if first >= 2025:
        score += 2.0
    if counts.get(2026, 0) >= counts.get(2025, 0):
        score += 1.0
    score += min(2.0, counts.get(2026, 0) / 5.0)
    return score


def build_opportunities(problem_clusters: list[dict[str, Any]], method_clusters: list[dict[str, Any]], matrix: dict[tuple[str, str], int]) -> list[dict[str, Any]]:
    problems = {row["problem_id"]: row for row in problem_clusters}
    methods = {row["method_id"]: row for row in method_clusters}
    opportunities = []
    for method_id, target_problem_ids in TRANSFER_COMPATIBILITY.items():
        if method_id not in methods:
            continue
        method = methods[method_id]
        source_maturity = method["paper_count"]
        if source_maturity < 2:
            continue
        source_problem = method["source_problems"][0][0] if method.get("source_problems") else ""
        for problem_id in target_problem_ids:
            if problem_id not in problems:
                continue
            target = problems[problem_id]
            current_use = matrix.get((problem_id, method_id), 0)
            if current_use >= max(2, int(target["paper_count"] * 0.25)):
                continue
            saturation_penalty = 2.0 if target["paper_count"] >= 25 else 0.5 if target["paper_count"] >= 15 else 0.0
            score = (
                2.0
                + problem_recency_score(target)
                + min(2.0, source_maturity / 8.0)
                + (2.0 if current_use == 0 else 0.8)
                - saturation_penalty
            )
            opportunities.append(
                {
                    "score": round(score, 2),
                    "target_problem_id": problem_id,
                    "target_problem": target["name"],
                    "source_problem_id": source_problem,
                    "source_method_id": method_id,
                    "source_method": method["name"],
                    "current_use_in_target": current_use,
                    "source_method_paper_count": source_maturity,
                    "target_problem_paper_count": target["paper_count"],
                    "rationale": transfer_rationale(method_id, problem_id),
                    "candidate_idea": candidate_idea_title(method_id, problem_id),
                    "minimal_experiment": minimal_experiment(problem_id, method_id),
                    "representative_target_papers": target["representative_papers"][:3],
                    "representative_method_papers": method["representative_papers"][:3],
                }
            )
    opportunities.sort(key=lambda row: (-row["score"], row["target_problem_id"], row["source_method_id"]))
    return opportunities[:40]


def transfer_rationale(method_id: str, problem_id: str) -> str:
    method = cluster_lookup(METHOD_CLUSTERS)[method_id]["name"]
    problem = cluster_lookup(PROBLEM_CLUSTERS)[problem_id]["name"]
    return f"{method} has been used in adjacent settings, while {problem} shares a compatible failure mode but shows limited usage of this method in the current local corpus."


def candidate_idea_title(method_id: str, problem_id: str) -> str:
    titles = {
        ("M06", "P04"): "Evidence-Calibrated Open-Set Temporal Grounding",
        ("M06", "P03"): "Uncertainty-Aware Sparse Evidence Selection for Long-Video Grounding",
        ("M07", "P03"): "Refusal-Aware Long-Video Moment Retrieval under Insufficient Evidence",
        ("M02", "P04"): "Query-Conditioned Evidence Sufficiency Testing for Invalid Moment Queries",
        ("M08", "P05"): "Agentic Decomposition for Multi-Moment Video Grounding",
        ("M03", "P10"): "Hierarchical Object-to-Moment Grounding for Spatio-Temporal Queries",
        ("M01", "P12"): "Pseudo-Label Uncertainty Correction for Ambiguous Moment Boundaries",
    }
    if (method_id, problem_id) in titles:
        return titles[(method_id, problem_id)]
    method = cluster_lookup(METHOD_CLUSTERS)[method_id]["name"].split(",")[0]
    problem = cluster_lookup(PROBLEM_CLUSTERS)[problem_id]["name"]
    return f"{method} for {problem}"


def minimal_experiment(problem_id: str, method_id: str) -> str:
    if problem_id in {"P02", "P03", "P04", "P05"}:
        return "Use QVHighlights/Charades-STA-style retrieval splits; compare against a deterministic baseline with R@1/mIoU plus a problem-specific diagnostic."
    if problem_id == "P07":
        return "Use a VideoLLM temporal grounding benchmark; evaluate time-span accuracy, evidence consistency, and failure/refusal behavior."
    if problem_id == "P10":
        return "Use spatio-temporal grounding data or object-event annotations; evaluate whether the transferred module improves temporal localization with spatial evidence."
    return "Start with a small frozen-feature diagnostic and one public benchmark before scaling to full training."


def write_timeline(problem_clusters: list[dict[str, Any]], out_dir: Path) -> None:
    lines = ["# Problem Timeline", ""]
    for cluster in sorted(problem_clusters, key=lambda row: (row["first_seen_year"], row["problem_id"])):
        counts = ", ".join(f"{year}: {count}" for year, count in cluster["paper_count_by_year"].items())
        lines.extend(
            [
                f"## {cluster['problem_id']} {cluster['name']}",
                "",
                f"- First seen in local corpus: {cluster['first_seen_year']}",
                f"- Paper count: {cluster['paper_count']}",
                f"- Count by year: {counts}",
                f"- Canonical question: {cluster['canonical_question']}",
                f"- Root cause: {cluster['root_cause']}",
                "- Representative papers:",
            ]
        )
        for paper in cluster["representative_papers"][:5]:
            lines.append(f"  - {paper['year']} {paper['title']} ({paper.get('venue') or 'unknown venue'})")
        lines.append("")
    (out_dir / "problem_timeline.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_opportunities(opportunities: list[dict[str, Any]], out_dir: Path) -> None:
    lines = ["# Transfer Opportunities", ""]
    for index, item in enumerate(opportunities, start=1):
        lines.extend(
            [
                f"## {index}. {item['candidate_idea']}  ",
                f"Score: {item['score']}",
                "",
                f"- Target problem: {item['target_problem_id']} {item['target_problem']}",
                f"- Transfer method: {item['source_method_id']} {item['source_method']}",
                f"- Current usage in target cluster: {item['current_use_in_target']}",
                f"- Rationale: {item['rationale']}",
                f"- Minimal experiment: {item['minimal_experiment']}",
                "- Target evidence papers:",
            ]
        )
        for paper in item["representative_target_papers"]:
            lines.append(f"  - {paper['year']} {paper['title']}")
        lines.append("- Method evidence papers:")
        for paper in item["representative_method_papers"]:
            lines.append(f"  - {paper['year']} {paper['title']}")
        lines.append("")
    (out_dir / "opportunity_cards.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_readme(cards: list[dict[str, Any]], problem_clusters: list[dict[str, Any]], method_clusters: list[dict[str, Any]], opportunities: list[dict[str, Any]], out_dir: Path) -> None:
    lines = [
        "# Idea Graph",
        "",
        "Local-only idea mining output built from already-downloaded papers.",
        "",
        f"- Papers processed: {len(cards)}",
        f"- Coarse problem clusters used: {len(problem_clusters)}",
        f"- Method clusters used: {len(method_clusters)}",
        f"- Transfer opportunities generated: {len(opportunities)}",
        "",
        "Important: problem clusters are intentionally coarse. Similar phrasings are collapsed into the same canonical problem to avoid one-paper-one-problem fragmentation.",
        "",
        "Files:",
        "",
        "- `paper_cards/`: per-paper structured cards.",
        "- `problem_clusters.json`: coarse problem taxonomy with first-seen year and yearly counts.",
        "- `method_clusters.json`: method taxonomy and source problem distribution.",
        "- `problem_method_matrix.csv`: problem x method usage matrix.",
        "- `problem_timeline.md`: readable time-ordered problem spectrum.",
        "- `opportunity_cards.md`: method-transfer idea candidates.",
    ]
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local problem-method idea graph from an existing paper library.")
    parser.add_argument("--library-dir", default=str(DEFAULT_LIBRARY_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-off-domain", action="store_true", help="Keep title-matched but non-video/off-domain papers.")
    args = parser.parse_args()

    library_dir = Path(args.library_dir)
    out_dir = ensure_dir(Path(args.out_dir))
    paper_dirs = load_paper_dirs(library_dir)
    if args.limit:
        paper_dirs = paper_dirs[: args.limit]
    all_cards = [build_paper_card(path) for path in paper_dirs]
    excluded = [card for card in all_cards if not card.get("domain_relevance", {}).get("is_video_vmr_related")]
    cards = all_cards if args.include_off_domain else [card for card in all_cards if card.get("domain_relevance", {}).get("is_video_vmr_related")]
    write_cards(cards, out_dir)
    problem_clusters = build_problem_clusters(cards)
    method_clusters = build_method_clusters(cards)
    matrix = write_matrix(cards, out_dir)
    opportunities = build_opportunities(problem_clusters, method_clusters, matrix)
    write_json(out_dir / "paper_cards_index.json", cards)
    write_json(out_dir / "excluded_off_domain.json", excluded if not args.include_off_domain else [])
    write_json(out_dir / "problem_clusters.json", problem_clusters)
    write_json(out_dir / "method_clusters.json", method_clusters)
    write_json(out_dir / "opportunities.json", opportunities)
    write_timeline(problem_clusters, out_dir)
    write_opportunities(opportunities, out_dir)
    write_readme(cards, problem_clusters, method_clusters, opportunities, out_dir)
    print(
        json.dumps(
            {
                "papers": len(cards),
                "input_papers": len(all_cards),
                "excluded_off_domain": 0 if args.include_off_domain else len(excluded),
                "problem_clusters": len(problem_clusters),
                "method_clusters": len(method_clusters),
                "opportunities": len(opportunities),
                "out_dir": str(out_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
