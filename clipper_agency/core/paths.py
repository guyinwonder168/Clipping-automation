"""Shared path conventions for cache and output directory layout."""

import os
from pathlib import Path


def job_output_dir(output_dir: str | Path, job_id: int) -> str:
    """Base output directory for a job.

    Used by all agents to construct per-job file paths.
    """
    return f"{output_dir}/job_{job_id}"


def research_cache_dir(output_dir: str | Path, job_id: int) -> str:
    """Cache directory for Researcher API responses and LLM synthesis."""
    return f"{job_output_dir(output_dir, job_id)}/research"


def scrapecreators_cache_file(output_dir: str | Path, job_id: int) -> str:
    """Cached structured ScrapeCreators search results (JSON)."""
    return f"{research_cache_dir(output_dir, job_id)}/scrapecreators.json"


def firecrawl_cache_file(output_dir: str | Path, job_id: int) -> str:
    """Cached Firecrawl search results (JSON)."""
    return f"{research_cache_dir(output_dir, job_id)}/firecrawl.json"


def research_brief_cache_file(output_dir: str | Path, job_id: int) -> str:
    """Cached LLM-synthesized research brief (JSON)."""
    return f"{research_cache_dir(output_dir, job_id)}/research_brief.json"


def ensure_research_cache_dir(output_dir: str | Path, job_id: int) -> str:
    """Create the research cache directory if it doesn't exist.

    Returns the cache directory path.
    """
    path = research_cache_dir(output_dir, job_id)
    os.makedirs(path, exist_ok=True)
    return path
