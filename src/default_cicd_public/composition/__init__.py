"""Composition root - dependency injection and service wiring."""

from pathlib import Path

from default_cicd_public.adapters.filesystem.copier import FilesystemCopier
from default_cicd_public.adapters.filesystem.discovery import FilesystemDiscovery
from default_cicd_public.application.ports import (
    AppServices,
    CopyTemplates,
    DiscoverProjects,
    GetSourceGithubPath,
)


def _get_package_github_path() -> Path:
    """Get the .github/ path relative to this package's installation."""
    # Navigate from this file to the project root
    # This file is at: src/default_cicd_public/composition/__init__.py
    # Project root is: ../../.. from src/default_cicd_public/composition/
    package_dir = Path(__file__).parent.parent.parent.parent
    github_path = package_dir / ".github"

    if not github_path.exists():
        msg = f"Could not find .github/ directory at {github_path}"
        raise FileNotFoundError(msg)

    return github_path.resolve()


def build_production() -> AppServices:
    """Build the production service container."""
    return AppServices(
        discover_projects=FilesystemDiscovery(),
        copy_templates=FilesystemCopier(),
        get_source_github_path=_get_package_github_path,
    )


def build_testing(
    discover_projects: DiscoverProjects | None = None,
    copy_templates: CopyTemplates | None = None,
    get_source_github_path: GetSourceGithubPath | None = None,
) -> AppServices:
    """
    Build a testing service container with optional mock implementations.

    Args:
        discover_projects: Custom discovery implementation or None for default.
        copy_templates: Custom copier implementation or None for default.
        get_source_github_path: Custom source path getter or None for default.

    Returns:
        AppServices configured for testing.
    """
    return AppServices(
        discover_projects=discover_projects or FilesystemDiscovery(),
        copy_templates=copy_templates or FilesystemCopier(),
        get_source_github_path=get_source_github_path or _get_package_github_path,
    )
