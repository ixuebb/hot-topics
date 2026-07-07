"""论文查询服务"""
from collections import defaultdict

from data_loader import DataLoader


class PaperNotFoundError(Exception):
    def __init__(self, paper_id):
        self.paper_id = paper_id
        super().__init__(f"Paper not found: {paper_id}")


def query_papers(loader: DataLoader, page=1, page_size=20, year=None, keyword=None, task_scope=None,
                 sort="year_desc"):
    papers = list(loader.paper_cards)

    if year:
        papers = [p for p in papers if p.get("year") == year]
    if keyword:
        kw = keyword.lower()
        papers = [p for p in papers if kw in (p.get("title", "") + " " + (p.get("abstract", "") or "")).lower()]
    if task_scope == "core":
        papers = [p for p in papers if p.get("task_scope", {}).get("is_core_video_moment_retrieval")]
    elif task_scope == "adjacent":
        papers = [p for p in papers if p.get("task_scope", {}).get("is_adjacent_only")]

    if sort == "year_desc":
        papers.sort(key=lambda p: -(p.get("year") or 0))
    elif sort == "year_asc":
        papers.sort(key=lambda p: p.get("year") or 0)
    elif sort == "title":
        papers.sort(key=lambda p: p.get("title", ""))

    total = len(papers)
    start = (page - 1) * page_size
    sliced = papers[start:start + page_size]

    results = []
    for p in sliced:
        results.append({
            "paper_id": p["paper_id"],
            "title": p.get("title", ""),
            "year": p.get("year"),
            "venue_or_source": p.get("venue_or_source", ""),
            "authors": p.get("authors", [])[:5],
            "task_scope": p.get("task_scope", {}),
            "datasets": p.get("datasets", []),
            "metrics": p.get("metrics", []),
            "problem_units_count": len(p.get("problem_units", [])),
            "method_units_count": len(p.get("method_units", [])),
            "abstract_snippet": (p.get("abstract", "") or "")[:200],
        })

    return results, total


def get_paper_detail(loader: DataLoader, paper_id: str):
    paper = loader.paper_by_id.get(paper_id)
    if not paper:
        raise PaperNotFoundError(paper_id)

    indexed = (loader.paper_index.get("papers", {}) or {}).get(paper_id, {})
    merged = {**indexed, **paper}

    related = find_related(loader, paper_id, limit=4)

    return {
        "paper_id": paper["paper_id"],
        "title": paper.get("title", ""),
        "year": paper.get("year"),
        "venue_or_source": paper.get("venue_or_source", ""),
        "authors": paper.get("authors", []),
        "abstract": merged.get("abstract", ""),
        "introduction": merged.get("introduction", ""),
        "task_scope": paper.get("task_scope", {}),
        "datasets": paper.get("datasets", []),
        "metrics": paper.get("metrics", []),
        "problem_units": paper.get("problem_units", []),
        "method_units": paper.get("method_units", []),
        "problem_method_links": paper.get("problem_method_links", []),
        "intro_motivation_chain": paper.get("intro_motivation_chain", {}),
        "novelty_axes": paper.get("novelty_axes", []),
        "figures": merged.get("figures", []),
        "tables": merged.get("tables", []),
        "related_papers": related,
    }


def find_related(loader: DataLoader, paper_id: str, limit=4):
    paper = loader.paper_by_id.get(paper_id)
    if not paper:
        return []

    target_units = set()
    for pu in paper.get("problem_units", []):
        target_units.add(pu.get("macro_problem_id", ""))
    for mu in paper.get("method_units", []):
        target_units.add(mu.get("macro_method_id", ""))

    if not target_units:
        return []

    scored = []
    for other in loader.paper_cards:
        if other["paper_id"] == paper_id:
            continue
        other_units = set()
        for pu in other.get("problem_units", []):
            other_units.add(pu.get("macro_problem_id", ""))
        for mu in other.get("method_units", []):
            other_units.add(mu.get("macro_method_id", ""))
        if not other_units:
            continue
        intersection = len(target_units & other_units)
        union = len(target_units | other_units)
        similarity = intersection / union if union > 0 else 0
        if similarity > 0:
            shared = list(target_units & other_units)
            scored.append((similarity, other, shared))

    scored.sort(key=lambda x: -x[0])
    results = []
    for sim, p, shared in scored[:limit]:
        results.append({
            "paper_id": p["paper_id"],
            "title": p.get("title", ""),
            "year": p.get("year"),
            "venue_or_source": p.get("venue_or_source", ""),
            "relation_type": "共享方法" if "EM" in str(shared) else "共享问题",
            "similarity": round(sim, 2),
            "shared_units": shared,
        })
    return results
