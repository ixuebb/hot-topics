"""统一响应格式包装"""
from flask import jsonify


def success(data=None, message="success", code=200, pagination=None):
    body = {"code": code, "message": message, "data": data if data is not None else {}}
    if pagination:
        body["pagination"] = {
            "page": pagination.get("page", 1),
            "page_size": pagination.get("page_size", 20),
            "total": pagination.get("total", 0),
            "total_pages": pagination.get("total_pages", 1),
        }
    return jsonify(body), code


def error(code, message, error_type=None, detail=None):
    body = {"code": code, "message": message, "data": None}
    if error_type or detail:
        body["error"] = {}
        if error_type:
            body["error"]["type"] = error_type
        if detail:
            body["error"]["detail"] = detail
    return jsonify(body), code


def make_pagination(page, page_size, total):
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }
