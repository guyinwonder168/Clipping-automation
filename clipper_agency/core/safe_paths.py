"""Safe filesystem path resolution helpers."""

from pathlib import Path


def resolve_existing_file_under(
    base_dir: str | Path,
    candidate: str | Path,
) -> Path | None:
    """Return a resolved existing file only when it is inside ``base_dir``.

    Relative candidates are resolved from ``base_dir``. Absolute candidates are
    accepted only if their canonical path is still contained by ``base_dir``.
    This prevents parent traversal and string-prefix boundary mistakes.
    """
    if not base_dir or not candidate:
        return None

    try:
        base = Path(base_dir).resolve()
        candidate_path = Path(candidate)
        resolved = (
            candidate_path.resolve()
            if candidate_path.is_absolute()
            else (base / candidate_path).resolve()
        )
        resolved.relative_to(base)
    except (OSError, RuntimeError, TypeError, ValueError):
        return None

    if not resolved.is_file():
        return None
    return resolved
