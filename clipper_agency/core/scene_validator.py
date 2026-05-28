"""Scene validation — checks file existence, size, and basic validity."""
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SceneValidationResult:
    path: str
    valid: bool
    issues: list[str] = field(default_factory=list)


class SceneValidator:
    """Validates media scene files for basic correctness."""

    @staticmethod
    def validate(path: str, min_bytes: int = 1024) -> SceneValidationResult:
        """Validate a single scene file.

        Checks: existence, non-empty, minimum file size.
        Returns SceneValidationResult with valid=False and issues list on failure.
        """
        issues: list[str] = []

        if not os.path.isfile(path):
            issues.append(f"Scene file not found: {path}")
        elif os.path.getsize(path) == 0:
            issues.append(f"Scene file is empty (zero bytes): {path}")
        elif os.path.getsize(path) < min_bytes:
            issues.append(
                f"Scene file too small ({os.path.getsize(path)} bytes, min {min_bytes}): {path}"
            )

        return SceneValidationResult(
            path=path,
            valid=len(issues) == 0,
            issues=issues,
        )

    @staticmethod
    def validate_all(
        paths: list[str], min_bytes: int = 1024
    ) -> list[SceneValidationResult]:
        """Validate multiple scenes. Returns list of results."""
        return [SceneValidator.validate(p, min_bytes=min_bytes) for p in paths]
