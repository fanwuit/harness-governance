"""Parity tests against legacy `.mjs` / `.sh` / `.py` scripts.

These tests run the original Node and Bash implementations side-by-side
with the Python CLI on the same temporary repo and assert that both
produce the same file layout, error messages, and exit codes.

Tests are skipped automatically when Node or Bash are unavailable on
the host so the suite remains green on Windows agents without those
runtimes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from harness_governance.cli import cli

# Lazy detection of legacy runtimes.
HAS_NODE = shutil.which("node") is not None
HAS_BASH = shutil.which("bash") is not None or shutil.which("sh") is not None

def _on_windows_with_git_bash() -> bool:
    """Return True when running on Windows under Git Bash / MSYS.

    Git Bash mangles Windows-style paths (``E:\foo`` becomes
    ``E:foo`` after stripping the backslash), so passing
    ``bash`` an absolute Windows path requires a separate conversion
    that is brittle across shells. We skip the bash parity tests on
    Windows to keep the suite green.
    """
    import os
    import sys

    if sys.platform != "win32":
        return False
    bash_path = shutil.which("bash") or ""
    return "Git" in bash_path or "MSYS" in os.environ.get("MSYSTEM", "")


REPO_ROOT = Path(__file__).resolve().parents[1]


pytestmark = pytest.mark.skipif(
    not HAS_NODE,
    reason="node not on PATH; legacy parity tests require it.",
)


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _py(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Invoke the Python CLI with --project-root before the subcommand."""
    return _run(
        ["python", "-m", "harness_governance.cli", "--project-root", str(cwd), *args],
        cwd=cwd,
    )


# ---------------------------------------------------------------------------
# packet init parity
# ---------------------------------------------------------------------------


def test_packet_init_parity_with_legacy_mjs(tmp_path: Path) -> None:
    change_id = "parity-fixture"
    # Python
    runner_result = _py(["packet", "init", change_id], tmp_path)
    assert runner_result.returncode == 0, runner_result.stderr
    py_files = sorted(
        p.name for p in (tmp_path / "docs" / "changes" / change_id).iterdir()
    )

    # Clean up to give the legacy script a fresh slate.
    shutil.rmtree(tmp_path / "docs")
    legacy = _run(
        ["node",
         str(REPO_ROOT / "harness-engineering" / "scripts" / "init-change-packet.mjs"),
         change_id, "--repo", str(tmp_path)],
        cwd=tmp_path,
    )
    assert legacy.returncode == 0, legacy.stderr
    legacy_files = sorted(
        p.name for p in (tmp_path / "docs" / "changes" / change_id).iterdir()
    )
    assert py_files == legacy_files == [
        "contracts.md",
        "design.md",
        "proposal.md",
        "tasks.md",
        "verification.md",
    ]


def test_packet_check_parity_with_legacy_mjs(tmp_path: Path) -> None:
    """Both Python and Node reject a fresh packet with the same message."""
    change_id = "parity-check"
    _py(["packet", "init", change_id], tmp_path)

    py = _py(["packet", "check", change_id], tmp_path)
    legacy = _run(
        ["node",
         str(REPO_ROOT / "harness-engineering" / "scripts" / "check-change-packet.mjs"),
         change_id, "--repo", str(tmp_path)],
        cwd=tmp_path,
    )

    assert py.returncode == 1
    assert legacy.returncode == 1
    # Both should reference the missing verification.md (the only failing
    # invariant on a freshly initialized packet).
    assert "verification.md" in py.stdout
    assert "verification.md" in legacy.stderr


