"""Clipper Agency — automated short-form video content production."""

import click

from clipper_agency.config.loader import load_config


@click.group()
@click.option("--config", "-c", default=None, help="Path to config file")
@click.pass_context
def cli(ctx: click.Context, config: str | None) -> None:
    """Clipper Agency — automated video content production."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config) if config else {}


@cli.command()
@click.option("--topic", "-t", required=True, help="Topic for video generation")
@click.option("--niche", "-n", default="indonesian_artists", help="Niche profile to use")
@click.option("--template", "-m", default=None, help="Video template to use")
@click.pass_context
def run(ctx: click.Context, topic: str, niche: str, template: str | None) -> None:
    """Run the full pipeline for a topic."""
    click.echo(f"Topic: {topic}")
    click.echo(f"Niche: {niche}")
    click.echo("Pipeline execution coming soon...")


if __name__ == "__main__":
    cli()
