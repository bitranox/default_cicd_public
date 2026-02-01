"""Pytest fixtures for default_cicd_public tests."""

from pathlib import Path

import pytest


@pytest.fixture
def source_github_dir(tmp_path: Path) -> Path:
    """Create a mock source .github directory with template files."""
    github_dir = tmp_path / "source" / ".github"
    workflows_dir = github_dir / "workflows"
    actions_dir = github_dir / "actions" / "extract-metadata"

    workflows_dir.mkdir(parents=True)
    actions_dir.mkdir(parents=True)

    # Create mock workflow files
    (workflows_dir / "default_cicd_public.yml").write_text("name: CI\n")
    (workflows_dir / "default_release_public.yml").write_text("name: Release\n")
    (workflows_dir / "codeql.yml").write_text("name: CodeQL\n")

    # Create mock dependabot
    (github_dir / "dependabot.yml").write_text("version: 2\n")

    # Create mock action
    (actions_dir / "action.yml").write_text("name: Extract metadata\n")

    return github_dir


@pytest.fixture
def target_project_with_marker(tmp_path: Path) -> Path:
    """Create a target project with the marker file."""
    project_dir = tmp_path / "target_project"
    workflows_dir = project_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)

    # Create the marker file
    (workflows_dir / "default_cicd_public.yml").write_text("name: Old CI\n")

    return project_dir


@pytest.fixture
def target_project_without_marker(tmp_path: Path) -> Path:
    """Create a target project without the marker file."""
    project_dir = tmp_path / "other_project"
    project_dir.mkdir(parents=True)
    (project_dir / "README.md").write_text("# Project\n")

    return project_dir


@pytest.fixture
def search_root_with_projects(tmp_path: Path) -> tuple[Path, list[Path]]:
    """Create a search root with multiple projects, some with markers."""
    root = tmp_path / "search_root"

    # Project 1: Has marker
    proj1 = root / "project1"
    (proj1 / ".github" / "workflows").mkdir(parents=True)
    (proj1 / ".github" / "workflows" / "default_cicd_public.yml").write_text("name: CI\n")

    # Project 2: Has marker (nested)
    proj2 = root / "org" / "project2"
    (proj2 / ".github" / "workflows").mkdir(parents=True)
    (proj2 / ".github" / "workflows" / "default_cicd_public.yml").write_text("name: CI\n")

    # Project 3: No marker
    proj3 = root / "project3"
    proj3.mkdir(parents=True)
    (proj3 / "README.md").write_text("# No marker\n")

    # Project 4: Has .github but different workflow
    proj4 = root / "project4"
    (proj4 / ".github" / "workflows").mkdir(parents=True)
    (proj4 / ".github" / "workflows" / "custom.yml").write_text("name: Custom\n")

    # node_modules should be skipped
    node_proj = root / "project1" / "node_modules" / "some_package"
    (node_proj / ".github" / "workflows").mkdir(parents=True)
    (node_proj / ".github" / "workflows" / "default_cicd_public.yml").write_text("name: CI\n")

    # Projects with markers
    projects_with_marker = [proj1, proj2]

    return root, projects_with_marker
