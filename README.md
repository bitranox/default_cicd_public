# Default CI/CD Public

CLI tool to distribute CI/CD templates to projects.

## Installation

```bash
pip install default-cicd-public
```

## Usage

```bash
# Show help
default-cicd-public --help
default-cicd-public distribute --help

# Dry run to see what would be copied
default-cicd-public distribute --dry-run --verbose

# Actual distribution (use with caution)
default-cicd-public distribute --verbose

# Search from a specific root
default-cicd-public distribute --search-root /path/to/projects --dry-run
```

## How it works

The `distribute` command:
1. Searches from filesystem root (or specified `--search-root`) for projects containing `.github/workflows/default_cicd_public.yml`
2. Copies all files from this project's `.github/` to each target project's `.github/`
3. Skips its own project to avoid self-modification

## Development

```bash
# Install dev dependencies
pip install -e .[dev]

# Run tests
pytest -v --cov=default_cicd_public -m "not local_only"

# Run all tests including local integration tests
pytest -v --cov=default_cicd_public

# Lint and format
ruff check . && ruff format --check .

# Type check
pyright
```

## License

MIT
