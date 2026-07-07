"""图谱构建服务"""
import math

from data_loader import DataLoader

SVG_W = 1600
SVG_H = 900


def clean_text(value):
    import re
    text = str(value or "").replace(r"#+\s*", "").replace(r"\s+", " ").replace(r"\s+([,.;:!?])", r"\1").strip()
    return text


def short_text(value, max_len=120):
    text = clean_text(value)
    return text[:max_len - 1] + "…" if len(text) > max_len else text


def build_forest_graph(loader: DataLoader):
    ideas = []
    for raw in loader.ideas:
        target = loader.micro_problems.get(raw.get("target_micro_problem_id", ""), {})
        method = loader.micro_methods.get(raw.get("source_micro_method_id", ""), {})
        ideas.append({
            "id": raw["idea_id"],
            "title": f'{short_text(method.get("name", ""), 34)} → {short_text(target.get("name", ""), 38)}',
            "summary": short_text(raw.get("technical_sketch", raw.get("candidate_idea", "")), 150),
            "score": float(raw.get("score", 0)),
            "risk": raw.get("risk_level", "medium"),
            "target_problem_id": raw.get("target_micro_problem_id", ""),
            "target_problem_name": target.get("name", ""),
            "source_method_id": raw.get("source_micro_method_id", ""),
            "source_method_name": method.get("name", ""),
            "problem_category": target.get("macro_problem_name", ""),
            "method_category": method.get("macro_method_name", ""),
            "featured": raw["idea_id"] == "FI001",
        })

    ideas.sort(key=lambda x: (not x["featured"], -x["score"]))

    min_score = min(i["score"] for i in ideas)
    max_score = max(i["score"] for i in ideas)

    groups = {}
    for idea in ideas:
        gid = idea["target_problem_id"] or "unknown"
        groups.setdefault(gid, []).append(idea)
    sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))

    cluster_radius = 390
    center = {"x": SVG_W / 2, "y": SVG_H / 2 + 42}
    nodes = []

    for gi, (gid, group) in enumerate(sorted_groups):
        angle = (math.pi * 2 * gi) / max(1, len(sorted_groups))
        gc = {
            "x": center["x"] + math.cos(angle) * cluster_radius,
            "y": center["y"] + math.sin(angle) * cluster_radius * 0.58,
        }
        group.sort(key=lambda x: -x["score"])
        for ii, idea in enumerate(group):
            local_angle = ii * 2.399963 + gi * 0.31
            local_radius = 28 + math.sqrt(ii) * 94 + ii * 2.5
            score_t = (idea["score"] - min_score) / max(0.01, max_score - min_score)
            r = 27 + score_t * 16 + (24 if idea["featured"] else 0)
            nodes.append({
                **idea,
                "radius": r,
                "x": center["x"] - 40 if idea["featured"] else max(90, min(SVG_W - 90, gc["x"] + math.cos(local_angle) * local_radius)),
                "y": center["y"] - 40 if idea["featured"] else max(150, min(SVG_H - 95, gc["y"] + math.sin(local_angle) * local_radius * 0.56)),
            })

    node_by_id = {n["id"]: n for n in nodes}
    links = []

    def add_links(key, ltype, strength):
        buckets = {}
        for n in nodes:
            v = n.get(key)
            if not v:
                continue
            buckets.setdefault(v, []).append(n)
        for members in buckets.values():
            sorted_m = sorted(members, key=lambda x: -x["score"])[:8]
            for i in range(len(sorted_m) - 1):
                links.append({
                    "id": f"{ltype}-{sorted_m[i]['id']}-{sorted_m[i + 1]['id']}",
                    "source": sorted_m[i]["id"],
                    "target": sorted_m[i + 1]["id"],
                    "type": ltype,
                    "strength": strength,
                })
            featured = next((n for n in sorted_m if n["featured"]), None)
            if featured:
                for n in sorted_m[:5]:
                    if n["id"] != featured["id"]:
                        links.append({
                            "id": f"{ltype}-{featured['id']}-{n['id']}",
                            "source": featured["id"],
                            "target": n["id"],
                            "type": ltype,
                            "strength": strength + 0.15,
                        })

    add_links("target_problem_id", "shared-problem", 0.82)
    add_links("source_method_id", "shared-method", 0.58)

    seen = set()
    unique_links = []
    for link in links:
        if link["id"] not in seen and node_by_id.get(link["source"]) and node_by_id.get(link["target"]):
            seen.add(link["id"])
            unique_links.append(link)

    return {
        "nodes": [{k: v for k, v in n.items() if k not in ("group",)} for n in nodes],
        "links": unique_links[:180],
        "stats": loader.get_stats(),
    }