def test_packet_check_parity_with_filled_packet(tmp_path: Path) -> None:
    change_id = "parity-filled"
    packet_dir = tmp_path / "docs" / "changes" / change_id
    packet_dir.mkdir(parents=True)
    # Fill contracts + verification so both checks pass.
    (packet_dir / "tasks.md").write_text(
        "# Tasks\n\n- [x] step one\n- [ ] step two\n", encoding="utf-8"
    )
    (packet_dir / "proposal.md").write_text("# Proposal\n\nStatus: draft\n", encoding="utf-8")
    (packet_dir / "design.md").write_text("# Design\n", encoding="utf-8")
    (packet_dir / "contracts.md").write_text(
        "# Contracts\n\n- Artifact: schema\n- Path: schema.json\n",
        encoding="utf-8",
    )
    (packet_dir / "verification.md").write_text(
        "# Verification\n\n## Commands\n\n- pytest -q\n\n## Results\n\n- pass\n",
        encoding="utf-8",
    )

    py = _py(["packet", "check", change_id], tmp_path)
    legacy = _run(
        ["node",
         str(REPO_ROOT / "harness-engineering" / "scripts" / "check-change-packet.mjs"),
         change_id, "--repo", str(tmp_path)],
        cwd=tmp_path,
    )
    assert py.returncode == 0, py.stderr
    assert legacy.returncode == 0, legacy.stderr


# ---------------------------------------------------------------------------
# entry record parity
# ---------------------------------------------------------------------------


def test_entry_record_parity_with_legacy_mjs(tmp_path: Path) -> None:
    record = tmp_path / "entry.md"
    py = _py(
        [
            "entry", "record",
            "--target", "src/x.py",
            "--scope", "wire CLI",
            "--layer", "implementation",
            "--readiness-gate", "pass",
            "--packetization", "ready",
            "--verification-command", "pytest",
            "--review-next-state", "docs/x/tasks.md",
            "--stop-conditions", "fail",
            "--output", str(record),
        ],
        tmp_path,
    )
    assert py.returncode == 0, py.stderr

    legacy = _run(
        ["node",
         str(REPO_ROOT / "governed-implementation-entry" / "scripts" / "check-entry-record.mjs"),
         str(record), "--repo", str(tmp_path)],
        cwd=tmp_path,
    )
    assert legacy.returncode == 0, legacy.stderr
    assert "passed" in legacy.stdout.lower()


def test_entry_check_finds_missing_field_parity(tmp_path: Path) -> None:
    record = tmp_path / "entry.md"
    record.write_text(
        "Implementation Entry Record:\n\n- Target: src/x.py\n",
        encoding="utf-8",
    )
    py = _py(["entry", "check", str(record)], tmp_path)
    legacy = _run(
        ["node",
         str(REPO_ROOT / "governed-implementation-entry" / "scripts" / "check-entry-record.mjs"),
         str(record), "--repo", str(tmp_path)],
        cwd=tmp_path,
    )
    assert py.returncode == 1
    assert legacy.returncode == 1
    assert "Missing field" in py.stdout
    assert "Missing field" in legacy.stderr


# ---------------------------------------------------------------------------
# Plan parity with the legacy init-session.sh (only when bash available).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not HAS_BASH or _on_windows_with_git_bash(),
    reason="bash parity test requires POSIX bash; skipped on Windows Git Bash.",
)
def test_plan_init_parity_with_legacy_bash(tmp_path: Path) -> None:
    py = _py(["plan", "init", "parity"], tmp_path)
    assert py.returncode == 0, py.stderr
    py_dirs = sorted(
        p.name for p in (tmp_path / ".planning").iterdir() if p.is_dir()
    )

    script_path = (REPO_ROOT / "planning-with-files" / "scripts" / "init-session.sh").as_posix()
    legacy = _run(
        ["bash", script_path, "--plan-dir", "parity"],
        cwd=tmp_path,
    )
    assert legacy.returncode == 0, legacy.stderr

    legacy_dirs = sorted(
        p.name for p in (tmp_path / ".planning").iterdir() if p.is_dir()
    )

    # Both should leave at least one .planning/<date>-parity/ directory.
    assert any(d.endswith("-parity") for d in py_dirs)
    assert any(d.endswith("-parity") for d in legacy_dirs)


def _on_windows_with_git_bash() -> bool:
    import os
    import sys

    if sys.platform != "win32":
        return False
    bash_path = shutil.which("bash") or ""
    return "Git" in bash_path or "MSYS" in os.environ.get("MSYSTEM", "")


def test_cli_help_lists_all_subcommands() -> None:
    """Smoke test for the top-level command tree used in parity docs."""
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for sub in (
        "init",
        "governed-start",
        "packet",
        "entry",
        "plan",
        "check",
        "status",
        "verify",
        "review",
        "config",
        "runner",
    ):
        assert sub in result.output, f"missing subcommand in --help: {sub}"