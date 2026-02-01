"""Console script entry point."""

from default_cicd_public.adapters.cli.root import cli
from default_cicd_public.composition import build_production


def main() -> None:
    """Main entry point for the CLI."""
    services = build_production()
    cli(obj=services)


if __name__ == "__main__":
    main()
