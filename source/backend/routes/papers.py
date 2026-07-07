"""论文相关路由"""
from flask import Blueprint, request

from middleware.response import success, error, make_pagination
from services.paper_service import query_papers, get_paper_detail, find_related, PaperNotFoundError

papers_bp = Blueprint("papers", __name__)


@papers_bp.route("", methods=["GET"])
def list_papers():
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    year = request.args.get("year", None, type=int)
    keyword = request.args.get("keyword", None, type=str)
    task_scope = request.args.get("task_scope", None, type=str)
    sort = request.args.get("sort", "year_desc", type=str)

    if page < 1:
        return error(400, "page must be >= 1", "BAD_REQUEST")
    if page_size < 1 or page_size > 100:
        return error(400, "page_size must be between 1 and 100", "BAD_REQUEST")

    from app import data_loader
    papers, total = query_papers(data_loader, page, page_size, year, keyword, task_scope, sort)
    return success(data=papers, pagination=make_pagination(page, page_size, total))


@papers_bp.route("/<paper_id>", methods=["GET"])
def get_paper(paper_id):
    from app import data_loader
    try:
        paper = get_paper_detail(data_loader, paper_id)
        return success(data=paper)
    except PaperNotFoundError as e:
        return error(404, str(e), "NOT_FOUND", f"No paper with id '{paper_id}' in the library.")


@papers_bp.route("/<paper_id>/related", methods=["GET"])
def get_related(paper_id):
    limit = request.args.get("limit", 4, type=int)
    from app import data_loader
    related = find_related(data_loader, paper_id, limit)
    return success(data=related)
