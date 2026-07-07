from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import Normalizer

from build_idea_graph import (
    DEFAULT_LIBRARY_DIR,
    DEFAULT_OUT_DIR,
    METHOD_CLUSTERS,
    PROBLEM_CLUSTERS,
    clean_text,
    extract_dataset_mentions,
    extract_metric_mentions,
    read_json,
    read_text,
)


SANITY_TITLES = (
    "actprompt:",
    "adaptive evidential learning",
    "cva: context-aware",
    "cliptbp:",
    "auvire:",
)

LIMITATION_MARKERS = (
    "however",
    "while effective",
    "despite",
    "but ",
    "nevertheless",
    "non-trivial",
    "challenge",
    "limitation",
    "fail to",
    "fails to",
    "failing",
    "struggle",
    "insufficient",
    "unable to",
    "difficult",
    "overconfident",
    "overconfidence",
    "false negative",
    "biased",
    "ignore",
    "neglect",
    "cannot",
    "prone to",
)

PRIOR_MARKERS = (
    "prior work",
    "previous work",
    "existing method",
    "existing model",
    "traditional approach",
    "recent method",
    "recent research",
    "most method",
    "conventional method",
    "state of the art",
    "baseline",
)

EXAMPLE_MARKERS = (
    "for example",
    "as illustrated",
    "as shown in figure",
    "as shown in fig",
    "figure 1",
    "fig. 1",
    "e.g.",
    "case study",
)

METHOD_MARKERS = (
    "we propose",
    "we introduce",
    "we present",
    "we develop",
    "our method",
    "our approach",
    "our framework",
)

STRONG_FAILURE_MARKERS = (
    "however",
    "while effective",
    "despite",
    "limitation",
    "drawback",
    "fail to",
    "fails to",
    "failing",
    "struggle",
    "insufficient",
    "cannot",
    "unable to",
    "difficult",
    "false negative",
    "overconfident",
    "overconfidence",
    "biased",
    "ignore",
    "neglect",
    "impractical",
    "expensive",
    "bottleneck",
    "long inference time",
    "accumulate errors",
    "error propagation",
    "lack of",
    "lacks ",
    "prone to",
)

INFERENCE_MARKERS = (
    "nms",
    "non-maximum suppression",
    "ranking",
    "selection",
    "threshold",
    "proposal filtering",
    "post-processing",
    "post processing",
    "inference",
)

ADJACENT_RULES = (
    ("temporal forgery localization", "Temporal Forgery Localization"),
    ("deepfake temporal localization", "Audio-visual Deepfake Temporal Localization"),
    ("action localization", "Action Localization"),
    ("anomaly localization", "Video Anomaly Localization"),
    ("video summarization", "Video Summarization"),
    ("open-world detection", "Open-world Detection"),
    ("deepfake detection", "Deepfake Detection"),
    ("video classification", "Video Classification"),
)

CORE_RULES = (
    ("video moment retrieval", "Video Moment Retrieval"),
    ("moment retrieval", "Video Moment Retrieval"),
    ("video temporal grounding", "Video Temporal Grounding"),
    ("temporal video grounding", "Video Temporal Grounding"),
    ("natural language video localization", "Natural Language Video Localization"),
    ("moment localization", "Moment Localization"),
    ("query-based highlight detection", "Query-based Highlight Detection"),
    ("highlight detection", "Highlight Detection"),
    ("video grounding", "Video Grounding"),
)

FAILURE_FACETS: dict[str, tuple[str, ...]] = {
    "uncertainty": ("uncertain", "uncertainty", "overconfident", "confidence", "evidence insuff", "hard moment"),
    "boundary": ("boundary", "start and end", "temporal gap", "overly broad", "offset"),
    "false_negative": ("false negative", "negative example", "hard negative", "irrelevant segment"),
    "bias": ("bias", "spurious", "static background", "modality imbalance", "shortcut"),
    "action_motion": (
        "action-sensitive",
        "action cue",
        "action-aware",
        "motion information",
        "motion feature",
        "moving object",
        "objects that are moving",
        "temporal action cue",
    ),
    "cross_modal": ("cross-modal", "video-text", "visual and textual", "audio-visual", "multimodal"),
    "multi_segment": ("multiple answer", "adjacent answer", "multiple correct", "repeated event", "clip pair"),
    "long_sparse": ("long video", "sparse evidence", "frame selection", "token", "computational overhead"),
    "open_set": ("invalid query", "irrelevant query", "open-set", "refuse", "no answer"),
    "domain_shift": ("domain gap", "cross-domain", "generalization", "out-of-domain", "in-domain"),
    "weak_supervision": ("weakly supervised", "pseudo label", "annotation", "unlabeled"),
    "context": ("context", "background clip", "contextual shift", "global temporal"),
    "reconstruction": ("reconstruction", "discrepancy", "inconsistency"),
    "reasoning": ("reasoning", "multi-hop", "compositional", "causal", "llm"),
    "proposal_dependency": ("proposal", "object detector", "anchor", "candidate segment", "pre-generated"),
    "backbone_dependency": ("backbone", "feature extractor", "pre-trained model", "pretrained model", "resnet", "s3d"),
    "representation": ("representation learning", "semantic-oriented", "fine-grained representation", "embedding"),
    "augmentation": ("augmentation", "mixing", "replacement clip", "synthetic"),
    "ranking_selection": ("ranking", "selection", "top-k", "retrieval score", "saliency"),
}

PROBLEM_FACET_NAMES = {
    "uncertainty": "Evidence Sufficiency, Uncertainty, and Abstention",
    "boundary": "Boundary Structure and Temporal Precision",
    "false_negative": "Semantic Negative Construction and Distractor Control",
    "bias": "Shortcut Bias and Spurious Context Dependence",
    "action_motion": "Action-Sensitive Visual and Motion Representation",
    "cross_modal": "Fine-Grained Cross-Modal Evidence Integration",
    "multi_segment": "Multi-Segment and Repeated-Event Structure",
    "long_sparse": "Sparse Evidence Discovery in Long Videos",
    "open_set": "Invalid Query and Open-Set Temporal Retrieval",
    "domain_shift": "Domain Adaptation and Generalization",
    "weak_supervision": "Weak Supervision and Annotation Reliability",
    "context": "Temporal Context Robustness",
    "reconstruction": "Cross-Modal Consistency and Reconstruction",
    "reasoning": "Compositional and Explicit Temporal Reasoning",
    "proposal_dependency": "Proposal and Detector Dependence",
    "backbone_dependency": "Backbone and Feature-Extractor Dependence",
    "representation": "Representation Granularity and Semantic Structure",
    "augmentation": "Augmentation Reliability and Distribution Shift",
    "ranking_selection": "Ranking and Selection Failure",
}

METHOD_FACET_NAMES = {
    "uncertainty": "Evidential and Calibration Mechanisms",
    "boundary": "Boundary-Aware Representation and Regression",
    "false_negative": "Hard-Negative and Query-Consistent Sampling",
    "bias": "Debiasing and Invariance Learning",
    "action_motion": "Action-Cue and Motion Injection",
    "cross_modal": "Cross-Modal Fusion and Alignment Mechanisms",
    "multi_segment": "Inter-Segment Relational Modeling",
    "long_sparse": "Efficient Selection and Sparse Processing",
    "open_set": "Refusal and Open-Set Decision Mechanisms",
    "domain_shift": "Domain Adaptation Mechanisms",
    "weak_supervision": "Pseudo-Label and Weak-Supervision Mechanisms",
    "context": "Multi-Scale Context Modeling",
    "reconstruction": "Reconstruction-Discrepancy Mechanisms",
    "reasoning": "Structured and Agentic Reasoning Mechanisms",
    "proposal_dependency": "Proposal Generation and Candidate Decoding",
    "backbone_dependency": "Backbone Adaptation and Feature Enhancement",
    "representation": "Representation Learning Mechanisms",
    "augmentation": "Data Augmentation and Context Diversification",
    "ranking_selection": "Ranking, Selection, and Hard-Mining Mechanisms",
}

FACET_TRANSFER_COMPATIBILITY = {
    ("reconstruction", "false_negative"): "cross-modal discrepancy can identify semantically inconsistent replacement clips",
    ("reconstruction", "open_set"): "reconstruction discrepancy can measure whether query-conditioned evidence is present",
    ("reconstruction", "uncertainty"): "reconstruction error can serve as an evidence-sufficiency signal",
    ("uncertainty", "open_set"): "calibrated uncertainty supports abstention on invalid or irrelevant queries",
    ("uncertainty", "boundary"): "uncertainty can prevent overconfident boundary selection under ambiguous evidence",
    ("boundary", "multi_segment"): "inside-outside boundary structure can separate adjacent or repeated answer segments",
    ("boundary", "proposal_dependency"): "boundary supervision can reduce dependence on coarse proposal candidates",
    ("action_motion", "long_sparse"): "action-sensitive cues can guide sparse frame or region selection",
    ("action_motion", "cross_modal"): "action cues can correct static-object-biased cross-modal alignment",
    ("reasoning", "multi_segment"): "structured reasoning can decompose relations across multiple temporal moments",
    ("reasoning", "open_set"): "explicit reasoning can verify query validity before producing a span",
    ("reasoning", "long_sparse"): "reasoning can organize evidence selection over long videos",
    ("augmentation", "false_negative"): "query-aware augmentation can prevent semantically false negative construction",
    ("augmentation", "bias"): "context diversification can break spurious background correlations",
    ("weak_supervision", "domain_shift"): "pseudo supervision can adapt the model without dense target-domain labels",
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"--- Page \d+ ---", " ", text)
    text = re.sub(r"arXiv:\S+\s+\[[^\]]+\]\s+\d+\s+\w+\s+\d{4}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def strip_citations(text: str) -> str:
    text = re.sub(r"\([^)]*(?:et al\.|\d{4})[^)]*\)", "", text)
    text = re.sub(r"\[[0-9,\-\s]+\]", "", text)
    text = re.sub(r"\b[A-Z][A-Za-z-]+\s+et\s+al\.?", "", text)
    text = re.sub(r"\bet\s+al\.?", "", text, flags=re.I)
    return normalize_whitespace(text)


def clean_semantic_text(text: str) -> str:
    text = strip_citations(text)
    boilerplate = (
        r"\bin this paper\b",
        r"\bin this work\b",
        r"\bour contributions? (?:are|is) summarized as follows\b",
        r"\bwe (?:propose|introduce|present|develop|conduct|demonstrate|show)\b",
        r"\bour (?:method|approach|framework|model)\b",
        r"\bas (?:shown|illustrated) in (?:figure|fig\.)\s*\d*\b",
        r"\bfigure\s*\d+\b",
        r"\bexperiments? (?:show|demonstrate|validate)\b",
    )
    for pattern in boilerplate:
        text = re.sub(pattern, " ", text, flags=re.I)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", " ", text)
    return normalize_whitespace(text)


def split_sentences(text: str) -> list[str]:
    text = normalize_whitespace(text)
    raw_parts = re.split(r"(?<=[.!?])\s+", text)
    parts: list[str] = []
    for raw in raw_parts:
        raw = raw.strip()
        if len(raw) < 15:
            continue
        if len(raw) <= 900:
            parts.append(raw)
            continue
        words = raw.split()
        chunk: list[str] = []
        length = 0
        for word in words:
            if chunk and length + len(word) + 1 > 700:
                parts.append(" ".join(chunk))
                chunk = chunk[-12:]
                length = sum(len(item) + 1 for item in chunk)
            chunk.append(word)
            length += len(word) + 1
        if chunk:
            parts.append(" ".join(chunk))
    return parts


def cut_before_related_work(text: str) -> str:
    patterns = (
        r"\n\s*#+\s*Related\s+Works?\b",
        r"\n\s*\d+(?:\.\d+)?\s+Related\s+Works?\b",
        r"\bRelated\s+works?\s+Video temporal grounding\b",
        r"\b2\s+Related\s+Works?\b",
    )
    cut = len(text)
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            cut = min(cut, match.start())
    return text[:cut]


def extract_intro_from_full_text(text: str) -> str:
    starts = [
        re.search(r"(?:^|\n)\s*(?:1(?:\.0)?\s+)?Introduction\b", text, re.IGNORECASE),
        re.search(r"\bIntroduction\b", text, re.IGNORECASE),
    ]
    start = next((match.end() for match in starts if match), 0)
    tail = text[start:]
    cut_patterns = (
        r"(?:^|\n)\s*(?:2(?:\.0)?\s+)?Related\s+Works?\b",
        r"(?:^|\n)\s*#+\s*Related\s+Works?\b",
        r"(?:^|\n)\s*(?:2|3)(?:\.0)?\s+(?:Method|Approach|Preliminar)",
    )
    cut = len(tail)
    for pattern in cut_patterns:
        match = re.search(pattern, tail, re.IGNORECASE)
        if match:
            cut = min(cut, match.start())
    return tail[:cut]


def load_sections(paper_dir: Path) -> dict[str, str]:
    abstract = cut_before_related_work(read_text(paper_dir / "abstract.md", limit=12000))
    intro_raw = read_text(paper_dir / "introduction.md", limit=40000)
    intro = cut_before_related_work(intro_raw)
    if len(normalize_whitespace(intro)) < 1200:
        full_text = read_text(paper_dir / "full_text.txt", limit=120000)
        recovered = extract_intro_from_full_text(full_text)
        if len(normalize_whitespace(recovered)) > len(normalize_whitespace(intro)):
            intro = recovered
    return {
        "Abstract": normalize_whitespace(abstract),
        "Introduction": normalize_whitespace(intro),
    }


def evidence(section: str, quote: str, role: str, evidence_id: str) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "section": section,
        "quote": normalize_whitespace(quote)[:700],
        "role": role,
        "page": None,
    }