def build_root_graph(loader: DataLoader, idea_id: str):
    idea_raw = loader.idea_by_id.get(idea_id)
    if not idea_raw:
        return None

    target = loader.micro_problems.get(idea_raw.get("target_micro_problem_id", ""), {})
    method = loader.micro_methods.get(idea_raw.get("source_micro_method_id", ""), {})

    idea_title = short_text(f'{short_text(method.get("name", ""), 34)} → {short_text(target.get("name", ""), 38)}', 60)

    nodes = [
        {"id": "idea", "type": "idea", "label": idea_title, "detail": idea_title, "x": 800, "y": 172, "confidence": 88, "size": 1.22},
        {"id": "trunk", "type": "trunk", "label": "把可迁移机制接到目标失败模式上", "detail": short_text(idea_raw.get("technical_sketch", ""), 120), "x": 800, "y": 292, "confidence": 84, "size": 1.1},
        {"id": "p_target", "type": "problem", "label": short_text(target.get("name", idea_raw.get("target_micro_problem", "")), 46), "detail": target.get("canonical_question", ""), "x": 470, "y": 425, "confidence": 82, "size": 1.0},
        {"id": "p_gap", "type": "problem", "label": "当前解决方案仍未充分覆盖", "detail": idea_raw.get("why_currently_underused", ""), "x": 800, "y": 425, "confidence": 76, "size": 1.0},
        {"id": "p_transfer", "type": "problem", "label": "跨问题迁移窗口", "detail": idea_raw.get("shared_failure_mode", ""), "x": 1130, "y": 425, "confidence": 82 if idea_raw.get("is_cross_task_transfer") else 68, "size": 1.0},
        {"id": "f_mode", "type": "failure", "label": short_text(target.get("failure_mode", idea_raw.get("shared_failure_mode", "")), 42), "detail": target.get("root_cause", ""), "x": 480, "y": 565, "confidence": 80, "size": 1.0},
        {"id": "f_root", "type": "failure", "label": short_text(target.get("root_cause", "根因") if target.get("root_cause") else idea_raw.get("shared_failure_mode", ""), 42), "detail": idea_raw.get("shared_failure_mode", ""), "x": 800, "y": 565, "confidence": 76, "size": 1.0},
        {"id": "f_underuse", "type": "failure", "label": "已有机制尚未被直接使用", "detail": idea_raw.get("why_currently_underused", ""), "x": 1120, "y": 565, "confidence": 78, "size": 1.0},
        {"id": "m_source", "type": "method", "label": short_text(method.get("name", idea_raw.get("source_micro_method", "")), 42), "detail": method.get("core_mechanism", ""), "x": 520, "y": 715, "confidence": 82, "size": 1.0},
        {"id": "m_transfer", "type": "method", "label": "可迁移机制", "detail": idea_raw.get("transferable_mechanism", ""), "x": 820, "y": 715, "confidence": 84, "size": 1.0},
        {"id": "m_components", "type": "method", "label": short_text(" / ".join((method.get("components", []) or [])[:4]) or "方法组件", 42), "detail": " / ".join(method.get("capability_facets", []) or []), "x": 1120, "y": 715, "confidence": 74, "size": 1.0},
    ]

    paper_pool = idea_raw.get("target_papers", []) + idea_raw.get("source_papers", [])
    seen_ids = set()
    unique_papers = []
    for p in paper_pool:
        pid = p.get("paper_id", "")
        if pid not in seen_ids:
            seen_ids.add(pid)
            unique_papers.append(p)
    unique_papers = unique_papers[:7]

    for idx, paper in enumerate(unique_papers):
        nodes.append({
            "id": f"paper_{idx}", "type": "paper",
            "label": short_text(paper.get("title", "Untitled"), 48),
            "detail": f'{paper.get("year", "")} · {paper.get("venue_or_source", "")}',
            "x": 180 + idx * 205, "y": 840,
            "confidence": 62 + min(26, len(paper.get("evidence", [])) * 8),
            "size": 1.0, "paper_id": paper.get("paper_id", ""),
            "evidence": paper.get("evidence", []),
        })

    edges = [
        {"id": "idea->trunk", "source": "idea", "target": "trunk", "type": "claim", "strength": 0.95, "label": "核心主张"},
        {"id": "trunk->p_target", "source": "trunk", "target": "p_target", "type": "root", "strength": 0.84, "label": "目标缺口"},
        {"id": "trunk->p_gap", "source": "trunk", "target": "p_gap", "type": "root", "strength": 0.76, "label": "未被覆盖"},
        {"id": "trunk->p_transfer", "source": "trunk", "target": "p_transfer", "type": "root", "strength": 0.84 if idea_raw.get("is_cross_task_transfer") else 0.66, "label": "迁移窗口"},
        {"id": "p_target->f_mode", "source": "p_target", "target": "f_mode", "type": "cause", "strength": 0.80, "label": "具体失败"},
        {"id": "p_gap->f_underuse", "source": "p_gap", "target": "f_underuse", "type": "cause", "strength": 0.78, "label": "直接连接少"},
        {"id": "p_transfer->f_root", "source": "p_transfer", "target": "f_root", "type": "cross-cause", "strength": 0.74, "label": "共享机制"},
        {"id": "f_mode->m_source", "source": "f_mode", "target": "m_source", "type": "transfer", "strength": 0.78, "label": "来源方法"},
        {"id": "f_root->m_transfer", "source": "f_root", "target": "m_transfer", "type": "transfer", "strength": 0.84, "label": "机制迁移"},
        {"id": "f_underuse->m_components", "source": "f_underuse", "target": "m_components", "type": "transfer", "strength": 0.72, "label": "组件补位"},
        {"id": "m_source->m_transfer", "source": "m_source", "target": "m_transfer", "type": "shared-mechanism", "strength": 0.62, "label": "共享机制"},
        {"id": "m_transfer->m_components", "source": "m_transfer", "target": "m_components", "type": "shared-mechanism", "strength": 0.58, "label": "组件化"},
    ]

    for idx in range(len(unique_papers)):
        target_node = "p_target" if idx < 2 else "m_source" if idx < 5 else "m_transfer"
        edges.append({"id": f"{target_node}->paper_{idx}", "source": target_node, "target": f"paper_{idx}", "type": "evidence", "strength": 0.62, "label": "论文证据"})

    return {"idea": {
        "id": idea_raw["idea_id"], "title": idea_title,
        "score": float(idea_raw.get("score", 0)), "risk": idea_raw.get("risk_level", "medium"),
        "trunk": short_text(idea_raw.get("technical_sketch", ""), 120),
        "datasets": "Charades-STA / QVHighlights / ActivityNet Captions",
    }, "nodes": nodes, "edges": edges}
