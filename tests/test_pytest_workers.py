"""The test job runs pytest across processes exactly when bmk's ``make test`` would.

A project that lists pytest-xdist in its dev extra runs its suite in parallel locally, through bmk;
CI ran the same suite in one process, so a cell took two to three times as long as the suite
needed. The ``Choose pytest workers`` step applies bmk's own rule (bmk
``adapters/stagerunner/helpers/_parallel.py``): parallel only when the project's configured pytest
loads both pytest-xdist and pytest-cov, the worker count from ``[tool.scripts.test] workers``
(``1`` is serial), ``--dist loadgroup`` unless the project picks a mode, and a project's own ``-n``
left alone. These tests run that exact script against sample projects and read what it writes to
GITHUB_OUTPUT: a copy of the logic would pass while the workflow drifted.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

# The step parses pyproject.toml with tomllib (3.11+), and asks the project's pytest which plugins
# it loads, so the interpreter running these tests must have both plugins: the template's own dev
# extra lists them.
pytestmark = [
    pytest.mark.skipif(sys.version_info < (3, 11), reason="the step's tomllib needs 3.11+"),
    pytest.mark.skipif(
        importlib.util.find_spec("xdist") is None or importlib.util.find_spec("pytest_cov") is None,
        reason="the probe needs pytest-xdist and pytest-cov installed",
    ),
]

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
CICD = WORKFLOWS / "default_cicd_public.yml"
WORKERS_STEP = "Choose pytest workers"


def _steps() -> list[dict[str, Any]]:
    workflow = cast("dict[str, Any]", yaml.safe_load(CICD.read_text(encoding="utf-8")))
    return cast("list[dict[str, Any]]", workflow["jobs"]["test"]["steps"])


def _step(name: str) -> dict[str, Any]:
    return next(s for s in _steps() if s.get("name") == name)


def _run(tmp_path: Path, pyproject: str) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    """Run the step as GitHub's ``shell: python`` does, in a project holding ``pyproject``."""
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    script = tmp_path.parent / f"{tmp_path.name}-step.py"
    script.write_text(str(_step(WORKERS_STEP)["run"]), encoding="utf-8")
    env = {
        k: v for k, v in os.environ.items() if k not in {"PYTEST_ADDOPTS", "PYTEST_XDIST_WORKER"}
    }
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**env, "GITHUB_OUTPUT": str(output)},
        check=False,
    )
    lines = output.read_text(encoding="utf-8").splitlines()
    return result, dict(line.split("=", 1) for line in lines if "=" in line)


PROJECT = '[project]\nname = "x"\nversion = "0"\n'


def _with_addopts(addopts: str, extra: str = "") -> str:
    return f'{PROJECT}\n[tool.pytest.ini_options]\naddopts = "{addopts}"\n{extra}'


def test_a_project_whose_pytest_loads_xdist_and_cov_runs_on_every_core(tmp_path: Path) -> None:
    result, out = _run(tmp_path, PROJECT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert out["args"] == "-n auto --dist loadgroup"


def test_a_worker_count_from_tool_scripts_test_is_passed_through(tmp_path: Path) -> None:
    result, out = _run(tmp_path, f"{PROJECT}\n[tool.scripts.test]\nworkers = 3\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert out["args"] == "-n 3 --dist loadgroup"


def test_workers_1_keeps_the_suite_in_one_process(tmp_path: Path) -> None:
    result, out = _run(tmp_path, f"{PROJECT}\n[tool.scripts.test]\nworkers = 1\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert out["args"] == ""


def test_workers_1_overrides_a_projects_own_n_with_n_0(tmp_path: Path) -> None:
    result, out = _run(tmp_path, _with_addopts("-n 4", "\n[tool.scripts.test]\nworkers = 1\n"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert out["args"] == "-n 0"


def test_a_projects_own_n_is_left_alone(tmp_path: Path) -> None:
    result, out = _run(tmp_path, _with_addopts("-n 2"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert out["args"] == ""


def test_a_projects_own_dist_mode_is_kept(tmp_path: Path) -> None:
    result, out = _run(tmp_path, _with_addopts("--dist loadfile"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert out["args"] == "-n auto"


def test_a_project_that_blocks_xdist_stays_serial(tmp_path: Path) -> None:
    result, out = _run(tmp_path, _with_addopts("-p no:xdist"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert out["args"] == ""
    assert "serial" in result.stdout


def test_a_project_that_blocks_pytest_cov_stays_serial(tmp_path: Path) -> None:
    # The test job always measures coverage, and only pytest-cov carries it into the workers.
    result, out = _run(tmp_path, _with_addopts("-p no:pytest_cov"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert out["args"] == ""


# pytest 9.2.0 builds Node.nodeid from a structured id and never reads _nodeid, which is where
# pytest-xdist 3.8.0 writes an item's group (pytest-xdist issue #1386), so --dist loadgroup spreads
# every xdist_group over all workers and the run stays green. This conftest gives the template's own
# pytest that behaviour, so the step's check runs against the real installed xdist source.
_NODEID_IGNORES_RENAME = (
    'from _pytest.nodes import Node\nNode.nodeid = property(lambda self: "structured-id")\n'
)


def test_a_pytest_that_drops_xdist_group_marks_stays_serial(tmp_path: Path) -> None:
    (tmp_path / "conftest.py").write_text(_NODEID_IGNORES_RENAME, encoding="utf-8")
    result, out = _run(tmp_path, PROJECT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert out["args"] == ""
    assert "pytest runs serial" in result.stdout
    assert "#1386" in result.stdout


def test_a_pytest_that_drops_xdist_group_marks_overrides_a_projects_own_n(tmp_path: Path) -> None:
    (tmp_path / "conftest.py").write_text(_NODEID_IGNORES_RENAME, encoding="utf-8")
    result, out = _run(tmp_path, _with_addopts("-n 4"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert out["args"] == "-n 0"


@pytest.mark.parametrize("bad", ['"many"', "0", "true", "-2"])
def test_a_worker_setting_that_is_no_count_fails_the_step(tmp_path: Path, bad: str) -> None:
    result, out = _run(tmp_path, f"{PROJECT}\n[tool.scripts.test]\nworkers = {bad}\n")
    assert result.returncode == 1
    assert "::error::" in result.stdout
    assert "[tool.scripts.test] workers" in result.stdout
    assert "args" not in out


def test_the_step_names_the_machine_it_runs_on(tmp_path: Path) -> None:
    # A cell's runtime depends on the runner's CPU as much as on the code, so the log says which.
    result, _ = _run(tmp_path, PROJECT)
    assert f"{os.cpu_count()} CPUs" in result.stdout


def test_the_step_runs_on_every_os_after_the_dev_deps_and_before_pytest() -> None:
    names = [s.get("name") for s in _steps()]
    step = _step(WORKERS_STEP)
    assert (
        names.index("Install dev deps")
        < names.index(WORKERS_STEP)
        < names.index("Run pytest (tests + coverage)")
    )
    assert "if" not in step
    assert step.get("shell") == "python"
    assert step.get("id") == "workers"


def test_pytest_receives_the_chosen_arguments() -> None:
    run = str(_step("Run pytest (tests + coverage)")["run"])
    assert "${{ steps.workers.outputs.args }}" in run
