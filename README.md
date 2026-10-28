# Default CI/CD Public

CLI tool to distribute CI/CD templates to projects.

## Installation

It is not published on PyPI; install it from the repository:

```bash
uv tool install git+https://github.com/bitranox/default_cicd_public.git
```

### Why we recommend uv: supply-chain protection

This repository commits a `uv.lock`. It pins every package the project needs, transitive
dependencies included, to an exact version and to the hashes of that version's files. The
`exclude-newer` setting under `[tool.uv]` in `pyproject.toml` adds a cooldown: uv leaves any
release younger than that out of the lock. CI installs from the lock, so a hijacked release that
gets pulled again within the cooldown never reaches our builds, and a file whose hash does not
match is refused.

That protection stays in this repository. The installable package declares only lower bounds
(`>=`) for its dependencies, so a plain `pip install` takes the newest release of every transitive
dependency at the moment you run it. If one of them was hijacked an hour earlier, you get the
hijacked version. `pipx install` and `uv tool install` without options do the same.

To install the command line tool with a cooldown of your own (uv then skips any release younger
than 7 days, transitive ones included), or to run the exact tree our CI tests:

```bash
uv tool install --exclude-newer "7 days" git+https://github.com/bitranox/default_cicd_public.git
git clone https://github.com/bitranox/default_cicd_public.git && cd default_cicd_public && uv sync --locked && uv run default-cicd-public --help
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

## Test matrix (read from the consumer's pyproject.toml)

The CI `setup` job builds the test matrix from the consumer's `pyproject.toml`:

- Python versions: every `Programming Language :: Python :: X.Y` classifier.
- Operating systems: `[tool.ci] os` (default `["ubuntu-latest"]`). macOS runs only the newest
  declared version, because GitHub's macOS runners are slow.
- Free-threaded builds: `[tool.ci] free-threaded`, a list of `"X.Y"` versions that are also
  declared as classifiers. Each adds an `X.Yt` cell on every OS except macOS.

```toml
[project]
classifiers = [
  "Programming Language :: Python :: 3.15",
  "Programming Language :: Python :: Free Threading :: 2 - Beta",
]

[tool.ci]
os = ["ubuntu-latest", "windows-latest", "macos-latest"]
free-threaded = ["3.15"]
```

`3.15t` cannot go into the classifiers: it is not a trove classifier, and hatchling refuses to
build a package with an unknown one. The version-less `Free Threading :: <level>` classifier is
what PyPI shows; the setup job warns when `free-threaded` is set without it. A free-threaded cell
installs the dev dependencies like any other, so a dependency without a free-threaded build (or a
source build that refuses one) has to be kept out of the dev install for that interpreter.

## Parallel tests

The test job runs pytest across processes exactly when bmk's `make test` does. The suite runs in
parallel only when the project's configured pytest loads both pytest-xdist and pytest-cov, which a
project gets by listing `pytest-xdist` in its dev extra. The worker count comes from
`[tool.scripts.test] workers`, bmk's own setting (default `"auto"`, one worker per CPU). A run
passes `--dist loadgroup`, so tests marked `@pytest.mark.xdist_group("<name>")` share one worker.
A `-n` or `--dist` in the project's own `addopts` is kept.

```toml
[tool.scripts.test]
workers = 1   # a suite that is not safe to run in parallel stays in one process
```

The suite also stays in one process when the installed pytest drops pytest-xdist's `xdist_group`
marks, which pytest 9.2.0 does with pytest-xdist 3.8.0 (pytest-xdist issue #1386): grouped tests
would otherwise run on every worker while the run stays green. The step asks the installed code,
not its version, so a fixed pytest-xdist release turns parallel runs back on by itself.

The `Choose pytest workers` step prints the runner's CPU model and count, because a cell's runtime
depends on the machine GitHub assigns as much as on the code.

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
