"""Tests for ``harness runner`` CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_READY_QUEUE = "[ready] Test task\n- Layer: implementation\n- Change: sample-change\n"


def _write_ready_queue(root: Path) -> None:
    """Write a minimal NEXT.md with one [ready] item."""
    (root / "NEXT.md").write_text(_READY_QUEUE, encoding="utf-8")


def test_runner_start_requires_queue_file(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "start",
            "--executor",
            "orchestrator",
        ],
    )

    assert result.exit_code != 0
    assert "Required scheduler queue file is missing" in result.output


# ---------------------------------------------------------------------------
# runner start -- orchestrator executor (lines 150-185)
# ---------------------------------------------------------------------------


def test_runner_start_orchestrator_stdout(tmp_repo: Path) -> None:
    """Orchestrator mode outputs prompt text to stdout."""
    _write_ready_queue(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "start",
            "--executor",
            "orchestrator",
        ],
    )
    assert result.exit_code == 0, result.output
    # The orchestrator prompt should reference the queue item
    assert "Test task" in result.output


def test_runner_start_orchestrator_output_file(tmp_repo: Path) -> None:
    """Orchestrator mode with --output writes prompt to a file."""
    _write_ready_queue(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "start",
            "--executor",
            "orchestrator",
            "--output",
            "orchestrator-prompt.md",
        ],
    )
    assert result.exit_code == 0, result.output
    out_path = tmp_repo / "orchestrator-prompt.md"
    assert out_path.is_file()
    content = out_path.read_text(encoding="utf-8")
    assert "Test task" in content
    assert "Orchestrator prompt written to" in result.output


def test_runner_start_orchestrator_missing_variables(tmp_repo: Path) -> None:
    """Orchestrator mode reports unresolved variables when context is sparse."""
    # Minimal queue item with no change packet -> many template vars unresolved
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Minimal task\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "start",
            "--executor",
            "orchestrator",
        ],
    )
    assert result.exit_code == 0, result.output
    # Warning about unresolved variables (sent to stderr, mixed into output)
    assert "unresolved variables" in result.output


# ---------------------------------------------------------------------------
# runner render (lines 251-329)
# ---------------------------------------------------------------------------


def test_runner_render_implementer(tmp_repo: Path) -> None:
    """Render the implementer role with a valid queue item."""
    _write_ready_queue(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--role",
            "implementer",
        ],
    )
    assert result.exit_code == 0, result.output
    # Should produce rendered template output (non-empty)
    assert len(result.output.strip()) > 0


def test_runner_render_output_file(tmp_repo: Path) -> None:
    """Render with --output writes the rendered prompt to a file."""
    _write_ready_queue(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--role",
            "implementer",
            "--output",
            "rendered-prompt.md",
        ],
    )
    assert result.exit_code == 0, result.output
    out_path = tmp_repo / "rendered-prompt.md"
    assert out_path.is_file()
    content = out_path.read_text(encoding="utf-8")
    assert len(content) > 0
    assert "implementer 提示已渲染并写入" in result.output or "Rendered implementer prompt written to" in result.output


def test_runner_render_no_ready_items(tmp_repo: Path) -> None:
    """Render with no ready/active items should raise ClickException."""
    (tmp_repo / "NEXT.md").write_text(
        "[blocked] Nothing to do\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--role",
            "implementer",
        ],
    )
    assert result.exit_code != 0
    assert "No [ready] or [active] item" in result.output


def test_runner_render_queue_item_infers_role(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Review queue-backed item\n"
        "- Id: review-1\n"
        "- Role: reviewer-verifier\n"
        "- SessionId: review-session\n"
        "- ChangeId: sample-change\n"
        "- ForbiddenScope: src/other.py\n"
        "- VerificationCommands: pytest -q\n"
        "- DoneWhen: review verdict is acceptable\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--queue",
            "review-1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert len(result.output.strip()) > 0
    assert "Role: Reviewer" in result.output or "Role: reviewer" in result.output


def test_runner_render_queue_item_infers_verifier_role(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Verify queue-backed item\n"
        "- Id: verify-1\n"
        "- Role: verifier\n"
        "- ChangeId: sample-change\n"
        "- ForbiddenScope: src/other.py\n"
        "- VerificationCommands: pytest -q\n"
        "- DoneWhen: verification passed\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--queue",
            "verify-1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Role: Verifier" in result.output or "role\": \"verifier\"" in result.output


def test_runner_render_records_session_bound_role(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[active] Implement queue-backed item\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: impl-session\n"
        "- ChangeId: sample-change\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--queue",
            "impl-1",
            "--role",
            "implementer",
            "--session-id",
            "impl-session",
        ],
    )

    assert result.exit_code == 0, result.output
    records = tmp_repo / ".harness" / "render-records" / "impl-session.ndjson"
    assert records.is_file()
    payload = json.loads(records.read_text(encoding="utf-8").splitlines()[0])
    assert payload["role"] == "implementer"
    assert payload["queueId"] == "impl-1"
    assert payload["sessionId"] == "impl-session"


def test_runner_render_records_capability_tier_from_tiers_json(
    tmp_repo: Path,
) -> None:
    (tmp_repo / ".agents").mkdir()
    (tmp_repo / ".agents" / "tiers.json").write_text(
        json.dumps(
            {
                "platform": "codex",
                "adapters": [
                    {
                        "role": "implementer",
                        "required_tier": "execution",
                        "adapter": "subagent",
                        "model_label": "exec-model",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_repo / "NEXT.md").write_text(
        "[active] Implement queue-backed item\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: impl-session\n"
        "- ChangeId: sample-change\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--queue",
            "impl-1",
            "--role",
            "implementer",
            "--session-id",
            "impl-session",
        ],
    )

    assert result.exit_code == 0, result.output
    records = tmp_repo / ".harness" / "render-records" / "impl-session.ndjson"
    payload = json.loads(records.read_text(encoding="utf-8").splitlines()[0])
    assert payload["requiredTier"] == "execution"
    assert payload["actualTier"] == "execution"
    assert payload["verifierRequired"] is True
    assert payload["platform"] == "codex"
    assert payload["adapter"] == "subagent"
    assert payload["modelLabel"] == "exec-model"


def test_runner_render_rejects_session_mismatch(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[active] Implement queue-backed item\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: impl-session\n"
        "- ChangeId: sample-change\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--queue",
            "impl-1",
            "--role",
            "implementer",
            "--session-id",
            "other-session",
        ],
    )

    assert result.exit_code != 0
    assert "sessionId" in result.output


# ---------------------------------------------------------------------------
# runner parse-result (lines 332-404)
# ---------------------------------------------------------------------------

_SUBAGENT_RESULT = {
    "role": "implementer",
    "filesChanged": ["src/main.py"],
    "contractBlocked": False,
    "verdict": "acceptable",
    "verificationPassed": True,
    "findings": [],
}


def test_runner_parse_result_from_file(tmp_repo: Path) -> None:
    """Parse a JSON subagent result from --input file and echo summary."""
    input_file = tmp_repo / "result.json"
    input_file.write_text(json.dumps(_SUBAGENT_RESULT), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "parse-result",
            "--role",
            "implementer",
            "--input",
            "result.json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["role"] == "implementer"
    assert data["filesChanged"] == ["src/main.py"]
    assert data["contractBlocked"] is False
    assert data["verdict"] == "acceptable"
    assert data["findingsCount"] == 0


def test_runner_parse_result_appends_invocation_log(tmp_repo: Path) -> None:
    """parse-result should append an NDJSON entry to the invocation log."""
    input_file = tmp_repo / "result.json"
    input_file.write_text(json.dumps(_SUBAGENT_RESULT), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "parse-result",
            "--role",
            "implementer",
            "--input",
            "result.json",
            "--invocation-log",
            ".harness/invocations.ndjson",
            "--round",
            "3",
        ],
    )
    assert result.exit_code == 0, result.output

    log_path = tmp_repo / ".harness" / "invocations.ndjson"
    assert log_path.is_file()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["role"] == "implementer"
    assert record["round"] == 3
    assert record["filesChanged"] == ["src/main.py"]
