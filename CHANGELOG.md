# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
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
