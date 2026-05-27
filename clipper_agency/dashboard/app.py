"""Flask dashboard app with basic auth and job listing."""

import os

from flask import Flask, abort, jsonify, render_template, request
from flask_wtf.csrf import CSRFError, CSRFProtect

from clipper_agency import __version__
from clipper_agency.config.loader import load_settings
from clipper_agency.dashboard.auth import requires_auth
from clipper_agency.db.connection import get_connection
from clipper_agency.db.queries import get_job, list_jobs
from clipper_agency.db.schema import initialize_schema

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("DASHBOARD_SECRET_KEY")


@app.before_request
def require_csrf_secret():
    """Fail closed for state-changing requests when CSRF config is missing."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not app.secret_key:
        abort(403)


CSRFProtect(app)


@app.errorhandler(CSRFError)
def handle_csrf_error(error: CSRFError):
    """Return JSON for CSRF validation failures."""
    return jsonify({"error": error.description}), 400


def _get_db():
    """Get a database connection with schema initialization."""
    settings = load_settings()
    conn = get_connection(str(settings.db_path))
    initialize_schema(conn)
    return conn


@app.route("/", methods=["GET"])
@requires_auth
def index():
    """Dashboard home page."""
    return render_template("index.html", version=__version__)


@app.route("/jobs", methods=["GET"])
@requires_auth
def jobs_page():
    """Jobs listing page."""
    conn = _get_db()
    jobs = list_jobs(conn, limit=50)
    return render_template("jobs.html", jobs=jobs, version=__version__)


@app.route("/api/jobs", methods=["GET"])
@requires_auth
def api_jobs():
    """JSON API: list recent jobs."""
    conn = _get_db()
    return jsonify(list_jobs(conn, limit=50))


@app.route("/api/jobs/<int:job_id>", methods=["GET"])
@requires_auth
def api_job_detail(job_id: int):
    """JSON API: get a specific job."""
    conn = _get_db()
    job = get_job(conn, job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(dict(job))


@app.route("/api/jobs", methods=["POST"])
@requires_auth
def api_create_job():
    """JSON API: create and run a new job."""
    data = request.get_json(silent=True)
    if not data or "topic" not in data:
        return jsonify({"error": "topic is required"}), 400

    from clipper_agency.orchestrator.engine import Orchestrator

    settings = load_settings()
    orch = Orchestrator(db_path=str(settings.db_path))
    result = orch.run_pipeline(
        topic=data["topic"],
        niche=data.get("niche", "indonesian_artists"),
        output_dir=str(settings.output_dir),
    )
    return jsonify(result)


def run_dashboard(host: str = "0.0.0.0", port: int = 5000) -> None:
    """Start the dashboard server (development only — use WSGI server in production)."""
    from werkzeug.serving import run_simple

    run_simple(host, port, app, use_debugger=False, use_reloader=False)
