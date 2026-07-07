"""趋势与系统路由"""
from flask import Blueprint, request

from middleware.response import success
from services.trend_service import get_hot_topics, get_temporal_trends

trends_bp = Blueprint("trends", __name__)


@trends_bp.route("/hot-topics", methods=["GET"])
def hot_topics():
    limit = request.args.get("limit", 10, type=int)
    year = request.args.get("year", None, type=int)
    from app import data_loader
    topics = get_hot_topics(data_loader, limit=limit, year=year)
    return success(data=topics)


@trends_bp.route("/temporal", methods=["GET"])
def temporal():
    start_year = request.args.get("start_year", 2021, type=int)
    end_year = request.args.get("end_year", 2026, type=int)
    from app import data_loader
    result = get_temporal_trends(data_loader, start_year, end_year)
    return success(data=result)