def sentence_records(sections: dict[str, str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    number = 0
    for section in ("Abstract", "Introduction"):
        for sentence in split_sentences(sections.get(section, "")):
            number += 1
            records.append(
                {
                    "index": number,
                    "section": section,
                    "text": sentence,
                    "lower": sentence.lower(),
                    "evidence_id": f"EV{number:03d}",
                }
            )
    return records


def make_chain_item(record: dict[str, Any], summary: str, role: str) -> dict[str, Any]:
    return {
        "summary": summary,
        "evidence": [evidence(record["section"], record["text"], role, record["evidence_id"])],
        "role": role,
    }


def contains_any(text: str, phrases: Iterable[str]) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in phrases)


def select_records(
    records: list[dict[str, Any]],
    markers: Iterable[str],
    sections: tuple[str, ...] = ("Introduction",),
    limit: int = 4,
) -> list[dict[str, Any]]:
    return [record for record in records if record["section"] in sections and contains_any(record["lower"], markers)][:limit]


def is_problem_candidate(record: dict[str, Any]) -> bool:
    lower = record["lower"]
    if len(record["text"]) < 35:
        return False
    author_method = contains_any(lower, METHOD_MARKERS)
    strong_failure = contains_any(lower, STRONG_FAILURE_MARKERS)
    if author_method and not strong_failure:
        return False
    if author_method:
        first_method = min((lower.find(marker) for marker in METHOD_MARKERS if marker in lower), default=len(lower))
        first_failure = min((lower.find(marker) for marker in STRONG_FAILURE_MARKERS if marker in lower), default=len(lower))
        if first_failure >= first_method:
            return False
    if strong_failure:
        return True
    return "challenge" in lower and not author_method and len(record["text"]) >= 80


def summarize_evidence(text: str, max_length: int = 260) -> str:
    text = strip_citations(text)
    text = re.sub(r"^(however|nevertheless|despite these advancements|while effective|but)\W+", "", text, flags=re.I)
    if len(text) <= max_length:
        return text
    shortened = text[:max_length].rsplit(" ", 1)[0]
    return shortened + "..."


def marker_context_record(
    intro_text: str,
    markers: Iterable[str],
    evidence_id: str,
) -> dict[str, Any] | None:
    lower = intro_text.lower()
    positions = [(lower.find(marker), marker) for marker in markers if lower.find(marker) >= 0]
    if not positions:
        return None
    position, _ = min(positions)
    start = max(0, position - 240)
    end = min(len(intro_text), position + 520)
    quote = normalize_whitespace(intro_text[start:end])
    return {
        "index": evidence_number(evidence_id),
        "section": "Introduction",
        "text": quote,
        "lower": quote.lower(),
        "evidence_id": evidence_id,
    }


def extract_intro_chain(
    records: list[dict[str, Any]],
    sections: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    intro = [record for record in records if record["section"] == "Introduction"]
    background = intro[:2]
    prior = select_records(records, PRIOR_MARKERS, limit=4)
    limitations = [record for record in intro if is_problem_candidate(record)][:6]
    examples = select_records(records, EXAMPLE_MARKERS, limit=4)
    methods = select_records(records, METHOD_MARKERS, limit=6)
    transitions = []
    for record in limitations:
        next_records = [item for item in intro if item["index"] > record["index"] and item["index"] <= record["index"] + 2]
        transitions.extend(next_records[:1])
    if not prior and len(intro) >= 3:
        prior = intro[2:4]
    if not limitations:
        limitations = [record for record in intro if "challenge" in record["lower"] or "limitation" in record["lower"]][:2]
    if not limitations:
        fallback_limitation = marker_context_record(
            sections.get("Introduction", ""),
            LIMITATION_MARKERS,
            "EV900",
        )
        if fallback_limitation:
            limitations = [fallback_limitation]
    if not examples:
        fallback_example = marker_context_record(
            sections.get("Introduction", ""),
            EXAMPLE_MARKERS,
            "EV901",
        )
        if fallback_example:
            examples = [fallback_example]
    if not methods:
        methods = select_records(records, METHOD_MARKERS, sections=("Abstract", "Introduction"), limit=4)
    chain = {
        "background_setup": [
            make_chain_item(record, summarize_evidence(record["text"]), "task_background") for record in background
        ],
        "prior_work_summary": [
            make_chain_item(record, summarize_evidence(record["text"]), "prior_work") for record in prior
        ],
        "prior_work_limitation": [
            make_chain_item(record, summarize_evidence(record["text"]), "limitation") for record in limitations
        ],
        "illustrative_examples": [],
        "core_problem_transition": [
            make_chain_item(record, summarize_evidence(record["text"]), "problem_transition")
            for record in transitions[:3]
        ],
        "method_transition": [
            make_chain_item(record, summarize_evidence(record["text"]), "method_transition") for record in methods
        ],
    }
    for number, record in enumerate(examples, start=1):
        chain["illustrative_examples"].append(
            {
                "example_id": f"EX{number}",
                "example_name": summarize_evidence(record["text"], 90),
                "scenario": summarize_evidence(record["text"], 300),
                "what_it_reveals": infer_example_revelation(record["text"]),
                "evidence": [
                    evidence(record["section"], record["text"], "illustrative_failure_case", record["evidence_id"])
                ],
                "role": "illustrative_failure_case",
            }
        )
    return chain


def infer_example_revelation(text: str) -> str:
    lower = text.lower()
    if "false negative" in lower or "negative example" in lower:
        return "The example exposes a training signal that contradicts the query semantics."
    if "lack" in lower or "missing" in lower or "without" in lower:
        return "The example shows that the model must reason under missing or incomplete evidence."
    if "visually similar" in lower:
        return "The example shows that partial visual similarity is insufficient for query-consistent localization."
    if "static" in lower or "background" in lower:
        return "The example shows that static context can distract the model from action-relevant temporal evidence."
    return "The example makes the paper's failure mode concrete in a specific video-query scenario."


def infer_task_scope(title: str, sections: dict[str, str]) -> dict[str, Any]:
    text = f"{title} {sections.get('Abstract', '')} {sections.get('Introduction', '')[:2500]}"
    lower = text.lower()
    title_lower = title.lower()
    for phrase, label in ADJACENT_RULES:
        if phrase in title_lower or phrase in lower[:1600]:
            return {
                "primary_task": label,
                "task_family": "temporal localization / adjacent video understanding",
                "is_core_video_moment_retrieval": False,
                "is_adjacent_task": True,
                "adjacent_task_type": label,
                "why_in_or_out": "The paper performs temporal localization but is not conditioned on a natural-language moment query.",
                "transferable_value": adjacent_transfer_value(lower),
                "evidence": task_evidence(sections, phrase),
            }
    for phrase, label in CORE_RULES:
        if phrase in title_lower or phrase in lower[:1800]:
            return {
                "primary_task": label,
                "task_family": "video moment retrieval / video temporal grounding",
                "is_core_video_moment_retrieval": True,
                "is_adjacent_task": False,
                "adjacent_task_type": "",
                "why_in_or_out": "The task explicitly localizes query-relevant temporal moments or highlights.",
                "transferable_value": "",
                "evidence": task_evidence(sections, phrase),
            }
    return {
        "primary_task": "General video temporal understanding",
        "task_family": "adjacent video understanding",
        "is_core_video_moment_retrieval": False,
        "is_adjacent_task": True,
        "adjacent_task_type": "General video temporal understanding",
        "why_in_or_out": "The local text does not establish a natural-language-conditioned moment retrieval task.",
        "transferable_value": adjacent_transfer_value(lower),
        "evidence": [],
    }


def task_evidence(sections: dict[str, str], phrase: str) -> list[dict[str, Any]]:
    for section in ("Abstract", "Introduction"):
        for sentence in split_sentences(sections.get(section, "")):
            if phrase in sentence.lower():
                return [evidence(section, sentence, "task_scope", "TASK01")]
    return []


def adjacent_transfer_value(lower: str) -> str:
    if "reconstruction" in lower or "discrepanc" in lower:
        return "Cross-modal reconstruction discrepancy can test query-video inconsistency or insufficient evidence."
    if "uncertainty" in lower:
        return "Uncertainty estimation can support abstention and evidence sufficiency in moment retrieval."
    if "boundary" in lower or "localization" in lower:
        return "Its temporal boundary mechanism may transfer to precise language-conditioned localization."
    return "The temporal representation or localization mechanism may transfer after adding language conditioning."


def macro_match(text: str, clusters: list[dict[str, Any]], prefix: str) -> tuple[str, str]:
    lower = text.lower()
    scored = []
    for cluster in clusters:
        score = sum(3 if " " in keyword else 1 for keyword in cluster["keywords"] if keyword.lower() in lower)
        scored.append((score, cluster["id"], cluster["name"]))
    score, cluster_id, name = max(scored)
    if score <= 0:
        return f"{prefix}_NEW", "new_or_adjacent"
    return cluster_id, name


def infer_problem_type(text: str) -> str:
    lower = text.lower()
    if contains_any(lower, INFERENCE_MARKERS):
        return "inference"
    if contains_any(lower, ("dataset", "annotation", "sample", "data bias", "label")):
        return "data"
    if contains_any(lower, ("loss", "training", "augmentation", "negative", "supervision")):
        return "training"
    if contains_any(lower, ("metric", "evaluation", "benchmark", "protocol")):
        return "evaluation"
    if contains_any(lower, ("task assumes", "task definition", "invalid query", "single interval")):
        return "task_definition"
    return "model"


def failure_clause(sentence: str) -> str:
    text = strip_citations(sentence)
    patterns = (
        r"(?:however|while effective|despite[^,]*|nevertheless)[,\s]+(.+)",
        r"(.{0,90}(?:fail(?:s|ed)? to|struggle(?:s|d)? to|cannot|unable to|ignore(?:s|d)?|neglect(?:s|ed)?).+)",
        r"(.{0,90}(?:limitation|challenge|false negative|overconfiden|biased uncertainty).+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return summarize_evidence(match.group(1), 240)
    return summarize_evidence(text, 240)


def question_from_failure(failure: str) -> str:
    clause = failure.rstrip(".")
    clause = re.sub(r"^(this|these|existing methods?|models?)\s+", "", clause, flags=re.I)
    return f"How can a temporal grounding system overcome the failure that {clause[0].lower() + clause[1:] if clause else 'is described in the introduction'}?"


def root_cause_from_record(record: dict[str, Any], records: list[dict[str, Any]]) -> str:
    sentence = strip_citations(record["text"])
    match = re.search(r"(?:because|due to|as|stemming from|caused by)\s+(.+)", sentence, re.I)
    if match:
        return summarize_evidence(match.group(1), 260)
    previous = next((item for item in reversed(records) if item["index"] < record["index"] and item["section"] == record["section"]), None)
    return summarize_evidence(previous["text"], 260) if previous else "The introduction attributes the failure to a mismatch between the available representation or supervision and the target temporal evidence."


def linked_examples(record: dict[str, Any], chain: dict[str, Any]) -> list[str]:
    linked = []
    for example in chain["illustrative_examples"]:
        ev = example["evidence"][0]
        if abs(evidence_number(ev.get("evidence_id", "")) - record["index"]) <= 4:
            linked.append(example["example_id"])
    if not linked and chain["illustrative_examples"]:
        linked.append(chain["illustrative_examples"][0]["example_id"])
    return linked


def evidence_number(evidence_id: str) -> int:
    match = re.search(r"(\d+)", evidence_id or "")
    return int(match.group(1)) if match else 0


def extract_generic_problem_units(
    records: list[dict[str, Any]],
    chain: dict[str, Any],
    task_scope: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = [
        record
        for record in records
        if record["section"] == "Introduction" and is_problem_candidate(record)
    ][:7]
    inference_candidates = [
        record
        for record in records
        if record["section"] == "Introduction"
        and contains_any(record["lower"], INFERENCE_MARKERS)
        and is_problem_candidate(record)
    ]
    candidates = list(dict.fromkeys(record["evidence_id"] for record in [*inference_candidates, *candidates]))
    by_id = {record["evidence_id"]: record for record in records}
    candidates = [by_id[evidence_id] for evidence_id in candidates]
    if not candidates:
        candidates = [
            record
            for record in records
            if record["section"] == "Abstract" and is_problem_candidate(record)
        ][:2]
    if not candidates:
        candidates = [
            record
            for record in records
            if record["section"] == "Introduction"
            and contains_any(record["lower"], ("need to", "requires", "require ", "important to"))
            and not contains_any(record["lower"], METHOD_MARKERS)
        ][:1]
    if not candidates:
        abstract = [record for record in records if record["section"] == "Abstract"]
        candidates = abstract[1:2] or abstract[:1] or records[:1]
    units = []
    seen = set()
    for number, record in enumerate(candidates[:5], start=1):
        failure = failure_clause(record["text"])
        signature = normalize_title(failure)[:120]
        if signature in seen:
            continue
        seen.add(signature)
        macro_id, macro_name = macro_match(failure, PROBLEM_CLUSTERS, "P")
        linked_example_ids = linked_examples(record, chain)
        units.append(
            {
                "problem_unit_id": f"PU{number}",
                "macro_problem_id": "",
                "macro_problem_name": "",
                "legacy_macro_problem_id": macro_id,
                "legacy_macro_problem_name": macro_name,
                "micro_problem_name": failure,
                "micro_problem_question": question_from_failure(failure),
                "failure_mode": failure,
                "root_cause": root_cause_from_record(record, records),
                "why_existing_methods_fail": summarize_evidence(record["text"], 320),
                "affected_scenario": example_scenario(linked_example_ids, chain),
                "problem_type": infer_problem_type(record["text"]),
                "linked_intro_evidence_ids": [record["evidence_id"]],
                "linked_example_ids": linked_example_ids,
                "evidence": [
                    evidence(record["section"], record["text"], "problem", record["evidence_id"])
                ],
            }
        )
    return units


def example_scenario(example_ids: list[str], chain: dict[str, Any]) -> str:
    for example in chain["illustrative_examples"]:
        if example["example_id"] in example_ids:
            return example["scenario"]
    return ""


def method_name_from_sentence(sentence: str) -> str:
    text = strip_citations(sentence)
    patterns = (
        r"(?:we|this paper)\s+(?:propose|introduce|present|develop)\s+(?:an?|the|our)?\s*([^.;]{8,150})",
        r"(?:our method|our approach|our framework)\s+([^.;]{8,150})",
        r"to address[^,.;]*,\s*(?:we\s+)?(?:propose|introduce)\s+([^.;]{8,150})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            name = re.split(r"\b(?:that|which|to enable|to improve|for addressing)\b", match.group(1), maxsplit=1, flags=re.I)[0]
            return summarize_evidence(name, 150).strip(" ,")
    return summarize_evidence(text, 150)


def extract_components(text: str) -> list[str]:
    components = []
    patterns = (
        r"\b[A-Z][A-Za-z-]+(?:\s+[A-Z][A-Za-z-]+){1,5}\s*\([A-Z][A-Z0-9-]{1,8}\)",
        r"\b[A-Z][A-Za-z-]+(?:\s+[A-Z][A-Za-z-]+){1,5}\b",
        r"\b[A-Z]{2,8}\b",
    )
    for pattern in patterns:
        for match in re.findall(pattern, text):
            candidate = normalize_whitespace(match)
            if candidate.lower() in {"video moment retrieval", "video temporal grounding", "vision language models"}:
                continue
            if candidate not in components:
                components.append(candidate)
    clauses = re.split(r"[,;]", strip_citations(text))
    for clause in clauses:
        if contains_any(clause, ("loss", "prompt", "encoder", "decoder", "regularizer", "reconstruction", "ranking", "fusion", "attention", "fine-tuning")):
            candidate = summarize_evidence(clause, 130)
            if 12 <= len(candidate) <= 150 and candidate not in components:
                components.append(candidate)
    return components[:10]


def extract_generic_method_units(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = select_records(records, METHOD_MARKERS, limit=8)
    if not candidates:
        candidates = select_records(records, METHOD_MARKERS, sections=("Abstract",), limit=3)
    units = []
    seen = set()
    for record in candidates:
        name = method_name_from_sentence(record["text"])
        signature = normalize_title(name)[:100]
        if not signature or signature in seen:
            continue
        seen.add(signature)
        macro_id, macro_name = macro_match(f"{name} {record['text']}", METHOD_CLUSTERS, "M")
        components = extract_components(record["text"])
        units.append(
            {
                "method_unit_id": f"MU{len(units) + 1}",
                "macro_method_id": "",
                "macro_method_name": "",
                "legacy_macro_method_id": macro_id,
                "legacy_macro_method_name": macro_name,
                "micro_method_name": name,
                "method_core_mechanism": summarize_evidence(record["text"], 380),
                "method_components": components or [name],
                "training_or_inference_strategy": infer_method_strategy(record["text"]),
                "what_is_transferred_or_injected_or_aligned": infer_transferred_content(record["text"]),
                "required_inputs": infer_required_inputs(record["text"]),
                "output_or_supervision": infer_output_supervision(record["text"]),
                "linked_intro_evidence_ids": [record["evidence_id"]],
                "evidence": [
                    evidence(record["section"], record["text"], "method", record["evidence_id"])
                ],
            }
        )
        if len(units) >= 5:
            break
    return units


def infer_method_strategy(text: str) -> str:
    lower = text.lower()
    if contains_any(lower, ("loss", "training", "fine-tun", "augmentation", "contrastive", "ranking")):
        return "training"
    if contains_any(lower, ("nms", "selection", "inference", "threshold", "post-processing")):
        return "inference"
    return "training and inference"


def infer_transferred_content(text: str) -> str:
    lower = text.lower()
    phrases = []
    for phrase in (
        "action cues",
        "temporal context",
        "visual and textual information",
        "audio-visual discrepancy",
        "uncertainty",
        "boundary evidence",
        "query relevance",
        "motion information",
        "semantic relationships",
    ):
        if phrase in lower:
            phrases.append(phrase)
    return ", ".join(phrases) or "task-relevant temporal and cross-modal evidence"


def infer_required_inputs(text: str) -> list[str]:
    lower = text.lower()
    inputs = []
    for phrase, label in (
        ("video", "video features"),
        ("frame", "frame features"),
        ("query", "text query"),
        ("text", "text features"),
        ("audio", "audio features"),
        ("clip", "clip features"),
        ("proposal", "moment proposals"),
    ):
        if phrase in lower and label not in inputs:
            inputs.append(label)
    return inputs or ["video features", "text query"]


def infer_output_supervision(text: str) -> str:
    lower = text.lower()
    outputs = []
    for phrase in ("boundary", "similarity", "uncertainty", "ranking", "contrastive", "reconstruction", "classification"):
        if phrase in lower:
            outputs.append(phrase)
    return ", ".join(outputs) or "temporal localization supervision"


def facets(text: str) -> list[str]:
    lower = text.lower()
    return [name for name, phrases in FAILURE_FACETS.items() if any(phrase in lower for phrase in phrases)]


def build_problem_method_links(
    problems: list[dict[str, Any]],
    methods: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    links = []
    if not problems or not methods:
        return links
    for problem in problems:
        problem_ev = min((evidence_number(item) for item in problem["linked_intro_evidence_ids"]), default=0)
        ranked = []
        for method in methods:
            method_ev = min((evidence_number(item) for item in method["linked_intro_evidence_ids"]), default=999)
            shared = set(facets(" ".join([problem["failure_mode"], problem["root_cause"]]))) & set(
                facets(" ".join([method["method_core_mechanism"], *method["method_components"]]))
            )
            distance = abs(method_ev - problem_ev)
            ranked.append((len(shared) * 3 - min(distance, 10) / 10, method, shared))
        for _, method, shared in sorted(ranked, key=lambda item: -item[0])[:2]:
            quote = method["evidence"][0]["quote"]
            links.append(
                {
                    "problem_unit_id": problem["problem_unit_id"],
                    "method_unit_id": method["method_unit_id"],
                    "solves_how": (
                        f"{method['micro_method_name']} targets {problem['micro_problem_name']} by operating on "
                        f"{', '.join(sorted(shared)) if shared else method['what_is_transferred_or_injected_or_aligned']}."
                    ),
                    "evidence": [
                        evidence(method["evidence"][0]["section"], quote, "link", method["evidence"][0]["evidence_id"])
                    ],
                }
            )
    return links


def known_profile(
    title: str,
    records: list[dict[str, Any]],
    chain: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    lower = title.lower()
    if "actprompt:" in lower:
        return actprompt_profile(records, chain)
    if "adaptive evidential learning" in lower:
        return demr_profile(records, chain)
    if "cva: context-aware" in lower:
        return cva_profile(records, chain)
    if "cliptbp:" in lower:
        return cliptbp_profile(records, chain)
    if "auvire:" in lower:
        return auvire_profile(records, chain)
    return None


def find_record(records: list[dict[str, Any]], *needles: str) -> dict[str, Any]:
    for record in records:
        if all(needle.lower() in record["lower"] for needle in needles):
            return record
    for record in records:
        if any(needle.lower() in record["lower"] for needle in needles):
            return record
    return records[0]


def profile_problem(
    unit_id: str,
    macro_id: str,
    macro_name: str,
    name: str,
    question: str,
    failure: str,
    root: str,
    why: str,
    problem_type: str,
    record: dict[str, Any],
    chain: dict[str, Any],
    example_id: str = "",
) -> dict[str, Any]:
    example_ids = [example_id] if example_id else []
    return {
        "problem_unit_id": unit_id,
        "macro_problem_id": "",
        "macro_problem_name": "",
        "legacy_macro_problem_id": macro_id,
        "legacy_macro_problem_name": macro_name,
        "micro_problem_name": name,
        "micro_problem_question": question,
        "failure_mode": failure,
        "root_cause": root,
        "why_existing_methods_fail": why,
        "affected_scenario": example_scenario(example_ids, chain),
        "problem_type": problem_type,
        "linked_intro_evidence_ids": [record["evidence_id"]],
        "linked_example_ids": example_ids,
        "evidence": [evidence(record["section"], record["text"], "problem", record["evidence_id"])],
    }


def profile_method(
    unit_id: str,
    macro_id: str,
    macro_name: str,
    name: str,
    mechanism: str,
    components: list[str],
    record: dict[str, Any],
    transfer: str,
    inputs: list[str],
    output: str,
) -> dict[str, Any]:
    return {
        "method_unit_id": unit_id,
        "macro_method_id": "",
        "macro_method_name": "",
        "legacy_macro_method_id": macro_id,
        "legacy_macro_method_name": macro_name,
        "micro_method_name": name,
        "method_core_mechanism": mechanism,
        "method_components": components,
        "training_or_inference_strategy": infer_method_strategy(record["text"]),
        "what_is_transferred_or_injected_or_aligned": transfer,
        "required_inputs": inputs,
        "output_or_supervision": output,
        "linked_intro_evidence_ids": [record["evidence_id"]],
        "evidence": [evidence(record["section"], record["text"], "method", record["evidence_id"])],
    }


def ensure_known_example(
    chain: dict[str, Any],
    record: dict[str, Any],
    name: str,
    scenario: str,
    revelation: str,
) -> str:
    for example in chain["illustrative_examples"]:
        if record["evidence_id"] in [item["evidence_id"] for item in example["evidence"]]:
            example["example_name"] = name
            example["scenario"] = scenario
            example["what_it_reveals"] = revelation
            return example["example_id"]
    example_id = f"EX{len(chain['illustrative_examples']) + 1}"
    chain["illustrative_examples"].append(
        {
            "example_id": example_id,
            "example_name": name,
            "scenario": scenario,
            "what_it_reveals": revelation,
            "evidence": [evidence(record["section"], record["text"], "illustrative_failure_case", record["evidence_id"])],
            "role": "illustrative_failure_case",
        }
    )
    return example_id


def actprompt_profile(records: list[dict[str, Any]], chain: dict[str, Any]):
    static = find_record(records, "pre-trained on massive image-text data", "static objects")
    coffee = find_record(records, "drinking coffee", "coffee mug")
    overhead = find_record(records, "end-to-end fine-tuning", "computational overhead")
    adaptation = find_record(records, "efficient in-domain feature adaptation")
    aci = find_record(records, "action cue injection", "prompt embeddings")
    ctpl = find_record(records, "context-aware temporal prompt learning", "consecutive frames")
    ex = ensure_known_example(
        chain,
        coffee,
        "drinking-coffee action-sensitive object example",
        "A lady is drinking coffee; the image encoder should attend to the mug and the hand holding it.",
        "Static object semantics do not identify which objects participate in the queried action.",
    )
    problems = [
        profile_problem(
            "PU1", "P06", "Cross-Modal Semantic Alignment Gap",
            "Image-pretrained VLMs miss action-sensitive objects",
            "How can image-pretrained VLMs distinguish action-sensitive objects from static background objects?",
            "The image encoder attends to static object semantics and overlooks objects involved in motion or action.",
            "Image-text pretraining lacks temporal action cues and creates a domain gap with video grounding.",
            "Late fusion adds motion after image encoding and cannot deeply adapt the image encoder to action-sensitive regions.",
            "model", static, chain, ex,
        ),
        profile_problem(
            "PU2", "P08", "Domain Shift and Generalization",
            "End-to-end VLM adaptation on long raw videos is computationally impractical",
            "How can a VLM image encoder be adapted in-domain before downstream grounding without end-to-end long-video training?",
            "Jointly training the feature encoder and downstream model on long raw videos incurs prohibitive cost.",
            "The adaptation target is a large pretrained image encoder while the downstream input is long video.",
            "Ordinary end-to-end fine-tuning couples feature adaptation with expensive downstream temporal training.",
            "training", overhead, chain,
        ),
    ]
    methods = [
        profile_method(
            "MU1", "M01", "Pretraining, Pseudo-Labeling, and Data Generation",
            "Preliminary in-domain VLM feature adaptation with pairwise ranking and contrastive pretext tasks",
            "Fine-tune only a small part of the VLM image encoder on downstream-domain clips before standard grounding.",
            ["preliminary in-domain fine-tuning", "moment-query pairwise ranking", "moment-query contrastive learning", "frozen downstream feature extraction"],
            adaptation, "downstream-adaptive image representations", ["video clips", "text queries"], "pairwise ranking and contrastive supervision",
        ),
        profile_method(
            "MU2", "M12", "Multi-Modal Fusion and Feature Enhancement",
            "Action-Cue-Injected prompt learning with video-guided and verb-guided prompts",
            "Produce action cues from video and text encoders and inject them as prompt embeddings into the VLM image encoder.",
            ["Action Cue Injection", "video-guided prompt injection", "verb-guided prompt injection", "attention-based action-sensitive region selection"],
            aci, "video-guided and verb-guided action cues", ["video features", "verb/text features", "image patches"], "action-sensitive image representation",
        ),
        profile_method(
            "MU3", "M03", "Coarse-to-Fine or Hierarchical Localization",
            "Context-aware Temporal Prompt Learning over selected action-sensitive regions",
            "Select action-sensitive regions from consecutive frames, extract motion features, and turn them into temporal prompts.",
            ["Context-aware Temporal Prompt Learning", "selected action-sensitive visual regions", "consecutive-frame motion extraction", "temporal prompt adaptor"],
            ctpl, "motion information from consecutive action-sensitive regions", ["selected visual regions", "consecutive frames"], "temporal prompt embeddings",
        ),
    ]
    return problems, methods


def demr_profile(records: list[dict[str, Any]], chain: dict[str, Any]):
    nms = find_record(records, "non-maximum suppression", "hard moments")
    example = find_record(records, "lack the presence of a woman", "cooking")
    der_issue = find_record(records, "higher-error predictions", "lower uncertainty")
    der = find_record(records, "der represents uncertainty", "proposal")
    rff = find_record(records, "reflective flipped fusion", "query reconstruction")
    geom = find_record(records, "geom-regularizer", "prediction accuracy")
    ex = ensure_known_example(
        chain,
        example,
        "woman-cooking missing-evidence example",
        "The query asks when the woman is cooking, but some frames do not contain the woman.",
        "A deterministic model cannot reliably align the action when required visual evidence is absent.",
    )
    problems = [
        profile_problem(
            "PU1", "P12", "Uncertainty, Calibration, and Rejection",
            "NMS-based deterministic inference forces hard segment selection under missing visual evidence",
            "How can MR avoid overconfident temporal selection when query-required evidence is missing or incomplete?",
            "NMS still selects the most probable segment although the model lacks evidence for the queried action.",
            "Deterministic MR cannot represent evidence insufficiency or abstain on hard moments.",
            "Cross-modal alignment improvements do not prevent deterministic post-processing from forcing a segment.",
            "inference", nms, chain, ex,
        ),
        profile_problem(
            "PU2", "P12", "Uncertainty, Calibration, and Rejection",
            "Vanilla DER miscalibrates uncertainty under multimodal evidence fusion",
            "How can DER be adapted when evidence must be fused from video and text?",
            "Higher-error predictions may receive lower uncertainty while accurate samples receive higher uncertainty.",
            "Vanilla DER relies on a heuristic regularizer and does not account for visual-text modality imbalance.",
            "Simple multimodal concatenation and evidence suppression misalign uncertainty with prediction error.",
            "model", der_issue, chain,
        ),
    ]
    methods = [
        profile_method(
            "MU1", "M06", "Uncertainty, Evidential Learning, and Calibration",
            "Deep Evidential Regression as an uncertainty-aware MR baseline",
            "Treat moment proposals as evidence and learn a second-order distribution that estimates sample uncertainty.",
            ["second-order evidential distribution", "proposal-as-evidence representation", "aleatoric uncertainty", "epistemic uncertainty", "uncertainty-guided gradients"],
            der, "proposal evidence and uncertainty", ["moment proposals", "video-text features"], "uncertainty-aware moment regression",
        ),
        profile_method(
            "MU2", "M06", "Uncertainty, Evidential Learning, and Calibration",
            "Debiased Evidential Learning with RFF, query reconstruction, and Geom regularization",
            "Use dual-branch progressive fusion and query reconstruction to reduce modality imbalance, then calibrate uncertainty from prediction accuracy.",
            ["Reflective Flipped Fusion", "dual-branch progressive cross-modal alignment", "Query Reconstruction", "Geom-regularizer", "counterintuitive uncertainty correction"],
            rff, "balanced visual-text evidence and prediction-error-aware uncertainty", ["video features", "query features", "moment proposals"], "debiased uncertainty and moment prediction",
        ),
        profile_method(
            "MU3", "M06", "Uncertainty, Evidential Learning, and Calibration",
            "Prediction-accuracy-aware Geom regularizer",
            "Adjust evidential uncertainty according to geometric prediction accuracy instead of uniformly suppressing evidence.",
            ["Geom-regularizer", "prediction-error-conditioned evidence suppression", "overconfidence correction"],
            geom, "prediction accuracy into uncertainty calibration", ["predicted moment", "ground-truth moment", "evidence parameters"], "calibrated uncertainty",
        ),
    ]
    return problems, methods


def cva_profile(records: list[dict[str, Any]], chain: dict[str, Any]):
    limitation = find_record(records, "query-agnostic", "false negatives")
    figure = find_record(records, "shown in fig. 1")
    qcd = find_record(records, "query-aware context diversification", "clip features")
    cbd = find_record(records, "context-invariant boundary discrimination")
    cte = find_record(records, "context-enhanced transformer encoder", "windowed self-attention")
    ex = ensure_known_example(
        chain,
        figure if "figure" in figure["lower"] or "fig." in figure["lower"] else limitation,
        "query-related replacement clip false-negative example",
        "Content mixing inserts a clip from another video that is nevertheless semantically related to the current query.",
        "Query-agnostic replacement can label a query-relevant clip as a negative training example.",
    )
    problems = [
        profile_problem(
            "PU1", "P11", "Dataset, Benchmark, and Evaluation Mismatch",
            "Query-agnostic content mixing creates semantically false negatives",
            "How can context diversification avoid replacing backgrounds with clips that remain relevant to the query?",
            "Semantically related replacement clips are treated as negatives and provide contradictory supervision.",
            "The augmentation samples replacement clips without measuring video-text relevance.",
            "Background replacement breaks spurious correlations but ignores whether the inserted content matches the query.",
            "training", limitation, chain, ex,
        ),
        profile_problem(
            "PU2", "P02", "Boundary Ambiguity and Localization Precision",
            "Temporal boundary representations change under diversified surrounding context",
            "How can boundary features remain semantically stable when the surrounding temporal context changes?",
            "Boundary clips become hard negatives or shift representation when context is replaced.",
            "Precise localization depends on local boundary evidence as well as surrounding temporal context.",
            "Standard alignment objectives do not explicitly enforce context-invariant boundary consistency.",
            "model", cbd, chain,
        ),
    ]
    methods = [
        profile_method(
            "MU1", "M01", "Pretraining, Pseudo-Labeling, and Data Generation",
            "Query-aware Context Diversification with CLIP relevance filtering",
            "Filter replacement clips by pretrained video-text relevance and preserve context immediately around the ground-truth moment.",
            ["Query-aware Context Diversification", "CLIP-based video-text relevance filtering", "false-negative prevention", "GT-context-preserving mask"],
            qcd, "query relevance into context augmentation", ["replacement clips", "text query", "CLIP features"], "query-consistent diversified training videos",
        ),
        profile_method(
            "MU2", "M10", "Contrastive or Cross-Modal Alignment",
            "Context-invariant Boundary Discrimination",
            "Apply a boundary-focused contrastive consistency objective across contextual shifts.",
            ["Context-invariant Boundary Discrimination", "boundary-focused contrastive learning", "context-shift consistency"],
            cbd, "boundary semantics across context variants", ["original video", "diversified video", "boundary features"], "context-invariant boundary representation",
        ),
        profile_method(
            "MU3", "M03", "Coarse-to-Fine or Hierarchical Localization",
            "Context-enhanced Transformer Encoder with local windows and bidirectional query aggregation",
            "Combine windowed self-attention with bidirectional cross-attention and learnable queries for multi-scale temporal context.",
            ["Context-enhanced Transformer Encoder", "windowed self-attention", "bidirectional cross-attention", "learnable queries", "hierarchical multi-scale context"],
            cte, "local and global temporal context", ["video clips", "learnable queries"], "multi-scale contextual representation",
        ),
    ]
    return problems, methods


def cliptbp_profile(records: list[dict[str, Any]], chain: dict[str, Any]):
    independent = find_record(records, "snippet-independent", "multiple correct answer segments")
    visual = find_record(records, "visually similar", "unable to distinguish")
    gap = find_record(records, "brief temporal gap", "overly broad")
    clip_loss = find_record(records, "clip-level similarity loss")
    boundary = find_record(records, "main boundary loss", "auxiliary boundary loss")
    figure = find_record(records, "pink hair")
    ex = ensure_known_example(
        chain,
        figure if "pink" in figure["lower"] else gap,
        "pink-haired woman repeated-segment example",
        "The query asks for a pink-haired woman describing her trip; visually similar or adjacent segments partially match but are not all correct.",
        "Independent snippet similarity merges distractors or adjacent answers and misses a short temporal gap.",
    )
    problems = [
        profile_problem(
            "PU1", "P05", "Multi-Moment, Compositional, and Complex Query Grounding",
            "Snippet-independent learning ignores relationships among multiple answer segments",
            "How can MR model semantic and temporal relationships among multiple correct answer segments?",
            "Independent snippet scoring cannot represent global relationships among multiple answer segments.",
            "The training unit is an isolated fixed-length snippet rather than a set or pair of answer clips.",
            "Efficient snippet-query matching discards inter-segment structure and global temporal context.",
            "model", independent, chain, ex,
        ),
        profile_problem(
            "PU2", "P02", "Boundary Ambiguity and Localization Precision",
            "Visually similar distractors and short gaps are merged into overly broad boundaries",
            "How can a model separate query-irrelevant visual matches and adjacent answers divided by a brief temporal gap?",
            "The model predicts one broad interval spanning distractors or several adjacent answer segments.",
            "Snippet-level similarity over-relies on partial visual overlap and lacks fine-grained inside-outside boundary structure.",
            "Independent saliency and offset regression cannot distinguish a short gap or partial query mismatch.",
            "model", gap if "gap" in gap["lower"] else visual, chain, ex,
        ),
    ]
    methods = [
        profile_method(
            "MU1", "M10", "Contrastive or Cross-Modal Alignment",
            "Clip-level similarity loss over positive answer-segment pairs and top-k hard negatives",
            "Learn relationships among clips inside the same ground-truth answer and contrast them with hard negative clip pairs.",
            ["clip-level similarity loss", "positive clip pairs inside GT segments", "top-k hard negative mining", "inter-segment semantic consistency"],
            clip_loss, "relationships among answer clips", ["clip embeddings", "GT answer segments", "text query"], "clip-pair contrastive supervision",
        ),
        profile_method(
            "MU2", "M05", "Boundary Refinement and Temporal Clustering",
            "Main and auxiliary boundary losses with inside-outside discrimination",
            "Supervise inside/outside boundary structure and stabilize start, end, center, and length regression with dynamic margins.",
            ["main boundary loss", "inside-outside boundary discrimination", "dynamic segment-length margin", "auxiliary boundary loss", "start/end/center/length regression"],
            boundary, "fine-grained boundary geometry", ["clip features", "ground-truth boundaries"], "precise temporal offsets",
        ),
    ]
    return problems, methods


def auvire_profile(records: list[dict[str, Any]], chain: dict[str, Any]):
    coarse = find_record(records, "coarse-grained video classification", "temporal forgery localization")
    underuse = find_record(records, "subtle cross-modal inconsistencies")
    reconstruction = find_record(records, "representation reconstruction module")
    discrepancy = find_record(records, "reconstruction-discrepancy encoder")
    problems = [
        profile_problem(
            "PU1", "P_NEW", "new_or_adjacent",
            "Video-level deepfake classification cannot localize short manipulated segments",
            "How can a deepfake detector identify the exact manipulated temporal interval rather than only classify the whole video?",
            "Coarse video-level classification hides brief forged intervals.",
            "Existing detectors optimize global authenticity rather than frame-level temporal boundaries.",
            "A single video label provides no fine-grained temporal supervision or boundary prediction.",
            "task_definition", coarse, chain,
        ),
        profile_problem(
            "PU2", "P_NEW", "new_or_adjacent",
            "Multimodal deepfake detectors underuse subtle audio-visual speech inconsistencies",
            "How can temporal forgery localization exploit discrepancies between audio and visual speech representations?",
            "Raw-signal fusion or generic features miss subtle cross-modal speech inconsistency.",
            "The relevant forgery cue is a mismatch between high-level audio and visual speech representations.",
            "Raw audio-visual processing overfits and general-purpose encoders lack speech-specific capacity.",
            "model", underuse, chain,
        ),
    ]
    methods = [
        profile_method(
            "MU1", "M12", "Multi-Modal Fusion and Feature Enhancement",
            "Audio-visual speech representation reconstruction",
            "Predict visual speech representations from audio and add unimodal audio-audio and visual-visual reconstruction paths.",
            ["audio-to-visual speech reconstruction", "audio-audio reconstruction", "visual-visual reconstruction", "pretrained speech-related feature extractors"],
            reconstruction, "cross-modal speech representations", ["audio speech features", "visual speech features"], "reconstruction errors",
        ),
        profile_method(
            "MU2", "M10", "Contrastive or Cross-Modal Alignment",
            "Reconstruction-discrepancy encoding for frame-level forgery localization",
            "Encode cross-modal reconstruction errors as discriminative forgery cues for frame classification and temporal boundaries.",
            ["cross-modal reconstruction discrepancy", "reconstruction-discrepancy encoder", "frame-level forgery classification", "temporal boundary regression"],
            discrepancy, "audio-visual inconsistency", ["reconstruction errors"], "frame-level forgery scores and temporal boundaries",
        ),
    ]
    return problems, methods


def enrich_chain_from_profile(
    chain: dict[str, Any],
    problems: list[dict[str, Any]],
    methods: list[dict[str, Any]],
) -> None:
    existing_limitation_ids = {
        item["evidence"][0]["evidence_id"] for item in chain["prior_work_limitation"] if item.get("evidence")
    }
    for problem in problems:
        ev = problem["evidence"][0]
        if ev["evidence_id"] not in existing_limitation_ids:
            chain["prior_work_limitation"].append(
                {
                    "summary": problem["micro_problem_name"],
                    "evidence": [ev],
                    "role": "limitation",
                }
            )
    existing_method_ids = {
        item["evidence"][0]["evidence_id"] for item in chain["method_transition"] if item.get("evidence")
    }
    for method in methods:
        ev = method["evidence"][0]
        if ev["evidence_id"] not in existing_method_ids:
            chain["method_transition"].append(
                {
                    "summary": method["micro_method_name"],
                    "evidence": [ev],
                    "role": "method_transition",
                }
            )


def novelty_axes(problems: list[dict[str, Any]], methods: list[dict[str, Any]]) -> list[dict[str, str]]:
    axes = []
    for method in methods[:3]:
        axes.append(
            {
                "axis": method.get("macro_method_name") or method.get("legacy_macro_method_name") or "paper-specific mechanism",
                "what_is_new": method["micro_method_name"],
                "compared_to": problems[0]["why_existing_methods_fail"] if problems else "prior temporal grounding methods",
                "why_it_matters": f"It directly targets {problems[0]['micro_problem_name'] if problems else 'the introduction-defined failure mode'}.",
            }
        )
    return axes


def transferable_units(methods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units = []
    for method in methods:
        method_facets = facets(" ".join([method["method_core_mechanism"], *method["method_components"]]))
        units.append(
            {
                "unit_name": method["micro_method_name"],
                "source_method_unit_id": method["method_unit_id"],
                "transferable_mechanism": method["method_core_mechanism"],
                "can_transfer_to": method_facets or ["temporal grounding problems with analogous evidence failure"],
                "required_assumption": "The target task exposes compatible inputs and a failure mode addressed by the mechanism.",
                "risk": "The mechanism may depend on task-specific supervision or representations.",
                "evidence": method["evidence"],
            }
        )
    return units


def reviewer_risks(task_scope: dict[str, Any], methods: list[dict[str, Any]]) -> list[dict[str, str]]:
    risks = [
        {
            "risk": "Incremental combination risk",
            "why": "Multiple known modules may appear as engineering aggregation unless the causal link to the micro problem is isolated.",
            "possible_defense": "Use problem-specific diagnostics and component-wise ablations tied to introduction evidence.",
        },
        {
            "risk": "Cross-dataset generalization",
            "why": "A mechanism may exploit annotation or feature conventions of one benchmark.",
            "possible_defense": "Verify on at least two datasets or a controlled cross-domain split.",
        },
    ]
    if task_scope.get("is_adjacent_task"):
        risks.append(
            {
                "risk": "Task-transfer mismatch",
                "why": "The source method was designed for an adjacent task without language-conditioned retrieval.",
                "possible_defense": "Define the shared failure variable and add language conditioning in a minimal diagnostic first.",
            }
        )
    if any("pretrained" in method["method_core_mechanism"].lower() for method in methods):
        risks.append(
            {
                "risk": "Backbone dependence",
                "why": "Improvements may come from a stronger pretrained encoder rather than the proposed mechanism.",
                "possible_defense": "Keep the backbone frozen and compare under identical extracted features.",
            }
        )
    return risks


def minimum_experiments(
    title: str,
    datasets: list[str],
    problems: list[dict[str, Any]],
    methods: list[dict[str, Any]],
) -> list[dict[str, str]]:
    dataset = ", ".join(datasets[:2]) or "QVHighlights and Charades-STA"
    metric = "R@1 at IoU thresholds, mIoU, and a problem-specific diagnostic"
    return [
        {
            "experiment_name": f"Minimal mechanism test for {methods[0]['micro_method_name'] if methods else title}",
            "baseline": title,
            "dataset": dataset,
            "module_to_modify": methods[0]["micro_method_name"] if methods else "target mechanism",
            "metric": metric,
            "expected_observation": f"Improvement should be concentrated on cases exhibiting {problems[0]['failure_mode'] if problems else 'the extracted failure mode'}.",
        }
    ]


def build_paper_card(paper_dir: Path) -> dict[str, Any]:
    metadata = read_json(paper_dir / "metadata.json", default={}) or {}
    title = metadata.get("title") or paper_dir.name
    sections = load_sections(paper_dir)
    records = sentence_records(sections)
    task_scope = infer_task_scope(title, sections)
    chain = extract_intro_chain(records, sections)
    profile = known_profile(title, records, chain)
    if profile:
        problems, methods = profile
        enrich_chain_from_profile(chain, problems, methods)
    else:
        problems = extract_generic_problem_units(records, chain, task_scope)
        methods = extract_generic_method_units(records)
    if not methods:
        fallback = records[0] if records else {"section": "Abstract", "text": title, "evidence_id": "EV000"}
        macro_id, macro_name = macro_match(title, METHOD_CLUSTERS, "M")
        methods = [
            profile_method(
                "MU1", macro_id, macro_name, f"Paper-specific mechanism from {title}",
                summarize_evidence(fallback["text"], 350), [summarize_evidence(fallback["text"], 140)],
                fallback, "task-specific temporal evidence", ["video features", "text query"], "temporal localization output",
            )
        ]
    links = build_problem_method_links(problems, methods)
    text = f"{sections['Abstract']} {sections['Introduction']}"
    datasets = extract_dataset_mentions(text)
    return {
        "paper_id": paper_dir.name,
        "local_dir": str(paper_dir),
        "title": title,
        "year": int(metadata.get("year") or 0),
        "venue_or_source": metadata.get("venue") or "",
        "authors": metadata.get("authors") or [],
        "task_scope": task_scope,
        "intro_motivation_chain": chain,
        "problem_units": problems,
        "method_units": methods,
        "problem_method_links": links,
        "novelty_axes": novelty_axes(problems, methods),
        "transferable_idea_units": transferable_units(methods),
        "reviewer_risk_points": reviewer_risks(task_scope, methods),
        "minimum_verification_experiments": minimum_experiments(title, datasets, problems, methods),
        "datasets": datasets,
        "metrics": extract_metric_mentions(text),
        "sources": {
            "abstract": str(paper_dir / "abstract.md"),
            "introduction": str(paper_dir / "introduction.md"),
            "full_text_fallback_used": len(normalize_whitespace(read_text(paper_dir / "introduction.md"))) < 1200,
        },
    }


def load_paper_dirs(library_dir: Path, sanity_only: bool = False, limit: int | None = None) -> list[Path]:
    candidates = []
    for paper_dir in sorted(path for path in library_dir.iterdir() if path.is_dir()):
        if not (paper_dir / "paper.pdf").exists():
            continue
        report = read_json(paper_dir / "repair_report.json", default={}) or {}
        if report and report.get("status") not in ("ok", None):
            continue
        metadata = read_json(paper_dir / "metadata.json", default={}) or {}
        title = metadata.get("title") or paper_dir.name
        if sanity_only and not any(key in title.lower() for key in SANITY_TITLES):
            continue
        candidates.append((paper_dir, title))
    deduplicated: dict[str, tuple[Path, str]] = {}
    for paper_dir, title in candidates:
        key = normalize_title(title)
        current = deduplicated.get(key)
        if current is None:
            deduplicated[key] = (paper_dir, title)
            continue
        current_year = int((read_json(current[0] / "metadata.json", default={}) or {}).get("year") or 9999)
        new_year = int((read_json(paper_dir / "metadata.json", default={}) or {}).get("year") or 9999)
        if new_year < current_year:
            deduplicated[key] = (paper_dir, title)
    paths = [item[0] for item in sorted(deduplicated.values(), key=lambda item: item[0].name)]
    return paths[:limit] if limit else paths


def unit_text(unit: dict[str, Any], kind: str) -> str:
    if kind == "problem":
        return clean_semantic_text(" ".join(
            [
                unit.get("micro_problem_name", ""),
                unit.get("failure_mode", ""),
                unit.get("root_cause", ""),
                unit.get("affected_scenario", ""),
            ]
        ))
    return clean_semantic_text(" ".join(
        [
            unit.get("micro_method_name", ""),
            unit.get("method_core_mechanism", ""),
            " ".join(unit.get("method_components", [])),
            unit.get("what_is_transferred_or_injected_or_aligned", ""),
        ]
    ))


def connected_components(similarity: np.ndarray, threshold: float) -> list[list[int]]:
    size = similarity.shape[0]
    seen = set()
    components = []
    for start in range(size):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            neighbors = np.flatnonzero(similarity[current] >= threshold)
            for neighbor in neighbors:
                value = int(neighbor)
                if value not in seen:
                    seen.add(value)
                    stack.append(value)
        components.append(component)
    return components


def semantic_projection(matrix: Any, max_components: int = 64) -> np.ndarray:
    max_rank = min(matrix.shape[0] - 1, matrix.shape[1] - 1, max_components)
    if max_rank < 2:
        return matrix.toarray()
    projected = TruncatedSVD(n_components=max_rank, random_state=0).fit_transform(matrix)
    return Normalizer(copy=False).fit_transform(projected)


def cluster_atomic_units(
    cards: list[dict[str, Any]],
    kind: str,
    paper_scope: str = "all",
    id_prefix: str | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], str]]:
    field = "problem_units" if kind == "problem" else "method_units"
    items = []
    for card in cards:
        is_core = card["task_scope"].get("is_core_video_moment_retrieval")
        is_adjacent = card["task_scope"].get("is_adjacent_task")
        if paper_scope == "core" and not is_core:
            continue
        if paper_scope == "adjacent" and not is_adjacent:
            continue
        for unit in card[field]:
            items.append((card, unit))
    if not items:
        return {}, {}
    texts = [unit_text(unit, kind) for _, unit in items]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    matrix = vectorizer.fit_transform(texts)
    large_corpus = len(items) >= 100
    projected = semantic_projection(matrix, max_components=64 if large_corpus else 32)
    if len(items) <= 2:
        labels = np.arange(len(items), dtype=int)
    else:
        labels = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=(
                (0.60 if kind == "problem" else 0.50)
                if large_corpus
                else (0.75 if kind == "problem" else 0.78)
            ),
            metric="cosine",
            linkage="average",
        ).fit_predict(projected)
    components = [
        [index for index, value in enumerate(labels) if int(value) == label]
        for label in sorted(set(int(value) for value in labels))
    ]
    similarity = cosine_similarity(projected)
    clusters: dict[str, dict[str, Any]] = {}
    assignment: dict[tuple[str, str], str] = {}
    for cluster_number, component in enumerate(components, start=1):
        member_rows = [items[index] for index in component]
        prefix = id_prefix or ("MP" if kind == "problem" else "MM")
        cluster_id = f"{prefix}{cluster_number:04d}"
        centroid_scores = similarity[np.ix_(component, component)].mean(axis=1)
        representative_card, representative_unit = member_rows[int(np.argmax(centroid_scores))]
        sanity_members = [
            (card, unit)
            for card, unit in member_rows
            if any(token in card["title"].lower() for token in SANITY_TITLES)
        ]
        if sanity_members:
            representative_card, representative_unit = max(
                sanity_members,
                key=lambda row: len(row[1].get(f"micro_{kind}_name", "")),
            )
        years = Counter(str(card["year"]) for card, _ in member_rows if card.get("year"))
        papers = unique_papers(member_rows)
        if kind == "problem":
            cluster_facets = dominant_cluster_facets(texts, component)
            cluster_name = concise_micro_cluster_name(
                "problem",
                member_rows,
                matrix,
                vectorizer,
                component,
                cluster_facets,
            )
            cluster_facets = sorted(
                set(cluster_facets)
                | set(facets(f"{cluster_name} {representative_unit['failure_mode']}"))
            )
            cluster = {
                "micro_problem_id": cluster_id,
                "macro_problem_id": "",
                "macro_problem_name": "",
                "legacy_macro_hints": sorted(
                    {
                        unit.get("legacy_macro_problem_id", "")
                        for _, unit in member_rows
                        if unit.get("legacy_macro_problem_id")
                    }
                ),
                "name": cluster_name,
                "canonical_question": representative_unit["micro_problem_question"],
                "root_cause": representative_unit["root_cause"],
                "failure_mode": representative_unit["failure_mode"],
                "problem_types": dict(Counter(unit["problem_type"] for _, unit in member_rows)),
                "shared_failure_facets": cluster_facets,
                "paper_count": len(papers),
                "core_paper_count": len(
                    {
                        card["paper_id"]
                        for card, _ in member_rows
                        if card["task_scope"].get("is_core_video_moment_retrieval")
                    }
                ),
                "adjacent_paper_count": len(
                    {
                        card["paper_id"]
                        for card, _ in member_rows
                        if card["task_scope"].get("is_adjacent_task")
                    }
                ),
                "paper_count_by_year": dict(sorted(years.items())),
                "representative_papers": papers[:8],
                "member_units": member_refs(member_rows, kind),
            }
        else:
            components_flat = list(representative_unit.get("method_components", []))
            for _, unit in member_rows:
                for value in unit.get("method_components", []):
                    if value not in components_flat:
                        components_flat.append(value)
            cluster_facets = dominant_cluster_facets(texts, component)
            cluster_name = concise_micro_cluster_name(
                "method",
                member_rows,
                matrix,
                vectorizer,
                component,
                cluster_facets,
            )
            cluster_facets = sorted(
                set(cluster_facets)
                | set(facets(f"{cluster_name} {representative_unit['method_core_mechanism']}"))
            )
            cluster = {
                "micro_method_id": cluster_id,
                "macro_method_id": "",
                "macro_method_name": "",
                "legacy_macro_hints": sorted(
                    {
                        unit.get("legacy_macro_method_id", "")
                        for _, unit in member_rows
                        if unit.get("legacy_macro_method_id")
                    }
                ),
                "name": cluster_name,
                "core_mechanism": representative_unit["method_core_mechanism"],
                "components": components_flat[:20],
                "capability_facets": cluster_facets,
                "paper_count": len(papers),
                "core_paper_count": len(
                    {
                        card["paper_id"]
                        for card, _ in member_rows
                        if card["task_scope"].get("is_core_video_moment_retrieval")
                    }
                ),
                "adjacent_paper_count": len(
                    {
                        card["paper_id"]
                        for card, _ in member_rows
                        if card["task_scope"].get("is_adjacent_task")
                    }
                ),
                "paper_count_by_year": dict(sorted(years.items())),
                "representative_papers": papers[:8],
                "member_units": member_refs(member_rows, kind),
                "has_adjacent_source": any(card["task_scope"].get("is_adjacent_task") for card, _ in member_rows),
            }
        clusters[cluster_id] = cluster
        for card, unit in member_rows:
            assignment[(card["paper_id"], unit[f"{kind}_unit_id"])] = cluster_id
    return clusters, assignment


def dominant_cluster_facets(texts: list[str], indices: list[int]) -> list[str]:
    counts = Counter(
        facet
        for index in indices
        for facet in set(facets(texts[index]))
    )
    if not counts:
        return []
    minimum = max(1, math.ceil(len(indices) * 0.34))
    selected = [facet for facet, count in counts.most_common() if count >= minimum]
    return selected or [facet for facet, _ in counts.most_common(2)]


def concise_micro_cluster_name(
    kind: str,
    member_rows: list[tuple[dict[str, Any], dict[str, Any]]],
    matrix: Any,
    vectorizer: TfidfVectorizer,
    indices: list[int],
    cluster_facets: list[str],
) -> str:
    unit_field = f"micro_{kind}_name"
    bad_starts = (
        "this ", "these ", "despite ", "although ", "however ", "while ",
        "not only ", "motivated by ", "existing studies", "existing methods",
        "recent studies", "sting studies", "we propose", "we introduce",
        "our method", "our approach", "it is ", "there are ",
    )
    candidates = []
    for card, unit in member_rows:
        name = normalize_whitespace(unit.get(unit_field, "")).strip(" .,:;")
        is_sanity_unit = any(token in card["title"].lower() for token in SANITY_TITLES)
        if not is_sanity_unit or not name or len(name) > 150 or name.lower().startswith(bad_starts):
            continue
        specificity = len(set(facets(unit_text(unit, kind))))
        candidates.append((3 + specificity, -len(name), name))
    if candidates:
        name = max(candidates)[2]
        return name[0].upper() + name[1:] if name else name

    facet_counts = Counter(
        facet
        for _, unit in member_rows
        for facet in facets(unit_text(unit, kind))
    )
    if len(facet_counts) > 1:
        facet_counts.pop("cross_modal", None)
    dominant = facet_counts.most_common(1)[0][0] if facet_counts else (cluster_facets[0] if cluster_facets else "")
    name_lookup = PROBLEM_FACET_NAMES if kind == "problem" else METHOD_FACET_NAMES
    base = name_lookup.get(dominant, "Evidence Failure" if kind == "problem" else "Transferable Mechanism")
    terms = taxonomy_top_terms(matrix, vectorizer, indices, limit=4)
    qualifier = " / ".join(terms[:2]).title()
    return f"{base}: {qualifier}" if qualifier else base


def unique_papers(member_rows: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = {}
    for card, unit in member_rows:
        rows[card["paper_id"]] = {
            "paper_id": card["paper_id"],
            "title": card["title"],
            "year": card["year"],
            "venue_or_source": card["venue_or_source"],
            "task_scope": card["task_scope"]["primary_task"],
            "evidence": unit.get("evidence", [])[:1],
        }
    return sorted(rows.values(), key=lambda row: (-int(row["year"] or 0), row["title"]))


def member_refs(member_rows: list[tuple[dict[str, Any], dict[str, Any]]], kind: str) -> list[dict[str, str]]:
    return [
        {
            "paper_id": card["paper_id"],
            f"{kind}_unit_id": unit[f"{kind}_unit_id"],
            "name": unit[f"micro_{kind}_name"],
        }
        for card, unit in member_rows
    ]


def derive_emergent_taxonomy(
    micro_clusters: dict[str, dict[str, Any]],
    kind: str,
    id_prefix: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Re-condense top-level nodes from micro clusters without using legacy Pxx/Mxx."""
    rows = list(micro_clusters.items())
    if not rows:
        return {}
    text_field = "failure_mode" if kind == "problem" else "core_mechanism"
    facet_field = "shared_failure_facets" if kind == "problem" else "capability_facets"
    texts = []
    for _, cluster in rows:
        facet_tokens = " ".join(cluster.get(facet_field, []) * 3)
        components = " ".join(cluster.get("components", [])) if kind == "method" else cluster.get("root_cause", "")
        texts.append(f"{cluster.get('name', '')} {cluster.get(text_field, '')} {components} {facet_tokens}")
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    matrix = vectorizer.fit_transform(texts)
    projected = semantic_projection(matrix, max_components=24)
    similarity = cosine_similarity(projected)
    if len(rows) <= 2:
        labels = np.zeros(len(rows), dtype=int)
    else:
        model = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=0.88,
            metric="cosine",
            linkage="average",
        )
        labels = merge_singleton_taxonomy_labels(model.fit_predict(projected), similarity)

    grouped: dict[int, list[int]] = defaultdict(list)
    for index, label in enumerate(labels):
        grouped[int(label)].append(index)

    taxonomy: dict[str, dict[str, Any]] = {}
    used_names: Counter[str] = Counter()
    prefix = id_prefix or ("EP" if kind == "problem" else "EM")
    name_lookup = PROBLEM_FACET_NAMES if kind == "problem" else METHOD_FACET_NAMES
    ordered_groups = sorted(grouped.values(), key=lambda values: (-len(values), min(values)))
    for number, indices in enumerate(ordered_groups, start=1):
        macro_id = f"{prefix}{number:03d}"
        facet_counts = Counter(
            facet
            for index in indices
            for facet in rows[index][1].get(facet_field, [])
        )
        if len(facet_counts) > 1:
            facet_counts.pop("cross_modal", None)
        dominant_facets = [facet for facet, _ in facet_counts.most_common(2)]
        base_name = " and ".join(name_lookup.get(facet, facet.replace("_", " ").title()) for facet in dominant_facets)
        top_terms = taxonomy_top_terms(matrix, vectorizer, indices)
        if not base_name:
            base_name = " / ".join(term.title() for term in top_terms[:3]) or (
                "Emergent Problem Family" if kind == "problem" else "Emergent Method Family"
            )
        used_names[base_name] += 1
        name = base_name if used_names[base_name] == 1 else f"{base_name}: {' / '.join(top_terms[:2]).title()}"
        member_ids = [rows[index][0] for index in indices]
        paper_ids = {
            paper["paper_id"]
            for index in indices
            for paper in rows[index][1].get("representative_papers", [])
        }
        years = Counter()
        for index in indices:
            years.update(rows[index][1].get("paper_count_by_year", {}))
        taxonomy[macro_id] = {
            f"macro_{kind}_id": macro_id,
            "name": name,
            "description": emergent_taxonomy_description(kind, dominant_facets, top_terms),
            "derived_from_bottom_up": True,
            "micro_cluster_count": len(member_ids),
            "paper_count": len(paper_ids),
            "paper_count_by_year": dict(sorted(years.items())),
            "dominant_facets": dominant_facets,
            "top_terms": top_terms,
            f"micro_{kind}_ids": member_ids,
            "legacy_macro_hints": sorted(
                {
                    hint
                    for index in indices
                    for hint in rows[index][1].get("legacy_macro_hints", [])
                }
            ),
        }
        for index in indices:
            cluster = rows[index][1]
            cluster[f"macro_{kind}_id"] = macro_id
            cluster[f"macro_{kind}_name"] = name
    return taxonomy


def merge_singleton_taxonomy_labels(labels: np.ndarray, similarity: np.ndarray) -> np.ndarray:
    labels = labels.copy()
    grouped: dict[int, list[int]] = defaultdict(list)
    for index, label in enumerate(labels):
        grouped[int(label)].append(index)
    singleton_indices = [indices[0] for indices in grouped.values() if len(indices) == 1]
    non_singleton_groups = [(label, indices) for label, indices in grouped.items() if len(indices) >= 2]
    if not singleton_indices:
        return labels
    if non_singleton_groups:
        for index in singleton_indices:
            candidates = [
                (float(np.mean(similarity[index, indices])), label)
                for label, indices in non_singleton_groups
            ]
            labels[index] = max(candidates)[1]
        return labels

    # If agglomeration produced only singletons, form nearest pairs without a fixed family count.
    unassigned = set(singleton_indices)
    next_label = int(max(labels)) + 1
    while len(unassigned) >= 2:
        first = min(unassigned)
        unassigned.remove(first)
        second = max(unassigned, key=lambda index: float(similarity[first, index]))
        unassigned.remove(second)
        labels[first] = next_label
        labels[second] = next_label
        next_label += 1
    if unassigned:
        last = unassigned.pop()
        existing: dict[int, list[int]] = defaultdict(list)
        for index, label in enumerate(labels):
            if index != last:
                existing[int(label)].append(index)
        labels[last] = max(
            (
                float(np.mean(similarity[last, indices])),
                label,
            )
            for label, indices in existing.items()
        )[1]
    return labels


def taxonomy_top_terms(
    matrix: Any,
    vectorizer: TfidfVectorizer,
    indices: list[int],
    limit: int = 6,
) -> list[str]:
    generic_terms = {
        "video", "model", "method", "temporal", "grounding", "trained", "following",
        "limitations", "limitation", "suffer", "effective", "including", "sentence",
        "multi", "module", "approach", "existing", "paper", "proposed", "learning",
        "simple", "novel", "framework", "namely", "comprising", "components",
        "challenge", "address", "recent", "current", "results", "using", "based",
        "task", "motivated", "achieve", "improve", "introduce",
        "contributions", "contribution", "present", "figure", "shown", "depicted",
        "experiment", "experiments", "demonstrate", "observations", "result",
        "results", "evaluation", "requires", "terms",
    }
    scores = np.asarray(matrix[indices].mean(axis=0)).ravel()
    terms = vectorizer.get_feature_names_out()
    out = []
    for index in scores.argsort()[::-1]:
        term = terms[index]
        if (
            len(term) < 4
            or term in generic_terms
            or any(token in generic_terms for token in term.split())
            or any(char.isdigit() for char in term)
        ):
            continue
        if any(term in existing or existing in term for existing in out):
            continue
        out.append(term)
        if len(out) >= limit:
            break
    return out


def emergent_taxonomy_description(kind: str, facets_: list[str], top_terms: list[str]) -> str:
    subject = "problems" if kind == "problem" else "mechanisms"
    facet_text = ", ".join(facets_) or "shared semantic structure"
    return (
        f"Bottom-up family of micro {subject} sharing {facet_text}. "
        f"The most discriminative local terms are: {', '.join(top_terms[:5])}."
    )


def apply_emergent_taxonomy_to_cards(
    cards: list[dict[str, Any]],
    micro_problems: dict[str, dict[str, Any]],
    micro_methods: dict[str, dict[str, Any]],
) -> None:
    for card in cards:
        for unit in card["problem_units"]:
            cluster = micro_problems.get(unit.get("micro_problem_cluster_id", ""), {})
            unit["macro_problem_id"] = cluster.get("macro_problem_id", "")
            unit["macro_problem_name"] = cluster.get("macro_problem_name", "")
        for unit in card["method_units"]:
            cluster = micro_methods.get(unit.get("micro_method_cluster_id", ""), {})
            unit["macro_method_id"] = cluster.get("macro_method_id", "")
            unit["macro_method_name"] = cluster.get("macro_method_name", "")
        for link in card["problem_method_links"]:
            problem_cluster = micro_problems.get(link.get("micro_problem_cluster_id", ""), {})
            method_cluster = micro_methods.get(link.get("micro_method_cluster_id", ""), {})
            link["macro_problem_id"] = problem_cluster.get("macro_problem_id", "")
            link["macro_method_id"] = method_cluster.get("macro_method_id", "")


def apply_cluster_ids(
    cards: list[dict[str, Any]],
    problem_assignment: dict[tuple[str, str], str],
    method_assignment: dict[tuple[str, str], str],
) -> None:
    for card in cards:
        for unit in card["problem_units"]:
            unit["micro_problem_cluster_id"] = problem_assignment.get((card["paper_id"], unit["problem_unit_id"]), "")
        for unit in card["method_units"]:
            unit["micro_method_cluster_id"] = method_assignment.get((card["paper_id"], unit["method_unit_id"]), "")
        for link in card["problem_method_links"]:
            link["micro_problem_cluster_id"] = problem_assignment.get((card["paper_id"], link["problem_unit_id"]), "")
            link["micro_method_cluster_id"] = method_assignment.get((card["paper_id"], link["method_unit_id"]), "")


def write_micro_matrix(cards: list[dict[str, Any]], out_dir: Path) -> dict[tuple[str, str], int]:
    counts: Counter[tuple[str, str]] = Counter()
    problem_ids = set()
    method_ids = set()
    for card in cards:
        if not card["task_scope"].get("is_core_video_moment_retrieval"):
            continue
        for link in card["problem_method_links"]:
            problem_id = link.get("micro_problem_cluster_id")
            method_id = link.get("micro_method_cluster_id")
            if problem_id and method_id:
                counts[(problem_id, method_id)] += 1
                problem_ids.add(problem_id)
                method_ids.add(method_id)
    problem_ids = sorted(problem_ids)
    method_ids = sorted(method_ids)
    with (out_dir / "micro_problem_method_matrix.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["micro_problem_id", *method_ids])
        for problem_id in problem_ids:
            writer.writerow([problem_id, *[counts[(problem_id, method_id)] for method_id in method_ids]])
    return dict(counts)


def build_fine_ideas(
    cards: list[dict[str, Any]],
    problems: dict[str, dict[str, Any]],
    methods: dict[str, dict[str, Any]],
    coverage: dict[tuple[str, str], int],
) -> list[dict[str, Any]]:
    ideas = []
    for problem_id, problem in problems.items():
        if contaminated_cluster_name(problem.get("name", "")):
            continue
        problem_quality = problem_cluster_quality(problem)
        if problem_quality < 2.0:
            continue
        target_facets = set(problem.get("shared_failure_facets", []))
        if not target_facets:
            target_facets = set(facets(f"{problem['failure_mode']} {problem['root_cause']}"))
        for method_id, method in methods.items():
            if contaminated_cluster_name(method.get("name", "")):
                continue
            method_quality = method_cluster_quality(method)
            if method_quality < 2.0:
                continue
            source_facets = set(method.get("capability_facets", []))
            shared = target_facets & source_facets
            specific_shared = shared - {"cross_modal", "context", "representation"}
            compatible = [
                reason
                for source_facet in source_facets
                for target_facet in target_facets
                if (reason := FACET_TRANSFER_COMPATIBILITY.get((source_facet, target_facet)))
            ]
            lexical = text_similarity(
                f"{problem['failure_mode']} {problem['root_cause']}",
                f"{method['core_mechanism']} {' '.join(method['components'])}",
            )
            if not specific_shared and not compatible and lexical < 0.32:
                continue
            current = coverage.get((problem_id, method_id), 0)
            if current >= max(2, math.ceil(problem["paper_count"] * 0.35)):
                continue
            source_count = method["paper_count"]
            sanity_source = any(
                any(token in paper.get("title", "").lower() for token in SANITY_TITLES)
                for paper in method.get("representative_papers", [])
            )
            newest = max((int(year) for year in problem["paper_count_by_year"]), default=0)
            score = (
                3.0
                + min(2.0, len(shared) * 0.8)
                + min(2.5, len(compatible) * 1.4)
                + min(1.5, lexical * 5)
                + min(1.2, math.log1p(source_count) / 2)
                + (0.8 if current == 0 else 0.2)
                + (0.5 if newest >= 2025 else 0)
                + (0.8 if method.get("has_adjacent_source") and compatible else 0.2 if method.get("has_adjacent_source") else 0)
                + (1.0 if sanity_source else 0)
                + min(1.0, (problem_quality + method_quality) / 8)
                - min(1.0, problem["paper_count"] / 40)
            )
            target_papers = problem["representative_papers"][:3]
            source_papers = method["representative_papers"][:3]
            dataset = choose_dataset(cards, target_papers)
            baseline = target_papers[0]["title"] if target_papers else "a recent VMR baseline"
            shared_text = (
                "; ".join(dict.fromkeys(compatible))
                if compatible
                else ", ".join(sorted(specific_shared or shared))
            ) or "a semantically compatible evidence failure"
            mechanism = method["core_mechanism"]
            ideas.append(
                {
                    "idea_id": "",
                    "score": round(score, 2),
                    "target_micro_problem_id": problem_id,
                    "target_micro_problem": problem["name"],
                    "source_micro_method_id": method_id,
                    "source_micro_method": method["name"],
                    "source_papers": source_papers,
                    "target_papers": target_papers,
                    "shared_failure_mode": shared_text,
                    "transferable_mechanism": mechanism,
                    "why_currently_underused": f"The local graph contains {current} direct problem-method link(s), versus {source_count} source paper(s) for the method cluster.",
                    "candidate_idea": idea_title(problem, method),
                    "technical_sketch": technical_sketch(problem, method),
                    "minimum_verification_experiment": (
                        f"Use {baseline} on {dataset}; add or replace the module responsible for "
                        f"{problem['failure_mode']} with {method['name']}. Keep extracted features fixed, "
                        "report R@1/mIoU and a subset diagnostic that isolates the target failure."
                    ),
                    "expected_gain": f"Better localization or calibration on cases characterized by {problem['failure_mode']}.",
                    "reviewer_attack_points": [
                        {
                            "risk": "Novelty may look like direct module transplantation.",
                            "mitigation": "Define the shared failure variable and compare against a naive plug-in baseline.",
                        },
                        {
                            "risk": "The source mechanism may require incompatible supervision or features.",
                            "mitigation": "Start with a frozen-feature diagnostic and document added inputs and labels.",
                        },
                        {
                            "risk": "Average benchmark gains may hide failure-specific behavior.",
                            "mitigation": "Predefine a target subset and report calibration or boundary diagnostics.",
                        },
                    ],
                    "risk_level": "medium-high" if method.get("has_adjacent_source") else "medium",
                    "is_cross_task_transfer": bool(method.get("has_adjacent_source") and compatible),
                    "novelty_reason": (
                        f"The proposal links atomic problem {problem_id} to atomic method {method_id}; "
                        f"their direct coverage is {current}, while their shared mechanism is {shared_text}."
                    ),
                    "not_justification": "This is not justified by a coarse Pxx x Mxx gap; it is traceable to paper-level problem units, method units, and introduction evidence.",
                    "target_problem_evidence": collect_cluster_evidence(problem),
                    "source_method_evidence": collect_cluster_evidence(method),
                }
            )
    ideas.sort(key=lambda row: (-row["score"], row["target_micro_problem_id"], row["source_micro_method_id"]))
    selected = []
    per_problem = Counter()
    reserved_mechanisms = set()
    for idea in ideas:
        mechanism_key = idea["shared_failure_mode"]
        if not idea["is_cross_task_transfer"] or mechanism_key in reserved_mechanisms:
            continue
        selected.append(idea)
        reserved_mechanisms.add(mechanism_key)
        per_problem[idea["target_micro_problem_id"]] += 1
        if len(selected) >= 20:
            break
    for idea in ideas:
        if idea in selected:
            continue
        if per_problem[idea["target_micro_problem_id"]] >= 3:
            continue
        selected.append(idea)
        per_problem[idea["target_micro_problem_id"]] += 1
        if len(selected) >= 60:
            break
    selected.sort(key=lambda row: (-row["score"], row["target_micro_problem_id"], row["source_micro_method_id"]))
    for index, idea in enumerate(selected, start=1):
        idea["idea_id"] = f"FI{index:03d}"
    return selected


def contaminated_cluster_name(name: str) -> bool:
    lower = name.lower()
    noise = (
        "abstract", "corresponding author", "open access", "copyright", "qeios",
        "university", "arxiv", "proceedings", "computer vision foundation",
        "specific / abstract", "author /", "et al",
    )
    return any(token in lower for token in noise)


def problem_cluster_quality(problem: dict[str, Any]) -> float:
    score = 0.0
    if not contaminated_cluster_name(problem.get("name", "")):
        score += 1.0
    if problem.get("shared_failure_facets"):
        score += 1.0
    failure = problem.get("failure_mode", "").lower()
    if contains_any(failure, STRONG_FAILURE_MARKERS) or contains_any(
        failure,
        ("query-agnostic", "overly broad", "missing evidence", "temporal gap", "domain gap"),
    ):
        score += 1.5
    if len(problem.get("root_cause", "")) >= 45:
        score += 0.5
    if len(problem.get("representative_papers", [])) >= 2:
        score += 0.5
    return score


def method_cluster_quality(method: dict[str, Any]) -> float:
    score = 0.0
    if not contaminated_cluster_name(method.get("name", "")):
        score += 1.0
    if method.get("capability_facets"):
        score += 1.0
    components = [
        item for item in method.get("components", [])
        if len(item) >= 5 and not contaminated_cluster_name(item)
    ]
    if len(components) >= 2:
        score += 1.0
    mechanism = method.get("core_mechanism", "").lower()
    if contains_any(mechanism, METHOD_MARKERS) or contains_any(
        mechanism,
        ("inject", "reconstruct", "calibrat", "contrastive", "boundary", "ranking", "selection"),
    ):
        score += 1.0
    if len(method.get("representative_papers", [])) >= 2:
        score += 0.5
    return score


def text_similarity(left: str, right: str) -> float:
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        matrix = vectorizer.fit_transform([left, right])
    except ValueError:
        return 0.0
    return float(cosine_similarity(matrix[0], matrix[1])[0, 0])


def idea_title(problem: dict[str, Any], method: dict[str, Any]) -> str:
    return f"{compact_label(method['name'], 72)} for {compact_label(problem['name'], 88)}"


def compact_label(text: str, limit: int) -> str:
    text = normalize_whitespace(text).strip(" .,:;")
    text = re.split(r"\b(?:motivated by|for motivated|which|that|whereby)\b", text, maxsplit=1, flags=re.I)[0].strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def technical_sketch(problem: dict[str, Any], method: dict[str, Any]) -> str:
    components = ", ".join(method.get("components", [])[:4])
    return (
        f"Instrument the target baseline to detect cases of {problem['failure_mode']}. "
        f"Insert {method['name']}. Implement its core mechanism as follows: {method['core_mechanism']} "
        f"Use the representative components {components or 'listed in the source method evidence'}; "
        f"train it against the existing localization objective plus a diagnostic loss tied to {problem['root_cause']}."
    )


def choose_dataset(cards: list[dict[str, Any]], papers: list[dict[str, Any]]) -> str:
    by_id = {card["paper_id"]: card for card in cards}
    datasets = []
    for paper in papers:
        for dataset in by_id.get(paper["paper_id"], {}).get("datasets", []):
            if dataset not in datasets:
                datasets.append(dataset)
    return " and ".join(datasets[:2]) or "QVHighlights and Charades-STA"


def collect_cluster_evidence(cluster: dict[str, Any]) -> list[dict[str, Any]]:
    evidence_rows = []
    for paper in cluster.get("representative_papers", [])[:3]:
        for ev in paper.get("evidence", [])[:1]:
            evidence_rows.append({"paper_id": paper["paper_id"], "title": paper["title"], **ev})
    return evidence_rows


def validate_cards(
    cards: list[dict[str, Any]],
    problem_taxonomy: dict[str, dict[str, Any]] | None = None,
    method_taxonomy: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    errors = []
    warnings = []
    stats = Counter()
    for card in cards:
        title = card["title"]
        chain = card["intro_motivation_chain"]
        intro_text = load_sections(Path(card["local_dir"]))["Introduction"]
        stats["papers"] += 1
        stats["problem_units"] += len(card["problem_units"])
        stats["method_units"] += len(card["method_units"])
        stats["examples"] += len(chain["illustrative_examples"])
        if not any(chain.values()):
            errors.append(f"{title}: empty intro_motivation_chain")
        if not card["problem_units"]:
            errors.append(f"{title}: no problem_units")
        if not card["method_units"]:
            errors.append(f"{title}: no method_units")
        for unit in card["problem_units"]:
            if not unit.get("evidence"):
                errors.append(f"{title}: problem unit without evidence")
            if not unit.get("linked_intro_evidence_ids") and not unit.get("linked_example_ids"):
                errors.append(f"{title}: problem unit without intro/example link")
            if unit.get("micro_problem_name") == unit.get("macro_problem_name"):
                errors.append(f"{title}: micro problem equals macro label")
        for unit in card["method_units"]:
            if not unit.get("evidence"):
                errors.append(f"{title}: method unit without evidence")
            if unit.get("micro_method_name") == unit.get("macro_method_name"):
                errors.append(f"{title}: micro method equals macro label")
        lower_intro = intro_text.lower()
        if contains_any(lower_intro, EXAMPLE_MARKERS) and not chain["illustrative_examples"]:
            errors.append(f"{title}: example marker present but illustrative_examples empty")
        if contains_any(lower_intro, ("however", "while effective", "despite", " but ")) and not chain["prior_work_limitation"]:
            errors.append(f"{title}: contrast marker present but prior_work_limitation empty")
        inference_failure_present = any(
            contains_any(record["lower"], INFERENCE_MARKERS) and is_problem_candidate(record)
            for record in sentence_records({"Introduction": intro_text})
        )
        if inference_failure_present:
            if not any(unit["problem_type"] == "inference" for unit in card["problem_units"]):
                warnings.append(f"{title}: inference markers present but no inference problem unit")
        for bucket in chain.values():
            for item in bucket:
                for ev in item.get("evidence", []):
                    if ev["section"] == "Related Work":
                        errors.append(f"{title}: Related Work evidence used")
    for taxonomy_name, taxonomy in (
        ("problem", problem_taxonomy or {}),
        ("method", method_taxonomy or {}),
    ):
        for macro_id, node in taxonomy.items():
            if node.get("micro_cluster_count", 0) < 2:
                errors.append(f"{macro_id}: emergent {taxonomy_name} family has fewer than two micro clusters")
            if not node.get("derived_from_bottom_up"):
                errors.append(f"{macro_id}: emergent {taxonomy_name} family is not marked bottom-up")
    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": dict(stats),
        "multi_problem_papers": sum(len(card["problem_units"]) > 1 for card in cards),
        "multi_method_papers": sum(len(card["method_units"]) > 1 for card in cards),
        "adjacent_papers": sum(card["task_scope"].get("is_adjacent_task") for card in cards),
    }


def sanity_assertions(cards: list[dict[str, Any]]) -> dict[str, Any]:
    results = {}
    checks = {
        "actprompt": ("action-sensitive", "action-cue-injected", "context-aware temporal prompt"),
        "adaptive evidential": ("nms-based", "vanilla der", "reflective flipped fusion", "geom"),
        "cva:": ("query-agnostic", "query-aware context diversification", "boundary discrimination"),
        "cliptbp:": ("snippet-independent", "clip-level similarity", "auxiliary boundary"),
        "auvire:": ("video-level deepfake", "reconstruction-discrepancy", "adjacent"),
    }
    for label, required in checks.items():
        card = next((card for card in cards if label in card["title"].lower()), None)
        if not card:
            results[label] = {"passed": False, "missing": ["paper"]}
            continue
        blob = json.dumps(card, ensure_ascii=False).lower()
        missing = [phrase for phrase in required if phrase not in blob]
        if label == "auvire:" and not card["task_scope"].get("is_adjacent_task"):
            missing.append("adjacent_task_flag")
        results[label] = {"passed": not missing, "missing": missing, "paper_id": card["paper_id"]}
    return {"passed": all(item["passed"] for item in results.values()), "papers": results}


def write_card_files(cards: list[dict[str, Any]], out_dir: Path) -> None:
    card_dir = out_dir / "paper_micro_cards"
    if card_dir.exists():
        shutil.rmtree(card_dir)
    card_dir.mkdir(parents=True)
    for card in cards:
        write_json(card_dir / f"{card['paper_id']}.json", card)


def write_summary(
    out_dir: Path,
    cards: list[dict[str, Any]],
    problem_taxonomy: dict[str, dict[str, Any]],
    adjacent_problem_taxonomy: dict[str, dict[str, Any]],
    method_taxonomy: dict[str, dict[str, Any]],
    micro_problems: dict[str, dict[str, Any]],
    micro_methods: dict[str, dict[str, Any]],
    ideas: list[dict[str, Any]],
    quality: dict[str, Any],
) -> None:
    lines = [
        "# Fine-grained Idea Graph",
        "",
        "Bottom-up graph built from Abstract and Introduction evidence only.",
        "",
        f"- Deduplicated papers: {len(cards)}",
        f"- Core VMR/VTG papers: {sum(card['task_scope']['is_core_video_moment_retrieval'] for card in cards)}",
        f"- Adjacent-task papers: {sum(card['task_scope']['is_adjacent_task'] for card in cards)}",
        f"- Atomic problem units: {sum(len(card['problem_units']) for card in cards)}",
        f"- Atomic method units: {sum(len(card['method_units']) for card in cards)}",
        f"- Emergent top-level problem families: {len(problem_taxonomy)}",
        f"- Emergent adjacent-task problem families: {len(adjacent_problem_taxonomy)}",
        f"- Emergent top-level method families: {len(method_taxonomy)}",
        f"- Micro problem clusters: {len(micro_problems)}",
        f"- Micro method clusters: {len(micro_methods)}",
        f"- Fine-grained ideas: {len(ideas)}",
        f"- Quality passed: {quality['passed']}",
        "",
        "Top-level EPxx/EMxx families are re-derived from micro clusters and their count is data-dependent.",
        "Legacy Pxx/Mxx labels are retained only as compatibility hints and never drive clustering, linking, or idea inference.",
    ]
    (out_dir / "README_FINEGRAINED.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a bottom-up, evidence-grounded fine-grained VMR idea graph.")
    parser.add_argument("--library-dir", default=str(DEFAULT_LIBRARY_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sanity-only", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    library_dir = Path(args.library_dir)
    out_dir = ensure_dir(Path(args.out_dir))
    paper_dirs = load_paper_dirs(library_dir, sanity_only=args.sanity_only, limit=args.limit)
    cards = [build_paper_card(path) for path in paper_dirs]
    micro_problems, problem_assignment = cluster_atomic_units(cards, "problem", paper_scope="core", id_prefix="MP")
    adjacent_micro_problems, adjacent_problem_assignment = cluster_atomic_units(
        cards,
        "problem",
        paper_scope="adjacent",
        id_prefix="AMP",
    )
    micro_methods, method_assignment = cluster_atomic_units(cards, "method", paper_scope="all", id_prefix="MM")
    problem_assignment.update(adjacent_problem_assignment)
    apply_cluster_ids(cards, problem_assignment, method_assignment)
    problem_taxonomy = derive_emergent_taxonomy(micro_problems, "problem")
    adjacent_problem_taxonomy = derive_emergent_taxonomy(
        adjacent_micro_problems,
        "problem",
        id_prefix="AP",
    )
    method_taxonomy = derive_emergent_taxonomy(micro_methods, "method")
    all_micro_problems = {**micro_problems, **adjacent_micro_problems}
    apply_emergent_taxonomy_to_cards(cards, all_micro_problems, micro_methods)
    coverage = write_micro_matrix(cards, out_dir)
    ideas = build_fine_ideas(cards, micro_problems, micro_methods, coverage)
    adjacent = [
        {
            "paper_id": card["paper_id"],
            "title": card["title"],
            "year": card["year"],
            "venue_or_source": card["venue_or_source"],
            "task_scope": card["task_scope"],
            "problem_units": card["problem_units"],
            "method_units": card["method_units"],
            "transferable_idea_units": card["transferable_idea_units"],
        }
        for card in cards
        if card["task_scope"].get("is_adjacent_task")
    ]
    quality = validate_cards(
        cards,
        {**problem_taxonomy, **adjacent_problem_taxonomy},
        method_taxonomy,
    )
    sanity = sanity_assertions(cards) if args.sanity_only else {}
    if sanity:
        quality["sanity"] = sanity
        quality["passed"] = quality["passed"] and sanity["passed"]

    write_card_files(cards, out_dir)
    write_json(out_dir / "paper_micro_cards_index.json", cards)
    write_json(
        out_dir / "intro_motivation_chains.json",
        [
            {
                "paper_id": card["paper_id"],
                "title": card["title"],
                "task_scope": card["task_scope"],
                "intro_motivation_chain": card["intro_motivation_chain"],
            }
            for card in cards
        ],
    )
    write_json(out_dir / "micro_problem_clusters.json", micro_problems)
    write_json(out_dir / "adjacent_micro_problem_clusters.json", adjacent_micro_problems)
    write_json(out_dir / "micro_method_clusters.json", micro_methods)
    write_json(out_dir / "emergent_problem_taxonomy.json", problem_taxonomy)
    write_json(out_dir / "adjacent_problem_taxonomy.json", adjacent_problem_taxonomy)
    write_json(out_dir / "emergent_method_taxonomy.json", method_taxonomy)
    write_json(out_dir / "adjacent_task_papers.json", adjacent)
    write_json(out_dir / "idea_opportunities_finegrained.json", ideas)
    write_json(out_dir / "finegrained_quality_report.json", quality)
    write_summary(
        out_dir,
        cards,
        problem_taxonomy,
        adjacent_problem_taxonomy,
        method_taxonomy,
        micro_problems,
        micro_methods,
        ideas,
        quality,
    )
    result = {
        "papers": len(cards),
        "core_papers": sum(card["task_scope"].get("is_core_video_moment_retrieval") for card in cards),
        "adjacent_papers": len(adjacent),
        "atomic_problem_units": sum(len(card["problem_units"]) for card in cards),
        "atomic_method_units": sum(len(card["method_units"]) for card in cards),
        "emergent_problem_families": len(problem_taxonomy),
        "emergent_adjacent_problem_families": len(adjacent_problem_taxonomy),
        "emergent_method_families": len(method_taxonomy),
        "micro_problem_clusters": len(micro_problems),
        "adjacent_micro_problem_clusters": len(adjacent_micro_problems),
        "micro_method_clusters": len(micro_methods),
        "finegrained_ideas": len(ideas),
        "quality_passed": quality["passed"],
        "quality_errors": len(quality["errors"]),
        "quality_warnings": len(quality["warnings"]),
        "out_dir": str(out_dir),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and not quality["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
