"""Filesystem-based template copier."""

import shutil
from pathlib import Path

from default_cicd_public.domain.models import CopyResult, CopyStatus, DiscoveredProject


class FilesystemCopier:
    """Copies template files to target projects."""

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
        files_to_copy = self._collect_files(source_github_path)

        if dry_run:
            return CopyResult(
                project=target_project,
                status=CopyStatus.DRY_RUN,
                files_copied=files_to_copy,
            )

        try:
            copied_files = self._copy_files(source_github_path, target_project.github_path)
            return CopyResult(
                project=target_project,
                status=CopyStatus.SUCCESS,
                files_copied=copied_files,
            )
        except PermissionError as e:
            return CopyResult(
                project=target_project,
                status=CopyStatus.PERMISSION_DENIED,
                error_message=str(e),
            )
        except OSError as e:
            return CopyResult(
                project=target_project,
                status=CopyStatus.ERROR,
                error_message=str(e),
            )

    def _collect_files(self, source_path: Path) -> list[Path]:
        """Collect all files to be copied (relative paths)."""
        files: list[Path] = []
        for item in source_path.rglob("*"):
            if item.is_file():
                files.append(item.relative_to(source_path))
        return sorted(files)

    def _copy_files(self, source_path: Path, target_path: Path) -> list[Path]:
        """Copy all files from source to target, preserving structure."""
        copied: list[Path] = []

        for item in source_path.rglob("*"):
            if not item.is_file():
                continue

            relative = item.relative_to(source_path)
            target_file = target_path / relative

            # Create parent directories if needed
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file
            shutil.copy2(item, target_file)
            copied.append(relative)

        return sorted(copied)
