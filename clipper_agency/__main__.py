"""Clipper Agency — automated short-form video content production."""

import click
from dotenv import load_dotenv

from clipper_agency import __version__
from clipper_agency.config.loader import load_settings
from clipper_agency.orchestrator.engine import Orchestrator

# Load .env into os.environ before any service reads env vars.
load_dotenv()


def _print_version(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"Clipper Agency v{__version__}")
    ctx.exit()


def _db_path() -> str:
    """Read database path from settings (env/.env) with fallback."""
    settings = load_settings()
    return str(settings.db_path)


def _output_dir() -> str:
    """Read output directory from settings (env/.env) with fallback."""
    settings = load_settings()
    return str(settings.output_dir)


@click.group()
@click.option("--version", is_flag=True, callback=_print_version, expose_value=False, is_eager=True, help="Show version and exit")
def cli() -> None:
    """Clipper Agency — automated video content production."""


@cli.command()
@click.option("--topic", "-t", required=True, help="Topic for video generation")
@click.option("--niche", "-n", default="indonesian_artists", help="Niche profile")
@click.option("--db", default=None, help="Database path (default: from .env or data/clipper.db)")
@click.option("--output-dir", "-o", default=None, help="Output directory (default: from .env or outputs)")
@click.option("--dry-run", is_flag=True, help="Validate input without running pipeline")
def run(topic: str, niche: str, db: str | None, output_dir: str | None, dry_run: bool) -> None:
    """Run the full pipeline for a topic."""
    click.echo(f"Clipper Agency — Topic: {topic}")
    click.echo(f"Niche: {niche}")

    if dry_run:
        click.echo("Dry run: input valid. Pipeline execution coming soon...")
        return

    resolved_db = db or _db_path()
    resolved_output = output_dir or _output_dir()

    click.echo("Starting pipeline...")
    orch = Orchestrator(db_path=resolved_db)
    result = orch.run_pipeline(topic=topic, niche=niche, output_dir=resolved_output)

    if result["status"] == "completed":
        click.echo(f"\N{check mark} Pipeline completed! Job ID: {result['job_id']}")
        out = result.get("output", {})
        if out.get("video_path"):
            click.echo(f"  Video: {out['video_path']}")
    else:
        reason = result.get("reason") or result.get("error") or "Unknown error"
        failed_at = result.get("failed_at", "")
        loc = f" at {failed_at}" if failed_at else ""
        click.echo(f"\N{cross mark} Pipeline failed{loc}: {reason}")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=5000, help="Port to bind")
def dashboard(host: str, port: int) -> None:
    """Start the web dashboard."""
    from clipper_agency.dashboard.app import run_dashboard

    click.echo(f"Dashboard starting at http://{host}:{port}")
    run_dashboard(host=host, port=port)


@cli.command()
def jobs() -> None:
    """List recent jobs."""
    from clipper_agency.db.connection import get_connection
    from clipper_agency.db.queries import list_jobs

    conn = get_connection(_db_path())
    for job in list_jobs(conn, limit=10):
        if job["status"] == "COMPLETED":
            status_icon = "\N{check mark}"
        elif job["status"] == "FAILED":
            status_icon = "\N{cross mark}"
        else:
            status_icon = "\N{hourglass}"
        click.echo(f"{status_icon} #{job['id']}: {job['topic']} — {job['status']} ({job['created_at']})")


if __name__ == "__main__":
    cli()
