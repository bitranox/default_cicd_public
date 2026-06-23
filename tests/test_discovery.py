"""Tests for project discovery."""

from pathlib import Path

import pytest

from default_cicd_public.adapters.filesystem.discovery import FilesystemDiscovery


class TestFilesystemDiscovery:
    """Tests for FilesystemDiscovery."""

    def test_discovers_project_with_marker(self, target_project_with_marker: Path) -> None:
        """Should discover a project that has the marker file."""
        discovery = FilesystemDiscovery()
        parent = target_project_with_marker.parent

        projects = list(discovery(parent))

        assert len(projects) == 1
        assert projects[0].root_path == target_project_with_marker
        assert projects[0].github_path == target_project_with_marker / ".github"

    def test_ignores_project_without_marker(self, target_project_without_marker: Path) -> None:
        """Should not discover a project without the marker file."""
        discovery = FilesystemDiscovery()

        projects = list(discovery(target_project_without_marker.parent))

        assert len(projects) == 0

    def test_discovers_multiple_projects(
        self, search_root_with_projects: tuple[Path, list[Path]]
    ) -> None:
        """Should discover all projects with the marker file."""
        root, expected_projects = search_root_with_projects
        discovery = FilesystemDiscovery()

        projects = list(discovery(root))

        found_roots = {p.root_path for p in projects}
        expected_roots = set(expected_projects)

        assert found_roots == expected_roots

    def test_skips_node_modules(self, search_root_with_projects: tuple[Path, list[Path]]) -> None:
        """Should skip node_modules directories."""
        root, _ = search_root_with_projects
        discovery = FilesystemDiscovery()

        projects = list(discovery(root))

        # Check relative paths from the search root, not full paths
        # (pytest temp paths may contain test names like "test_skips_node_modules")
        for project in projects:
            relative_path = project.root_path.relative_to(root)
            assert "node_modules" not in str(relative_path)

    def test_handles_permission_error(self, tmp_path: Path) -> None:
        """Should gracefully handle permission errors."""
        discovery = FilesystemDiscovery()

        # Create a non-existent path
        nonexistent = tmp_path / "nonexistent"

        # Should not raise, just return empty
        projects = list(discovery(nonexistent))
        assert projects == []

    def test_marker_file_property(self, target_project_with_marker: Path) -> None:
        """Should provide correct marker file path via property."""
        discovery = FilesystemDiscovery()

        projects = list(discovery(target_project_with_marker.parent))

        assert len(projects) == 1
        marker = projects[0].marker_file
        assert marker.exists()
        assert marker.name == "default_cicd_public.yml"


class TestSkippedDirectories:
    """Tests for directory skipping behavior."""

    @pytest.mark.parametrize(
        "skip_dir",
        [
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            ".tox",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
        ],
    )
    def test_skips_common_directories(self, tmp_path: Path, skip_dir: str) -> None:
        """Should skip common non-project directories."""
        # Create a project inside a skip directory
        project_in_skip = tmp_path / skip_dir / "hidden_project"
        (project_in_skip / ".github" / "workflows").mkdir(parents=True)
        (project_in_skip / ".github" / "workflows" / "default_cicd_public.yml").write_text(
            "name: CI\n"
        )

        discovery = FilesystemDiscovery()
        projects = list(discovery(tmp_path))

        # Should not find the project inside the skip directory
        assert len(projects) == 0
