"""VMR Idea Graph — Flask API Gateway"""
import sys
import time
from pathlib import Path

from flask import Flask, g, request, send_from_directory
from flask_cors import CORS

from config import Config

# Add backend dir to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_loader import DataLoader

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Data loader (startup) ──
data_loader: DataLoader = None
start_time = time.time()


def init_data():
    global data_loader
    cfg = app.config
    data_root = cfg.get("DATA_ROOT", Config.DATA_ROOT)
    data_loader = DataLoader(data_root)
    try:
        data_loader.load_all()
        print(f"[Init] Data loaded from {data_root}")
    except FileNotFoundError as e:
        print(f"[WARN] Data not found at {data_root}: {e}")
        print("[WARN] API will return 503 until data is available.")


# ── Request logging middleware ──
@app.before_request
def before_request():
    g.start_time = time.time()


@app.after_request
def after_request(response):
    duration_ms = (time.time() - g.start_time) * 1000
    app.logger.info(f"{request.method} {request.path} → {response.status_code} ({duration_ms:.0f}ms)")
    return response


# ── Register API routes ──
from routes.graph import graph_bp
from routes.papers import papers_bp
from routes.ideas import ideas_bp
from routes.trends import trends_bp
from routes.system import system_bp

app.register_blueprint(graph_bp, url_prefix="/api/graph")
app.register_blueprint(papers_bp, url_prefix="/api/papers")
app.register_blueprint(ideas_bp, url_prefix="/api/ideas")
app.register_blueprint(trends_bp, url_prefix="/api/trends")
app.register_blueprint(system_bp, url_prefix="/api")


# ── Static file serving (production mode) ──
@app.route("/")
def serve_index():
    static_dir = str(app.config.get("STATIC_DIR", Config.STATIC_DIR))
    return send_from_directory(static_dir, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    static_dir = str(app.config.get("STATIC_DIR", Config.STATIC_DIR))
    if filename.endswith((".json", ".js", ".css", ".html", ".png", ".jpg", ".jpeg", ".svg", ".ico")):
        return send_from_directory(static_dir, filename)
    return send_from_directory(static_dir, filename)


# ── Error handlers ──
@app.errorhandler(404)
def handle_404(e):
    return {"code": 404, "message": "Endpoint not found", "data": None, "error": {"type": "NOT_FOUND"}}, 404


@app.errorhandler(500)
def handle_500(e):
    app.logger.exception("Internal error")
    return {"code": 500, "message": "Internal server error", "data": None, "error": {"type": "INTERNAL_ERROR"}}, 500


# ── Main ──
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="VMR Idea Graph API Server")
    parser.add_argument("--port", type=int, default=Config.PORT, help="Server port")
    parser.add_argument("--data-root", type=str, default=str(Config.DATA_ROOT), help="Path to idea_graph data")
    parser.add_argument("--debug", action="store_true", default=Config.DEBUG, help="Debug mode")
    args = parser.parse_args()

    app.config["DATA_ROOT"] = Path(args.data_root)
    app.config["DEBUG"] = args.debug

    init_data()
    print(f"[Start] Listening on http://127.0.0.1:{args.port}/")
    print(f"[Start] API at http://127.0.0.1:{args.port}/api/")
    app.run(host=Config.HOST, port=args.port, debug=args.debug)
