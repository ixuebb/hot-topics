"""图谱相关路由"""
from flask import Blueprint, request

from middleware.response import success, error, make_pagination
from services.graph_service import build_forest_graph, build_root_graph

graph_bp = Blueprint("graph", __name__)


@graph_bp.route("/forest", methods=["GET"])
def get_forest():
    from app import data_loader
    result = build_forest_graph(data_loader)
    return success(data=result)


@graph_bp.route("/root", methods=["GET"])
def get_root():
    idea_id = request.args.get("idea", "").strip()
    if not idea_id:
        return error(400, "Missing required parameter: idea", "BAD_REQUEST", "Provide ?idea=FI001")
    from app import data_loader
    result = build_root_graph(data_loader, idea_id)
    if result is None:
        return error(404, f"Idea not found: {idea_id}", "NOT_FOUND", f"No idea with id '{idea_id}' in the database.")
    return success(data=result)
