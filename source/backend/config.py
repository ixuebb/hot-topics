"""Flask 应用配置"""
import os
from pathlib import Path


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    DATA_ROOT = Path(os.getenv("FLASK_DATA_ROOT", str(Path(__file__).resolve().parent.parent.parent / "data" / "idea_graph")))
    STATIC_DIR = Path(os.getenv("FLASK_STATIC_DIR", str(Path(__file__).resolve().parent.parent / "automation_platform" / "projects" / "vmr_idea_dashboard")))
    HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    PORT = int(os.getenv("FLASK_PORT", "5000"))
    RATE_LIMIT = int(os.getenv("FLASK_RATE_LIMIT", "100"))  # per minute
