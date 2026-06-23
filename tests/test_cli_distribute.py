"""Tests for the distribute CLI command."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from default_cicd_public.adapters.cli.root import cli
from default_cicd_public.application.ports import AppServices
from default_cicd_public.composition import build_testing
from default_cicd_public.domain.models import CopyResult, CopyStatus, DiscoveredProject


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_services(
    source_github_dir: Path, search_root_with_projects: tuple[Path, list[Path]]
) -> AppServices:
    """Create mock services for testing."""
    _root, projects_with_marker = search_root_with_projects

    def mock_discover(search_root: Path) -> Iterator[DiscoveredProject]:
        for proj_path in projects_with_marker:
            yield DiscoveredProject(
                root_path=proj_path,
                github_path=proj_path / ".github",
            )

    def mock_copy(
        source_github_path: Path, target_project: DiscoveredProject, *, dry_run: bool = False
    ) -> CopyResult:
        return CopyResult(
            project=target_project,
            status=CopyStatus.DRY_RUN if dry_run else CopyStatus.SUCCESS,
            files_copied=[Path("workflows/default_cicd_public.yml")],
        )

    def mock_get_source() -> Path:
        return source_github_dir

    return build_testing(
        discover_projects=mock_discover,
        copy_templates=mock_copy,
        get_source_github_path=mock_get_source,
    )


class TestDistributeCommand:
    """Tests for the distribute command."""

    def test_help_output(self, cli_runner: CliRunner) -> None:
        """Should display help text."""
        result = cli_runner.invoke(cli, ["distribute", "--help"])

        assert result.exit_code == 0
        assert "Distribute CI/CD templates" in result.output
        assert "--dry-run" in result.output
        assert "--verbose" in result.output
        assert "--search-root" in result.output

    def test_dry_run_flag(
        self,
        cli_runner: CliRunner,
        mock_services: AppServices,
        search_root_with_projects: tuple[Path, list[Path]],
    ) -> None:
        """Should perform dry run when flag is set."""
        root, _ = search_root_with_projects

        result = cli_runner.invoke(
            cli,
            ["distribute", "--search-root", str(root), "--dry-run"],
            obj=mock_services,
        )

        assert result.exit_code == 0
        assert "dry_run" in result.output.lower() or "Would update" in result.output

    def test_verbose_output(
        self,
        cli_runner: CliRunner,
        mock_services: AppServices,
        search_root_with_projects: tuple[Path, list[Path]],
    ) -> None:
        """Should show detailed output when verbose flag is set."""
        root, _ = search_root_with_projects

        result = cli_runner.invoke(
            cli,
            ["distribute", "--search-root", str(root), "--dry-run", "--verbose"],
            obj=mock_services,
        )

        assert result.exit_code == 0
        assert "Source .github/" in result.output or "DRY RUN" in result.output

    def test_search_root_option(
        self,
        cli_runner: CliRunner,
        mock_services: AppServices,
        search_root_with_projects: tuple[Path, list[Path]],
    ) -> None:
        """Should use specified search root."""
        root, _ = search_root_with_projects

        result = cli_runner.invoke(
            cli,
            ["distribute", "--search-root", str(root), "--dry-run"],
            obj=mock_services,
        )

        assert result.exit_code == 0

    def test_no_projects_found(
        self, cli_runner: CliRunner, source_github_dir: Path, tmp_path: Path
    ) -> None:
        """Should handle case when no projects are found."""

        def mock_discover(search_root: Path) -> Iterator[DiscoveredProject]:
            return iter([])

        services = build_testing(
            discover_projects=mock_discover,
            get_source_github_path=lambda: source_github_dir,
        )

        result = cli_runner.invoke(
            cli,
            ["distribute", "--search-root", str(tmp_path), "--dry-run"],
            obj=services,
        )

        assert result.exit_code == 0
        assert "No target projects found" in result.output

    def test_excludes_self_project(self, cli_runner: CliRunner, source_github_dir: Path) -> None:
        """Should exclude the source project from distribution."""
        source_root = source_github_dir.parent

        # Create a discovery that returns the source project itself
        def mock_discover(search_root: Path) -> Iterator[DiscoveredProject]:
            yield DiscoveredProject(
                root_path=source_root,
                github_path=source_github_dir,
            )

        services = build_testing(
            discover_projects=mock_discover,
            get_source_github_path=lambda: source_github_dir,
        )

        result = cli_runner.invoke(
            cli,
            ["distribute", "--search-root", str(source_root), "--dry-run"],
            obj=services,
        )

        assert result.exit_code == 0
        # Should report no projects after filtering out self
        assert "No target projects found" in result.output

    def test_summary_table_displayed(
        self,
        cli_runner: CliRunner,
        mock_services: AppServices,
        search_root_with_projects: tuple[Path, list[Path]],
    ) -> None:
        """Should display a summary table at the end."""
        root, _ = search_root_with_projects

        result = cli_runner.invoke(
            cli,
            ["distribute", "--search-root", str(root), "--dry-run"],
            obj=mock_services,
        )

        assert result.exit_code == 0
        assert "Summary" in result.output or "projects" in result.output.lower()


class TestVersionOption:
    """Tests for version option."""

    def test_version_output(self, cli_runner: CliRunner) -> None:
        """Should display version information."""
        result = cli_runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output


@pytest.mark.local_only
class TestRealFilesystemIntegration:
    """Integration tests that use the real filesystem.

    These tests are marked with local_only and excluded from CI.
    """

    def test_discovers_real_projects(self, tmp_path: Path) -> None:
        """Integration test with real filesystem discovery."""
        from default_cicd_public.adapters.filesystem.copier import FilesystemCopier
        from default_cicd_public.adapters.filesystem.discovery import FilesystemDiscovery

        # Create source
        source_github = tmp_path / "source" / ".github"
        (source_github / "workflows").mkdir(parents=True)
        (source_github / "workflows" / "default_cicd_public.yml").write_text("name: CI\n")
        (source_github / "workflows" / "release.yml").write_text("name: Release\n")

        # Create target
        target = tmp_path / "target"
        (target / ".github" / "workflows").mkdir(parents=True)
        (target / ".github" / "workflows" / "default_cicd_public.yml").write_text("old\n")

        # Run with real implementations
        discovery = FilesystemDiscovery()
        copier = FilesystemCopier()

        projects = list(discovery(tmp_path))
        assert len(projects) == 2  # source and target

        # Copy to target (excluding source)
        target_project = next(p for p in projects if p.root_path == target)
        result = copier(source_github, target_project, dry_run=False)

        assert result.status == CopyStatus.SUCCESS
        assert (target / ".github" / "workflows" / "release.yml").exists()
