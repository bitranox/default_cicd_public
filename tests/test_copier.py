"""Tests for template copier."""

from pathlib import Path

from default_cicd_public.adapters.filesystem.copier import FilesystemCopier
from default_cicd_public.domain.models import CopyStatus, DiscoveredProject


class TestFilesystemCopier:
    """Tests for FilesystemCopier."""

    def test_copies_files_successfully(
        self, source_github_dir: Path, target_project_with_marker: Path
    ) -> None:
        """Should copy all files from source to target."""
        copier = FilesystemCopier()
        target_github = target_project_with_marker / ".github"
        project = DiscoveredProject(
            root_path=target_project_with_marker,
            github_path=target_github,
        )

        result = copier(source_github_dir, project, dry_run=False)

        assert result.status == CopyStatus.SUCCESS
        assert len(result.files_copied) > 0
        assert result.error_message is None

        # Verify files were actually copied
        assert (target_github / "workflows" / "default_cicd_public.yml").exists()
        assert (target_github / "workflows" / "default_release_public.yml").exists()
        assert (target_github / "workflows" / "codeql.yml").exists()
        assert (target_github / "dependabot.yml").exists()
        assert (target_github / "actions" / "extract-metadata" / "action.yml").exists()

    def test_dry_run_does_not_modify(
        self, source_github_dir: Path, target_project_with_marker: Path
    ) -> None:
        """Dry run should not modify any files."""
        copier = FilesystemCopier()
        target_github = target_project_with_marker / ".github"
        project = DiscoveredProject(
            root_path=target_project_with_marker,
            github_path=target_github,
        )

        # Read original content
        original_content = (target_github / "workflows" / "default_cicd_public.yml").read_text()

        result = copier(source_github_dir, project, dry_run=True)

        assert result.status == CopyStatus.DRY_RUN
        assert len(result.files_copied) > 0

        # Verify file was NOT modified
        current_content = (target_github / "workflows" / "default_cicd_public.yml").read_text()
        assert current_content == original_content

    def test_creates_missing_directories(self, source_github_dir: Path, tmp_path: Path) -> None:
        """Should create missing directories in target."""
        copier = FilesystemCopier()
        target_project = tmp_path / "new_project"
        target_project.mkdir()
        target_github = target_project / ".github"
        # Don't create .github - let copier handle it

        project = DiscoveredProject(
            root_path=target_project,
            github_path=target_github,
        )

        result = copier(source_github_dir, project, dry_run=False)

        assert result.status == CopyStatus.SUCCESS
        assert target_github.exists()
        assert (target_github / "workflows").exists()
        assert (target_github / "actions" / "extract-metadata").exists()

    def test_overwrites_existing_files(
        self, source_github_dir: Path, target_project_with_marker: Path
    ) -> None:
        """Should overwrite existing files in target."""
        copier = FilesystemCopier()
        target_github = target_project_with_marker / ".github"
        project = DiscoveredProject(
            root_path=target_project_with_marker,
            github_path=target_github,
        )

        # Verify original content is different
        original = (target_github / "workflows" / "default_cicd_public.yml").read_text()
        source_content = (source_github_dir / "workflows" / "default_cicd_public.yml").read_text()
        assert original != source_content

        result = copier(source_github_dir, project, dry_run=False)

        assert result.status == CopyStatus.SUCCESS

        # Verify content was replaced
        new_content = (target_github / "workflows" / "default_cicd_public.yml").read_text()
        assert new_content == source_content

    def test_returns_relative_paths(
        self, source_github_dir: Path, target_project_with_marker: Path
    ) -> None:
        """Should return relative paths for copied files."""
        copier = FilesystemCopier()
        target_github = target_project_with_marker / ".github"
        project = DiscoveredProject(
            root_path=target_project_with_marker,
            github_path=target_github,
        )

        result = copier(source_github_dir, project, dry_run=False)

        # All paths should be relative (no absolute paths)
        for file_path in result.files_copied:
            assert not file_path.is_absolute()
            # Should contain expected files
            assert any(
                expected in str(file_path) for expected in ["workflows", "dependabot", "action"]
            )


class TestCopyResultProperties:
    """Tests for CopyResult properties."""

    def test_is_success_for_success_status(
        self, source_github_dir: Path, target_project_with_marker: Path
    ) -> None:
        """is_success should be True for SUCCESS status."""
        copier = FilesystemCopier()
        target_github = target_project_with_marker / ".github"
        project = DiscoveredProject(
            root_path=target_project_with_marker,
            github_path=target_github,
        )

        result = copier(source_github_dir, project, dry_run=False)

        assert result.is_success is True

    def test_is_success_for_dry_run_status(
        self, source_github_dir: Path, target_project_with_marker: Path
    ) -> None:
        """is_success should be True for DRY_RUN status."""
        copier = FilesystemCopier()
        target_github = target_project_with_marker / ".github"
        project = DiscoveredProject(
            root_path=target_project_with_marker,
            github_path=target_github,
        )

        result = copier(source_github_dir, project, dry_run=True)

        assert result.is_success is True
