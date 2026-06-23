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

## PyPI publishing (API token or Trusted Publisher)

The release workflow (`default_release_public.yml`) publishes with whichever auth is
available, chosen automatically by its `Select PyPI auth method` step:

- If the `PYPI_API_TOKEN` secret is set, it publishes with that API token.
- If the secret is absent, it publishes via an OIDC Trusted Publisher (the job has
  `id-token: write` and is pinned to the `pypi` environment).

This means a project keeps working on a token and can migrate to a Trusted Publisher
with no workflow change:

1. On PyPI, add a Trusted Publisher for the project: owner `<github-owner>`, repository
   `<repo>`, workflow `default_release_public.yml`, environment `pypi`.
2. Delete the `PYPI_API_TOKEN` secret from the GitHub repository.

The next release then uses OIDC. If you ever see PyPI report that a Trusted Publisher
is configured but the upload still used an API token, that means the `PYPI_API_TOKEN`
secret is still present: delete it so the workflow switches to OIDC. To re-enable token
publishing, just add the secret back.

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
