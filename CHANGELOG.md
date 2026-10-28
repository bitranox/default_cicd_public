# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Free-threaded CI cells: `[tool.ci] free-threaded = ["3.15"]` in a consumer's `pyproject.toml`
  adds a `3.15t` test cell on every OS except macOS (which keeps only the newest regular version).
  It is a `[tool.ci]` key and not a classifier because `3.15t` is no trove classifier and hatchling
  refuses to build with an unknown one. Each entry must be an `"X.Y"` string the classifiers
  already declare, or the setup job fails; the job warns when the list is set but no
  `Programming Language :: Python :: Free Threading :: <level>` classifier is.
- Python 3.15 is a supported version: declared in the classifiers, so CI and `make test-all` run it.
- `uv.lock` is committed, and `[tool.uv] exclude-newer` sets a cooldown that keeps releases younger
  than it out of the lock. CI installs exactly the locked tree on push and pull request; the nightly
  scheduled run still resolves afresh to catch upstream breakage early.

### Changed
- The test job runs pytest across processes exactly when bmk's `make test` does: a new
  `Choose pytest workers` step passes `-n <workers> --dist loadgroup` when the project's configured
  pytest loads pytest-xdist and pytest-cov, with the count from `[tool.scripts.test] workers`
  (`1` keeps the suite in one process; a project's own `-n` or `--dist` is kept). It stays serial
  when the installed pytest drops pytest-xdist's `xdist_group` marks, as pytest 9.2.0 does with
  pytest-xdist 3.8.0 (pytest-xdist issue #1386), the same rule as bmk 3.31.0. The step also
  prints the runner's CPU model and count: a cell's runtime turned out to depend on the machine
  GitHub assigns (lsdsk's cells on Python 3.11-3.13 ran either about 17 or about 28 minutes,
  whichever version it was, and a Node step in the same job slowed by the same factor).
- The `test`, `pipx-uv` and `notebooks` jobs time out after 60 minutes instead of 30. A large suite's slowest cells
  (on a slower GitHub runner) reached the 30-minute limit
  and were cancelled after their tests had already passed, so a green suite read as a failure.
  60 still ends a hung job hours before GitHub's six-hour default.
- CI installs the project from its committed `uv.lock` on push and pull request: `uv export
  --locked` writes the pinned tree with file hashes, uv installs it (verifying every hash), and the
  project itself goes in with `--no-deps`. `--locked` fails the run when `pyproject.toml` changed
  without a lock refresh. The nightly scheduled run keeps the unlocked resolve, still inside the
  project's `[tool.uv]` cooldown, as a canary for upstream breakage. `pip-audit` audits the same
  tree the install step used. A project without a `uv.lock` keeps the unlocked install.
- `[project.urls]` points at the real repository, and the README installs from git: the package is
  not on PyPI.
- The release workflow triggers on a `v*` tag push only. It previously also listened
  for `release: published`, and since `bmk release` pushes the tag and then creates the
  GitHub release, both events fired about a second apart and produced two concurrent
  Release runs racing each other to the same PyPI upload. The loser logged
  `Skipping ... already exists`, which reads like a failed publish even though the
  package shipped. The tag push is the event to keep: `bmk` runs `git push <remote> <tag>`
  unconditionally, while `gh release create` sits behind a gh-availability check and runs
  with `check=False`, so keying the publish off the release event instead would silently
  publish nothing whenever `gh` is missing or fails. A `concurrency` group keyed on the tag
  now also stops a `workflow_dispatch` re-run from overlapping the tag-push run.
  Creating a GitHub release from the UI for an already-pushed tag no longer publishes;
  the tag push already did at creation time.
- The CI `pip-audit` step now audits the project's own resolved dependency tree
  (`uv pip compile` on `pyproject.toml`, then `pip-audit --no-deps -r`) instead of
  the whole `--system` environment. Because dev deps are installed into the runner
  image's interpreter, the scan was reporting CVEs in packages the runner ships but
  no project declares or distributes (`setuptools`, `pip`, `wheel`) - findings no
  consumer is exposed to, and which no project can fix. The result is now identical
  across every OS/python in the matrix and depends only on declared dependencies.
  The dev-dependency selector is chosen from what each project actually declares
  (`--extra dev`, a PEP 735 `--group dev`, or neither); asking uv for an extra that
  does not exist is a hard error, which would have broken the audit outright in a
  project that declares no dev dependencies.
- Direct URL requirements (`pkg @ git+https://...`) are filtered out before the
  audit and named in a `::notice::` rather than dropped silently. pip-audit cannot
  audit them (they are not on PyPI) but would first try to `git clone` each one to
  resolve a version. No public project uses one today; this keeps the step
  identical to `default_cicd_private`, where sibling private repos are depended on
  exactly that way.
- The install section explains why installing with uv protects against supply-chain attacks and why
  a plain `pip install` from PyPI does not.
- The test matrix runs macOS on the newest declared Python only; ubuntu and windows still run every
  version. GitHub's macOS runners are slow, so a repository listing `macos-latest` now gets one macOS
  test job instead of one per version. The setup job builds the pairs as a `matrix-include` output,
  and `python-latest` is the newest version by number rather than the last classifier.
- `tests/test_test_matrix.py` runs the setup job's own matrix script against sample pyproject files;
  PyYAML (and its type stubs) is now a declared dev dependency for it.
- The `test`, `pipx-uv` and `notebooks` jobs time out after 30 minutes. A hung test held its runner
  for GitHub's six-hour limit, and on macOS that also starved every other repository's macOS jobs.
- `astral-sh/setup-uv` moves from v7 to v10.3.2 (pinned by sha) in the CI and release workflows,
  keeping `enable-cache: true` and `prune-cache: false`. v10.3.1 stops concurrent jobs from warning
  `Failed to save: Unable to reserve cache` when they save the same cache key.

### Fixed
- macOS test jobs ran on Homebrew's Python instead of the matrix version: the bash-4 step put all of
  `$(brew --prefix)/bin` on PATH, so Homebrew's `python3` came first and `uv pip install --system`
  installed into it. Only bash's own bin directory goes on PATH now, every install in the test job
  names setup-python's interpreter (`--python sys.executable`), and a new "Assert the matrix
  interpreter" step fails the job on any OS when `python` or `pytest` on PATH belong to another
  installation (on macOS the toolcache's `bin` is a symlink into the python.org framework install,
  which counts as setup-python's own). `tests/test_workflow_guards.py` runs that step's script against a pass and a fail
  case.

### Security
- Every third-party action in the distributed workflows is pinned to a full commit sha, with the
  ref it replaced kept as a trailing comment (`uses: owner/repo@<40-hex sha> # v7`):
  `pypa/gh-action-pypi-publish` (`release/v1`), `astral-sh/setup-uv` (`v7`) and
  `codecov/codecov-action` (`v7`). A tag or branch can be moved by whoever controls the action's
  repository, and every consumer would run the moved code on its next CI or release run; the
  publish step in particular holds the PyPI credential. `actions/*` and `github/*` stay on major
  tags. Dependabot's `github-actions` ecosystem updates the sha and the comment together. A test
  fails when any non-`actions`/`github` `uses:` under `.github/` is not pinned this way.
- Dependabot checks the `github-actions` ecosystem monthly instead of weekly and groups every
  action update into one pull request (`groups: github-actions: patterns: ["*"]`), so the sha
  pins arrive as one reviewable bump rather than one PR per action. The `pip` ecosystem is
  unchanged.

## [0.1.4] 2026-06-14

### Changed
- Added a `typed_click.py` facade wrapping rich-click's `option` / `version_option` decorators behind explicit, fully-known signatures, keeping the CLI strict-clean under pyright (`reportUnknownMemberType`) without disabling the rule (ignore isolated to the facade).

## [0.1.3] - 2026-05-18

### Fixed

- Silenced pyright strict-mode false positive `reportUnknownMemberType` triggered by Click 8.4's generic `ParamType`; scoped suppression to the two CLI adapter modules (`adapters/cli/commands/distribute.py`, `adapters/cli/root.py`)

### Changed

- Refreshed pip-audit CVE exclusion list: dropped obsolete pip (CVE-2025-8869, CVE-2026-1703) and pillow (CVE-2026-25990) entries, added paramiko (CVE-2026-44405) and urllib3 (CVE-2026-44431, CVE-2026-44432) entries
- Cleaned up `.gitignore`

## [0.1.2] - 2026-03-31

### Changed

- Updated CI/CD workflow matrix and actions (codecov v6, upload/download artifact updates)
- Switched pip-audit to warning-only mode to reduce noise
- Disabled ruff cache write on private runner
- Configured bandit to read from pyproject.toml

### Fixed

- Cleaned up CVE exclusions: removed resolved setuptools/pygments CVEs, added current pip, pillow, and py exclusions
- Fixed `tomllib` import error on Python 3.10 in CI system dependency install steps (fallback to `pip._vendor.tomli`)

## [0.1.1] - 2026-02-13

### Changed

- Updated CI/CD workflows and metadata extraction action
- Updated dev dependencies to latest versions (pytest 9.x, pytest-cov 7.x, ruff 0.15.x, pyright 1.1.408, bandit 1.9.3, pip-audit 2.10.0, import-linter 2.10)
- Added Bash 4+ compatibility for macOS
- Set test coverage threshold to 80%

### Fixed

- Added CVE exclusions for transitive setuptools vulnerabilities (CVE-2026-1703, CVE-2026-25990, CVE-2026-26007)
- Updated `.gitignore` to not exclude `.devcontainer`

### Added

- Added Makefile for project task automation
- Added quickstart notebook
