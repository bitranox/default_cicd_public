# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
