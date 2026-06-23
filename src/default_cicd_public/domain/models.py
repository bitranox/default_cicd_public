"""Domain models for CI/CD template distribution."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class CopyStatus(Enum):
    """Status of a copy operation."""

    SUCCESS = "success"
    SKIPPED_SELF = "skipped_self"
    PERMISSION_DENIED = "permission_denied"
    ERROR = "error"
    DRY_RUN = "dry_run"


@dataclass(frozen=True)
class DiscoveredProject:
    """A project discovered by scanning the filesystem."""

    root_path: Path
    github_path: Path

    @property
    def marker_file(self) -> Path:
        """Return the path to the marker workflow file."""
        return self.github_path / "workflows" / "default_cicd_public.yml"


@dataclass
class CopyResult:
    """Result of copying templates to a project."""

    project: DiscoveredProject
    status: CopyStatus
    files_copied: list[Path] = field(default_factory=lambda: [])
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        """Return True if the operation succeeded or was a dry run."""
        return self.status in (CopyStatus.SUCCESS, CopyStatus.DRY_RUN)
