"""Flask dashboard app with basic auth and job listing."""

from flask import Flask, jsonify, render_template, request

from clipper_agency.dashboard.auth import requires_auth
from clipper_agency.db.connection import get_connection
from clipper_agency.db.queries import get_job, list_jobs
from clipper_agency.db.schema import initialize_schema

app = Flask(__name__, template_folder="templates")


def _get_db():
    """Get a database connection with schema initialization."""
    conn = get_connection("data/clipper.db")
    initialize_schema(conn)
    return conn


@app.route("/")
@requires_auth
def index():
    """Dashboard home page."""
    return render_template("index.html")


@app.route("/jobs")
@requires_auth
def jobs_page():
    """Jobs listing page."""
    conn = _get_db()
    jobs = list_jobs(conn, limit=50)
    return render_template("jobs.html", jobs=jobs)


@app.route("/api/jobs")
@requires_auth
def api_jobs():
    """JSON API: list recent jobs."""
    conn = _get_db()
    return jsonify(list_jobs(conn, limit=50))


@app.route("/api/jobs/<int:job_id>")
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

    orch = Orchestrator()
    result = orch.run_pipeline(
        topic=data["topic"],
        niche=data.get("niche", "indonesian_artists"),
    )
    return jsonify(result)


def run_dashboard(host: str = "0.0.0.0", port: int = 5000) -> None:
    """Start the dashboard server (development only — use WSGI server in production)."""
    from werkzeug.serving import run_simple

    run_simple(host, port, app, use_debugger=False, use_reloader=False)
