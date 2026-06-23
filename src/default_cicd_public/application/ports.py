"""Port definitions (protocols) for the application layer."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from default_cicd_public.domain.models import CopyResult, DiscoveredProject


class DiscoverProjects(Protocol):
    """Protocol for discovering projects with the marker file."""

    def __call__(self, search_root: Path) -> Iterator[DiscoveredProject]:
        """
        Discover projects containing the marker workflow file.

        Args:
            search_root: The root directory to start searching from.

        Yields:
            DiscoveredProject instances for each matching project.
        """
        ...


class CopyTemplates(Protocol):
    """Protocol for copying templates to a target project."""

    def __call__(
        self,
        source_github_path: Path,
        target_project: DiscoveredProject,
        *,
        dry_run: bool = False,
    ) -> CopyResult:
        """
        Copy all files from source .github/ to target project's .github/.

        Args:
            source_github_path: Path to the source .github/ directory.
            target_project: The target project to copy templates to.
            dry_run: If True, simulate the copy without making changes.

        Returns:
            CopyResult with the status and details of the operation.
        """
        ...


class GetSourceGithubPath(Protocol):
    """Protocol for getting the source .github/ directory path."""

    def __call__(self) -> Path:
        """
        Get the path to our own .github/ directory.

        Returns:
            Path to the source .github/ directory.
        """
        ...


@dataclass
class AppServices:
    """Container for all application services (ports)."""

    discover_projects: DiscoverProjects
    copy_templates: CopyTemplates
    get_source_github_path: GetSourceGithubPath
