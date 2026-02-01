"""Root CLI command group."""

import rich_click as click

from default_cicd_public.__init__conf__ import __app_name__, __version__
from default_cicd_public.adapters.cli.constants import CLICK_CONTEXT_SETTINGS


@click.group(context_settings=CLICK_CONTEXT_SETTINGS)
@click.version_option(__version__, "-V", "--version", prog_name=__app_name__)
def cli() -> None:
    """Default CI/CD Public - Distribute CI/CD templates to your projects."""


# Import and register commands
from default_cicd_public.adapters.cli.commands.distribute import distribute  # noqa: E402

cli.add_command(distribute)
