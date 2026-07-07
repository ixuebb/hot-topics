"""JSON数据加载与内存索引"""
import json
from collections import defaultdict
from pathlib import Path


class DataLoader:
    def __init__(self, data_root: str | Path):
        self.data_root = Path(data_root)
        self.ideas = []
        self.micro_problems = {}
        self.micro_methods = {}
        self.paper_cards = []
        self.paper_index = {}
        self.paper_by_id = {}
        self.idea_by_id = {}
        self.papers_by_problem = defaultdict(list)
        self.papers_by_year = defaultdict(list)
        self._loaded = False

    def load_all(self):
        self.ideas = self._load_json("idea_opportunities_finegrained.json")
        self.micro_problems = self._load_json("micro_problem_clusters.json")
        self.micro_methods = self._load_json("micro_method_clusters.json")
        self.paper_cards = self._load_json("paper_micro_cards_index.json")
        self.paper_index = self._load_json("paper_index.json", fallback={"summary": None, "papers": {}})
        self._build_indices()
        self._loaded = True
        print(f"[DataLoader] Loaded {len(self.ideas)} ideas, {len(self.micro_problems)} problems, "
              f"{len(self.micro_methods)} methods, {len(self.paper_cards)} papers")

    def _build_indices(self):
        self.paper_by_id = {p["paper_id"]: p for p in self.paper_cards}
        self.idea_by_id = {i["idea_id"]: i for i in self.ideas}
        for p in self.paper_cards:
            year = p.get("year")
            if year:
                self.papers_by_year[int(year)].append(p["paper_id"])
            for pu in p.get("problem_units", []):
                self.papers_by_problem[pu.get("macro_problem_id", "unknown")].append(p["paper_id"])

    def _load_json(self, filename: str, fallback=None):
        filepath = self.data_root / filename
        if not filepath.exists():
            if fallback is not None:
                return fallback
            raise FileNotFoundError(f"Data file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def is_ready(self):
        return self._loaded

    def get_stats(self):
        return {
            "paper_count": len(self.paper_cards),
            "core_papers": sum(1 for p in self.paper_cards if p.get("task_scope", {}).get("is_core_video_moment_retrieval", False)),
            "adjacent_papers": sum(1 for p in self.paper_cards if p.get("task_scope", {}).get("is_adjacent_only", False)),
            "idea_count": len(self.ideas),
            "problem_count": len(self.micro_problems),
            "method_count": len(self.micro_methods),
        }
