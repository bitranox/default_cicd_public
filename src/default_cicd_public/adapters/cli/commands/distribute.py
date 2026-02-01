"""The distribute command for copying CI/CD templates to projects."""

import sys
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.table import Table

from default_cicd_public.application.ports import AppServices
from default_cicd_public.domain.models import CopyResult, CopyStatus


def get_default_search_root() -> Path:
    """Get the default search root based on the platform."""
    if sys.platform == "win32":
        # On Windows, default to C:\
        return Path("C:\\")
    return Path("/")


@click.command()
@click.option(
    "--source",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Source .github/ directory to copy from. Auto-detected if not specified.",
)
@click.option(
    "--search-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Root directory to search from. Defaults to filesystem root (/ or C:\\).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be copied without making changes.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed per-project output.",
)
@click.pass_obj
def distribute(
    services: AppServices,
    source: Path | None,
    search_root: Path | None,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Distribute CI/CD templates to all projects with the marker file.

    Searches for projects containing .github/workflows/default_cicd_public.yml
    and copies all files from this project's .github/ directory to each target.
    """
    console = Console()

    # Determine search root
    if search_root is None:
        search_root = get_default_search_root()

    # Get our source .github path
    if source is not None:
        source_github_path = source.resolve()
    else:
        source_github_path = services.get_source_github_path()
    our_project_root = source_github_path.parent.resolve()

    if verbose:
        console.print(f"[dim]Source .github/:[/] {source_github_path}")
        console.print(f"[dim]Search root:[/] {search_root}")
        if dry_run:
            console.print("[yellow]DRY RUN - no changes will be made[/]")
        console.print()

    # Discover and process projects
    results: list[CopyResult] = []

    with console.status("[bold blue]Searching for projects...", spinner="dots"):
        discovered = list(services.discover_projects(search_root))

    # Filter out our own project
    projects_to_process = [p for p in discovered if p.root_path.resolve() != our_project_root]

    if not projects_to_process:
        console.print("[yellow]No target projects found.[/]")
        return

    console.print(f"Found [bold]{len(projects_to_process)}[/] target project(s)")
    console.print()

    # Process each project
    for project in projects_to_process:
        with console.status(f"[bold blue]Processing {project.root_path}...", spinner="dots"):
            result = services.copy_templates(
                source_github_path,
                project,
                dry_run=dry_run,
            )
            results.append(result)

        if verbose:
            _print_result(console, result, dry_run)

    # Print summary
    console.print()
    _print_summary(console, results, dry_run)


def _print_result(console: Console, result: CopyResult, dry_run: bool) -> None:
    """Print the result of a single copy operation."""
    status_styles = {
        CopyStatus.SUCCESS: "[green]✓ SUCCESS[/]",
        CopyStatus.DRY_RUN: "[cyan]○ DRY RUN[/]",
        CopyStatus.SKIPPED_SELF: "[dim]- SKIPPED (self)[/]",
        CopyStatus.PERMISSION_DENIED: "[red]✗ PERMISSION DENIED[/]",
        CopyStatus.ERROR: "[red]✗ ERROR[/]",
    }

    status_text = status_styles.get(result.status, f"[yellow]? {result.status.value}[/]")
    console.print(f"  {result.project.root_path}: {status_text}")

    if result.error_message:
        console.print(f"    [red]{result.error_message}[/]")

    if result.files_copied and result.is_success:
        console.print(f"    [dim]Files: {len(result.files_copied)}[/]")


def _print_summary(console: Console, results: list[CopyResult], dry_run: bool) -> None:
    """Print a summary table of all operations."""
    table = Table(title="Distribution Summary")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")

    # Count by status
    counts: dict[CopyStatus, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1

    status_order = [
        (CopyStatus.SUCCESS, "green"),
        (CopyStatus.DRY_RUN, "cyan"),
        (CopyStatus.SKIPPED_SELF, "dim"),
        (CopyStatus.PERMISSION_DENIED, "red"),
        (CopyStatus.ERROR, "red"),
    ]

    for status, style in status_order:
        if status in counts:
            table.add_row(f"[{style}]{status.value}[/]", str(counts[status]))

    console.print(table)

    # Final message
    total = len(results)
    successful = counts.get(CopyStatus.SUCCESS, 0) + counts.get(CopyStatus.DRY_RUN, 0)

    if dry_run:
        console.print(f"\n[cyan]Would update {successful}/{total} projects.[/]")
    else:
        console.print(f"\n[green]Updated {successful}/{total} projects.[/]")
