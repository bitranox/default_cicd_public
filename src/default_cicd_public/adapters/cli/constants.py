"""CLI constants and configuration."""

from pathlib import Path

import rich_click as click

# The marker file that identifies projects using our CI/CD templates
MARKER_FILE = Path(".github") / "workflows" / "default_cicd_public.yml"

# Click context settings
CLICK_CONTEXT_SETTINGS: dict[str, object] = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 120,
}

# Rich-click styling
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = False
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "dim"
