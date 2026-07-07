"""系统状态路由"""
from flask import Blueprint, send_from_directory

from middleware.response import success

system_bp = Blueprint("system", __name__)


@system_bp.route("/status", methods=["GET"])
def get_status():
    from app import data_loader, start_time
    import time
    stats = data_loader.get_stats()
    stats["uptime_seconds"] = int(time.time() - start_time)
    stats["data_loaded"] = data_loader.is_ready()
    return success(data=stats)


@system_bp.route("/health", methods=["GET"])
def health():
    from app import data_loader
    return success(data={
        "status": "healthy" if data_loader.is_ready() else "loading",
        "data_loaded": data_loader.is_ready(),
    })
