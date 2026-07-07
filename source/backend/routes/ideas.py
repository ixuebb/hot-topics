"""Idea相关路由"""
from flask import Blueprint, request

from middleware.response import success, error, make_pagination

ideas_bp = Blueprint("ideas", __name__)


@ideas_bp.route("", methods=["GET"])
def list_ideas():
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    sort = request.args.get("sort", "score_desc", type=str)
    risk_level = request.args.get("risk_level", None, type=str)

    if page < 1:
        return error(400, "page must be >= 1", "BAD_REQUEST")
    if page_size < 1 or page_size > 100:
        return error(400, "page_size must be between 1 and 100", "BAD_REQUEST")

    from app import data_loader
    ideas = list(data_loader.ideas)
    if risk_level:
        ideas = [i for i in ideas if i.get("risk_level") == risk_level]

    if sort == "score_desc":
        ideas.sort(key=lambda i: -float(i.get("score", 0)))
    elif sort == "score_asc":
        ideas.sort(key=lambda i: float(i.get("score", 0)))
    elif sort == "novelty_desc":
        ideas.sort(key=lambda i: -float(i.get("score", 0)))

    total = len(ideas)
    start = (page - 1) * page_size
    sliced = ideas[start:start + page_size]

    results = []
    for raw in sliced:
        target = data_loader.micro_problems.get(raw.get("target_micro_problem_id", ""), {})
        method = data_loader.micro_methods.get(raw.get("source_micro_method_id", ""), {})
        results.append({
            "idea_id": raw["idea_id"],
            "title": f'{method.get("name", raw.get("source_micro_method", ""))} → {target.get("name", raw.get("target_micro_problem", ""))}',
            "score": float(raw.get("score", 0)),
            "risk_level": raw.get("risk_level", "medium"),
            "target_problem": target.get("name", ""),
            "source_method": method.get("name", ""),
            "is_cross_task_transfer": raw.get("is_cross_task_transfer", False),
            "summary": (raw.get("technical_sketch", "") or raw.get("candidate_idea", ""))[:150],
        })

    return success(data=results, pagination=make_pagination(page, page_size, total))


@ideas_bp.route("/<idea_id>", methods=["GET"])
def get_idea(idea_id):
    from app import data_loader
    raw = data_loader.idea_by_id.get(idea_id)
    if not raw:
        return error(404, f"Idea not found: {idea_id}", "NOT_FOUND", f"No idea with id '{idea_id}' in the database.")
    return success(data=dict(raw))
