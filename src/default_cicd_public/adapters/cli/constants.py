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
# TEXT_MARKUP replaces the USE_RICH_MARKUP / USE_MARKDOWN pair, which rich-click >= 1.9 resolves to
# the same "rich" value but warns about on every help render.
click.rich_click.TEXT_MARKUP = "rich"
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "dim"
