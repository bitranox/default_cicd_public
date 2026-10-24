"""Guards on the distributed CI workflow: job timeouts, the setup-uv pin, and the test interpreter.

Each test pins a decision that a later edit could silently undo:

* A hung test once held five macOS runners for 50 minutes until it was cancelled by hand. The
  jobs that run project code therefore carry ``timeout-minutes: 30``.
* setup-uv is pinned to one reviewed commit (v10.3.0), in both workflows.
* On macOS, the bash-4 step used to put ALL of Homebrew's bin directory on PATH, so Homebrew's
  python3 shadowed setup-python's. ``uv pip install --system`` then installed into Homebrew's
  interpreter, and every macOS cell ran pytest on that Python while its job name still said the
  matrix version. Now only bash's own bin directory goes on PATH, every install names its
  interpreter, and a workflow step fails the job when ``python`` or ``pytest`` on PATH belong to
  any other installation. That step's script is executed here, against a pass and a fail case.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
CICD = WORKFLOWS / "default_cicd_public.yml"
RELEASE = WORKFLOWS / "default_release_public.yml"
SETUP_UV = "astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0"
ASSERT_STEP = "Assert the matrix interpreter"


def _jobs() -> dict[str, Any]:
    workflow = cast("dict[str, Any]", yaml.safe_load(CICD.read_text(encoding="utf-8")))
    return cast("dict[str, Any]", workflow["jobs"])


def _steps(job: str) -> list[dict[str, Any]]:
    return cast("list[dict[str, Any]]", _jobs()[job]["steps"])


def _code_lines(script: str) -> list[str]:
    """The script's lines without whole-line comments, which may name a flag they do not pass."""
    return [line for line in script.splitlines() if not line.lstrip().startswith("#")]


@pytest.mark.parametrize("job", ["test", "pipx-uv", "notebooks"])
def test_jobs_that_run_project_code_time_out_after_30_minutes(job: str) -> None:
    assert _jobs()[job].get("timeout-minutes") == 30


