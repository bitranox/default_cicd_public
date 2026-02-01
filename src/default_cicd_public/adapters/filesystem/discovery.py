"""Filesystem-based project discovery."""

from collections.abc import Iterator
from pathlib import Path

from default_cicd_public.domain.models import DiscoveredProject

# Directories to skip during traversal
SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".env",
        "env",
        ".tox",
        ".nox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".cache",
        "dist",
        "build",
        ".eggs",
        "*.egg-info",
        "site-packages",
        ".hg",
        ".svn",
        "CVS",
    }
)

MARKER_FILE = Path(".github") / "workflows" / "default_cicd_public.yml"


class FilesystemDiscovery:
    """Discovers projects containing the marker workflow file."""

    def __call__(self, search_root: Path) -> Iterator[DiscoveredProject]:
        """
        Recursively search for projects containing the marker file.

        Args:
            search_root: The root directory to start searching from.

        Yields:
            DiscoveredProject instances for each matching project.
        """
        yield from self._walk(search_root)

    def _walk(self, directory: Path) -> Iterator[DiscoveredProject]:
        """Recursively walk the directory tree."""
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return
        except OSError:
            return

        # Check if this directory contains the marker file
        marker_path = directory / MARKER_FILE
        try:
            has_marker = marker_path.exists() and marker_path.is_file()
        except OSError:
            has_marker = False

        if has_marker:
            github_path = directory / ".github"
            yield DiscoveredProject(root_path=directory, github_path=github_path)

        # Recurse into subdirectories
        for entry in entries:
            try:
                is_directory = entry.is_dir()
            except OSError:
                # Stale file handle or other filesystem errors
                continue

            if not is_directory:
                continue

            # Skip common non-project directories
            if entry.name in SKIP_DIRS:
                continue

            # Skip hidden directories (except .github which we already checked)
            if entry.name.startswith(".") and entry.name != ".github":
                continue

            # Skip if matches a pattern (e.g., *.egg-info)
            if any(entry.name.endswith(skip.lstrip("*")) for skip in SKIP_DIRS if "*" in skip):
                continue

            yield from self._walk(entry)
