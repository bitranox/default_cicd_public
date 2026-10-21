"""Every third-party action this template distributes is pinned to a full commit sha.

A tag or branch ref (`@v7`, `@release/v1`) is mutable: whoever controls the action's repository
can move it, and every consumer repo then runs the new code on its next CI or release run. A
40-hex commit sha cannot be moved. The trailing `# <ref>` comment keeps the human-readable ref
next to the sha, and dependabot's github-actions ecosystem updates sha and comment together.

Actions owned by `actions` and `github` stay on major tags: that is a recorded trust decision
(GitHub-hosted, GitHub-maintained), not an oversight, so this test does not demand a pin there.
Local `./...` actions ship inside `.github/` itself and have no ref at all.

The scan is line-based rather than a YAML parse because a `uses:` key in a workflow or composite
action is always a scalar on one line, and the comment this test checks is invisible to a YAML
loader.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

GITHUB_DIR = Path(__file__).resolve().parents[1] / ".github"
TRUSTED_OWNERS = frozenset({"actions", "github"})
USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<value>.*?)\s*$")
PINNED = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40} # \S+")


def _unquote(value: str) -> str:
    """Return the ref with one pair of surrounding YAML quotes removed."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def unpinned_reason(value: str) -> str | None:
    """Return why a `uses:` value violates the pinning rule, or None when it is acceptable.

    Args:
        value: Everything after `uses:` on the line, trailing comment included.

    Returns:
        A short reason for a third-party ref not pinned as `owner/repo@<sha> # <ref>`,
        or None for a pinned ref, a trusted owner's ref, or a local `./` action.

    Examples:
        >>> unpinned_reason("actions/checkout@v7") is None
        True
        >>> unpinned_reason("pypa/gh-action-pypi-publish@release/v1")
        'not pinned to a 40-hex commit sha with a # <ref> comment'
    """
    bare = _unquote(value.split(" #", 1)[0].strip())
    if bare.startswith("./"):
        return None
    owner = bare.split("/", 1)[0]
    if owner in TRUSTED_OWNERS:
        return None
    if PINNED.fullmatch(value) is None:
        return "not pinned to a 40-hex commit sha with a # <ref> comment"
    return None


def _uses_lines() -> list[tuple[str, int, str]]:
    """Return (relative path, line number, value) for every `uses:` line under .github/."""
    found: list[tuple[str, int, str]] = []
    for path in sorted(GITHUB_DIR.rglob("*")):
        if path.suffix not in {".yml", ".yaml"} or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            match = USES_LINE.match(line)
            if match is not None:
                found.append((str(path.relative_to(GITHUB_DIR)), number, match["value"]))
    return found


@pytest.mark.parametrize(
    ("value", "acceptable"),
    [
        ("actions/checkout@v7", True),
        ("github/codeql-action/init@v4", True),
        ("./.github/actions/extract-metadata", True),
        ("astral-sh/setup-uv@37802adc94f370d6bfd71619e3f0bf239e1f3b78 # v7", True),
        ("'astral-sh/setup-uv@v7'", False),
        ("astral-sh/setup-uv@v7", False),
        ("pypa/gh-action-pypi-publish@release/v1", False),
        ("astral-sh/setup-uv@37802adc94f370d6bfd71619e3f0bf239e1f3b78", False),
        ("astral-sh/setup-uv@37802adc94f370d6bfd71619e3f0bf239e1f3b7 # v7", False),
        ("astral-sh/setup-uv@37802ADC94F370D6BFD71619E3F0BF239E1F3B78 # v7", False),
    ],
)
def test_unpinned_reason_classifies_refs(value: str, acceptable: bool) -> None:
    """The rule accepts trusted and local refs and pinned third-party ones, nothing else."""
    assert (unpinned_reason(value) is None) is acceptable


def test_every_third_party_action_is_pinned_to_a_commit_sha() -> None:
    """No `uses:` under .github/ names a third-party action by a movable tag or branch."""
    lines = _uses_lines()
    # A scan that found nothing proves nothing: the workflows certainly contain uses: lines.
    assert lines, f"no uses: lines found under {GITHUB_DIR}"
    violations = [
        f"{path}:{number}: {value} ({reason})"
        for path, number, value in lines
        if (reason := unpinned_reason(value)) is not None
    ]
    assert not violations, "\n".join(violations)
