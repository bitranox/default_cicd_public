"""The test matrix runs macOS on the newest declared Python only, every other OS on all of them.

GitHub's macOS runners are slow, so a repository that lists `macos-latest` in `[tool.ci].os` gets
one macOS test job (the newest Python from its classifiers) instead of one per version. ubuntu and
windows keep the whole version list. The matrix is computed by a Python script inside the
workflow's `setup` job, so these tests run that exact script against a sample pyproject.toml and
read what it writes to GITHUB_OUTPUT: a copy of the logic would pass while the workflow drifted.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "default_cicd_public.yml"

ALL_OS = '["ubuntu-latest", "windows-latest", "macos-latest"]'


def _workflow() -> dict[str, Any]:
    return cast("dict[str, Any]", yaml.safe_load(WORKFLOW.read_text(encoding="utf-8")))


def _metadata_script() -> str:
    steps = cast("list[dict[str, Any]]", _workflow()["jobs"]["setup"]["steps"])
    return next(str(step["run"]) for step in steps if step.get("id") == "metadata")


def _run_setup(tmp_path: Path, *, versions: list[str], os_list: str) -> dict[str, str]:
    """Run the setup job's metadata script against a pyproject and return its outputs."""
    classifiers = ", ".join(f'"Programming Language :: Python :: {v}"' for v in versions)
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nclassifiers = [{classifiers}]\n\n[tool.ci]\nos = {os_list}\n',
        encoding="utf-8",
    )
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    subprocess.run(
        [sys.executable, "-c", _metadata_script()],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output)},
        check=True,
    )
    lines = output.read_text(encoding="utf-8").splitlines()
    return dict(line.split("=", 1) for line in lines if line)


def _include(outputs: dict[str, str]) -> list[tuple[str, str]]:
    entries = cast("list[dict[str, str]]", json.loads(outputs["matrix-include"]))
    return sorted((entry["os"], entry["python"]) for entry in entries)


def test_macos_runs_only_the_newest_python(tmp_path: Path) -> None:
    outputs = _run_setup(
        tmp_path, versions=["3.10", "3.11", "3.12", "3.13", "3.14", "3.15"], os_list=ALL_OS
    )

    include = _include(outputs)

    assert [pair for pair in include if pair[0] == "macos-latest"] == [("macos-latest", "3.15")]
    for os_name in ("ubuntu-latest", "windows-latest"):
        assert [py for name, py in include if name == os_name] == [
            "3.10",
            "3.11",
            "3.12",
            "3.13",
            "3.14",
            "3.15",
        ]


def test_newest_is_chosen_by_version_not_by_classifier_order(tmp_path: Path) -> None:
    outputs = _run_setup(tmp_path, versions=["3.15", "3.9", "3.10"], os_list=ALL_OS)

    assert outputs["python-latest"] == "3.15"
    assert [pair for pair in _include(outputs) if pair[0] == "macos-latest"] == [
        ("macos-latest", "3.15")
    ]


def test_without_macos_every_os_gets_every_version(tmp_path: Path) -> None:
    outputs = _run_setup(
        tmp_path, versions=["3.12", "3.13"], os_list='["ubuntu-latest", "windows-latest"]'
    )

    assert _include(outputs) == [
        ("ubuntu-latest", "3.12"),
        ("ubuntu-latest", "3.13"),
        ("windows-latest", "3.12"),
        ("windows-latest", "3.13"),
    ]


def test_the_test_job_takes_its_matrix_from_the_setup_include() -> None:
    workflow = _workflow()

    assert workflow["jobs"]["test"]["strategy"]["matrix"] == {
        "include": "${{ fromJSON(needs.setup.outputs.matrix-include) }}",
    }
    assert "matrix-include" in workflow["jobs"]["setup"]["outputs"]