@pytest.mark.parametrize("workflow", [CICD, RELEASE], ids=lambda p: p.name)
def test_every_setup_uv_ref_is_the_reviewed_v10_3_0_pin(workflow: Path) -> None:
    refs = re.findall(
        r"uses:\s*(astral-sh/setup-uv@.*?)\s*$", workflow.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert refs, f"{workflow.name} has no setup-uv step"
    assert set(refs) == {SETUP_UV}


def test_macos_bash_step_puts_only_bash_on_path() -> None:
    bash_step = next(s for s in _steps("test") if s.get("name") == "Install bash 4+ on macOS")
    assert '"$(brew --prefix bash)/bin" >> "$GITHUB_PATH"' in bash_step["run"]
    for job in _jobs():
        for step in _steps(job):
            code = _code_lines(str(step.get("run", "")))
            assert not any("$(brew --prefix)/bin" in line for line in code), (
                f"{job}: {step.get('name')}"
            )


def test_no_install_in_the_test_job_targets_whatever_python_comes_first() -> None:
    offenders = [
        step.get("name")
        for step in _steps("test")
        if any("--system" in line for line in _code_lines(str(step.get("run", ""))))
    ]
    assert offenders == []


def test_the_interpreter_assertion_runs_on_every_os_right_after_the_dev_deps() -> None:
    names = [s.get("name") for s in _steps("test")]
    assert names.index(ASSERT_STEP) == names.index("Install dev deps") + 1
    step = _steps("test")[names.index(ASSERT_STEP)]
    assert "if" not in step
    assert step.get("shell") == "python"


# --- the assertion step's own script, executed --------------------------------------------------


def _assert_script() -> str:
    return str(next(s for s in _steps("test") if s.get("name") == ASSERT_STEP)["run"])


def _run_assert(
    tmp_path: Path, *, python_location: Path, pytest_shebang: str
) -> subprocess.CompletedProcess[str]:
    """Run the step as GitHub's `shell: python` does, with one fake pytest first on PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "pytest"
    fake.write_text(f"{pytest_shebang}\nimport sys\n", encoding="utf-8")
    fake.chmod(0o755)
    script = tmp_path / "step.py"
    script.write_text(_assert_script(), encoding="utf-8")
    env = {
        **os.environ,
        "pythonLocation": str(python_location),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    }
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


def _interpreter_root() -> Path:
    """The installation the running interpreter belongs to (a venv's python resolves into it)."""
    return Path(sys.executable).resolve().parents[1]


@pytest.mark.skipif(sys.platform == "win32", reason="the POSIX branch reads pytest's shebang")
def test_assert_step_passes_when_python_and_pytest_belong_to_setup_pythons_install(
    tmp_path: Path,
) -> None:
    result = _run_assert(
        tmp_path,
        python_location=_interpreter_root(),
        pytest_shebang=f"#!{Path(sys.executable).resolve()}",
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="the POSIX branch reads pytest's shebang")
def test_assert_step_fails_when_pytest_runs_another_interpreter(tmp_path: Path) -> None:
    other = tmp_path / "homebrew" / "bin" / "python3.15"
    result = _run_assert(tmp_path, python_location=_interpreter_root(), pytest_shebang=f"#!{other}")
    assert result.returncode == 1
    assert "::error::" in result.stdout
    assert "pytest" in result.stdout


@pytest.mark.skipif(sys.platform == "win32", reason="the POSIX branch reads pytest's shebang")
def test_assert_step_fails_when_python_itself_is_outside_setup_pythons_install(
    tmp_path: Path,
) -> None:
    elsewhere = tmp_path / "toolcache"
    elsewhere.mkdir()
    result = _run_assert(
        tmp_path, python_location=elsewhere, pytest_shebang=f"#!{Path(sys.executable).resolve()}"
    )
    assert result.returncode == 1
    assert "python on PATH" in result.stdout


@pytest.mark.skipif(sys.platform == "win32", reason="the POSIX branch reads pytest's shebang")
def test_assert_step_follows_the_sh_exec_form_of_a_long_shebang(tmp_path: Path) -> None:
    """Installers write `#!/bin/sh` plus an exec line when the interpreter path is too long."""
    exe = Path(sys.executable).resolve()
    shebang = f"#!/bin/sh\n'''exec' \"{exe}\" \"$0\" \"$@\"\n' '''"
    result = _run_assert(tmp_path, python_location=_interpreter_root(), pytest_shebang=shebang)
    assert result.returncode == 0, result.stdout + result.stderr


def _framework_layout(tmp_path: Path) -> Path:
    """setup-python's macOS layout: the toolcache dir's bin is a SYMLINK into the real install.

    actions/python-versions installs the python.org .pkg into /Library/Frameworks/.../Versions/X.Y
    and links <toolcache>/bin to it (installers/macos-pkg-setup-template.sh), so the interpreter's
    real path lies outside $pythonLocation. Here the real install is the one running this test.
    """
    toolcache = tmp_path / "toolcache" / "arm64"
    toolcache.mkdir(parents=True)
    (toolcache / "bin").symlink_to(Path(sys.executable).resolve().parent, target_is_directory=True)
    return toolcache


@pytest.mark.skipif(sys.platform == "win32", reason="the POSIX branch reads pytest's shebang")
def test_assert_step_accepts_a_toolcache_bin_symlinked_into_the_real_install(
    tmp_path: Path,
) -> None:
    result = _run_assert(
        tmp_path,
        python_location=_framework_layout(tmp_path),
        pytest_shebang=f"#!{Path(sys.executable).resolve()}",
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="the POSIX branch reads pytest's shebang")
def test_assert_step_still_rejects_another_interpreter_behind_a_symlinked_toolcache(
    tmp_path: Path,
) -> None:
    other = tmp_path / "homebrew" / "bin" / "python3.15"
    result = _run_assert(
        tmp_path, python_location=_framework_layout(tmp_path), pytest_shebang=f"#!{other}"
    )
    assert result.returncode == 1
    assert "pytest" in result.stdout
