"""Clipper Agency — automated short-form video content production."""

import click

from clipper_agency.orchestrator.engine import Orchestrator


@click.group()
def cli() -> None:
    """Clipper Agency — automated video content production."""


@cli.command()
@click.option("--topic", "-t", required=True, help="Topic for video generation")
@click.option("--niche", "-n", default="indonesian_artists", help="Niche profile")
@click.option("--db", default="data/clipper.db", help="Database path")
@click.option("--output-dir", "-o", default="outputs", help="Output directory")
@click.option("--dry-run", is_flag=True, help="Validate input without running pipeline")
def run(topic: str, niche: str, db: str, output_dir: str, dry_run: bool) -> None:
    """Run the full pipeline for a topic."""
    click.echo(f"Clipper Agency — Topic: {topic}")
    click.echo(f"Niche: {niche}")

    if dry_run:
        click.echo("Dry run: input valid. Pipeline execution coming soon...")
        return

    click.echo("Starting pipeline...")
    orch = Orchestrator(db_path=db)
    result = orch.run_pipeline(topic=topic, niche=niche, output_dir=output_dir)

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
def jobs() -> None:
    """List recent jobs."""
    from clipper_agency.db.connection import get_connection
    from clipper_agency.db.queries import list_jobs

    conn = get_connection("data/clipper.db")
    for job in list_jobs(conn, limit=10):
        if job["status"] == "COMPLETED":
            status_icon = "\N{check mark}"
        elif job["status"] == "FAILED":
            status_icon = "\N{cross mark}"
        else:
            status_icon = "\N{hourglass}"
        click.echo(f"{status_icon} #{job['id']}: {job['topic']} — {job['status']} ({job['created_at']})")
