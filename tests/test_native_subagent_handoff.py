"""Contract tests for native subagent handoff runner behaviour."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.hard_gates import native_handoff_gate_failures


def _write_project(root: Path) -> None:
    (root / ".agents").mkdir()
    (root / ".agents" / "tiers.json").write_text(
        json.dumps(
            {
                "platform": "codex",
                "adapters": [
                    {
                        "role": "reviewer-verifier",
                        "required_tier": "strong",
                        "adapter": "subagent",
                        "model_label": "strong-model",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "NEXT.md").write_text(
        "[active] Review native handoff\n"
        "- Id: review-1\n"
        "- Role: reviewer-verifier\n"
        "- SessionId: native-session\n"
        "- ChangeId: native-change\n"
        "- Forbidden scope: do not touch platform executors\n"
        "- Verification commands: pytest tests/test_native_subagent_handoff.py -q\n"
        "- Done when: native handoff lifecycle is gateable\n",
        encoding="utf-8",
    )
    packet = root / "docs" / "changes" / "native-change"
    packet.mkdir(parents=True)
    (packet / "tasks.md").write_text(
        "# Tasks\n\n"
        "## Owner Files\n\n"
        "src/harness_governance/commands/runner.py\n\n"
        "## Allowed Scope\n\n"
        "native handoff runner lifecycle\n\n"
        "## Forbidden Scope\n\n"
        "platform executor fallback\n\n"
        "## Verification Commands\n\n"
        "pytest tests/test_native_subagent_handoff.py -q\n\n"
        "## Done When\n\n"
        "native handoff lifecycle is gateable\n",
        encoding="utf-8",
    )
    (packet / "contracts.md").write_text(
        "# Contracts\n\n- Native handoff only.\n",
        encoding="utf-8",
    )


def test_prepare_native_writes_request_and_prompt(tmp_path: Path) -> None:
    _write_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "prepare-native",
            "--role",
            "reviewer-verifier",
            "--queue",
            "review-1",
            "--session-id",
            "native-session",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    request_path = tmp_path / payload["requestPath"]
    prompt_path = tmp_path / payload["promptPath"]
    assert request_path.is_file()
    assert prompt_path.is_file()
    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request["sessionId"] == "native-session"
    assert request["queueId"] == "review-1"
    assert request["role"] == "reviewer-verifier"
    assert request["platform"] == "codex"
    assert request["adapter"] == "subagent"
    assert request["status"] == "prepared"
    assert len(request["promptSha256"]) == 64


def test_prepare_native_rejects_subprocess_adapter(tmp_path: Path) -> None:
    _write_project(tmp_path)
    tiers = tmp_path / ".agents" / "tiers.json"
    data = json.loads(tiers.read_text(encoding="utf-8"))
    data["adapters"][0]["adapter"] = "subprocess"
    tiers.write_text(json.dumps(data), encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "prepare-native",
            "--role",
            "reviewer-verifier",
            "--queue",
            "review-1",
            "--session-id",
            "native-session",
        ],
    )

    assert result.exit_code != 0
    assert "native subagent" in result.output.lower()


def test_record_spawn_and_parse_result_correlate_records(tmp_path: Path) -> None:
    _write_project(tmp_path)
    runner = CliRunner()
    prepared = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "prepare-native",
            "--role",
            "reviewer-verifier",
            "--queue",
            "review-1",
            "--session-id",
            "native-session",
        ],
    )
    assert prepared.exit_code == 0, prepared.output
    request_id = json.loads(prepared.output)["requestId"]

    spawned = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "record-native-spawn",
            "--session-id",
            "native-session",
            "--role",
            "reviewer-verifier",
            "--request-id",
            request_id,
            "--agent-id",
            "agent-123",
            "--status",
            "spawned",
        ],
    )
    assert spawned.exit_code == 0, spawned.output

    result_file = tmp_path / "reviewer-result.json"
    result_file.write_text(
        json.dumps(
            {
                "role": "reviewer",
                "verdict": "accept",
                "findings": [],
                "verificationResults": [
                    {"command": "pytest -q", "status": "passed", "evidence": "ok"}
                ],
            }
        ),
        encoding="utf-8",
    )
    parsed = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "parse-result",
            "--role",
            "reviewer-verifier",
            "--session-id",
            "native-session",
            "--request-id",
            request_id,
            "--agent-id",
            "agent-123",
            "--input",
            str(result_file),
        ],
    )

    assert parsed.exit_code == 0, parsed.output
    payload = json.loads(parsed.output)
    assert payload["requestId"] == request_id
    assert payload["agentId"] == "agent-123"
    assert payload["verdict"] == "accept"
    assert payload["verificationPassed"] is True


def test_parse_result_rejects_completion_role_mismatch(tmp_path: Path) -> None:
    _write_project(tmp_path)
    runner = CliRunner()
    prepared = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "prepare-native",
            "--role",
            "reviewer-verifier",
            "--queue",
            "review-1",
            "--session-id",
            "native-session",
        ],
    )
    assert prepared.exit_code == 0, prepared.output
    request_id = json.loads(prepared.output)["requestId"]
    spawned = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "record-native-spawn",
            "--session-id",
            "native-session",
            "--role",
            "reviewer-verifier",
            "--request-id",
            request_id,
            "--agent-id",
            "agent-123",
        ],
    )
    assert spawned.exit_code == 0, spawned.output
    result_file = tmp_path / "reviewer-result.json"
    result_file.write_text(
        json.dumps(
            {
                "role": "reviewer",
                "verdict": "accept",
                "verificationResults": [
                    {"command": "pytest -q", "status": "passed", "evidence": "ok"}
                ],
                "findings": [],
            }
        ),
        encoding="utf-8",
    )

    parsed = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "parse-result",
            "--role",
            "reviewer",
            "--session-id",
            "native-session",
            "--request-id",
            request_id,
            "--agent-id",
            "agent-123",
            "--input",
            str(result_file),
        ],
    )

    assert parsed.exit_code != 0
    assert "does not match completion role" in parsed.output


def test_runner_start_no_longer_accepts_process_executors(tmp_path: Path) -> None:
    _write_project(tmp_path)

    for executor in ("subprocess", "codex"):
        result = CliRunner().invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "runner",
                "start",
                "--executor",
                executor,
            ],
        )
        assert result.exit_code != 0


def test_reviewer_prepare_fails_when_required_fields_missing(tmp_path: Path) -> None:
    _write_project(tmp_path)
    (tmp_path / "NEXT.md").write_text(
        "[active] Review incomplete\n"
        "- Id: review-1\n"
        "- Role: reviewer-verifier\n"
        "- SessionId: native-session\n"
        "- ChangeId: native-change\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "changes" / "native-change" / "tasks.md").write_text(
        "# Tasks\n\n## Owner Files\n\nsrc/harness_governance/commands/runner.py\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "prepare-native",
            "--role",
            "reviewer-verifier",
            "--queue",
            "review-1",
            "--session-id",
            "native-session",
        ],
    )

    assert result.exit_code != 0
    assert "FORBIDDEN_SCOPE" in result.output


def test_native_handoff_gate_requires_complete_lifecycle(tmp_path: Path) -> None:
    _write_project(tmp_path)
    (tmp_path / "NEXT.md").write_text(
        "[active] Review native handoff\n"
        "- Id: review-1\n"
        "- Role: reviewer-verifier\n"
        "- RolePlan: reviewer-verifier\n"
        "- SessionId: native-session\n"
        "- ChangeId: native-change\n"
        "- Forbidden scope: do not touch platform executors\n"
        "- Verification commands: pytest tests/test_native_subagent_handoff.py -q\n"
        "- Done when: native handoff lifecycle is gateable\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    prepared = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "prepare-native",
            "--role",
            "reviewer-verifier",
            "--queue",
            "review-1",
            "--session-id",
            "native-session",
        ],
    )
    assert prepared.exit_code == 0, prepared.output
    request_id = json.loads(prepared.output)["requestId"]
    assert native_handoff_gate_failures(tmp_path, "native-session") == [
        "Missing native spawn record for role reviewer-verifier."
    ]

    spawned = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "record-native-spawn",
            "--session-id",
            "native-session",
            "--role",
            "reviewer-verifier",
            "--request-id",
            request_id,
            "--agent-id",
            "agent-123",
        ],
    )
    assert spawned.exit_code == 0, spawned.output
    assert native_handoff_gate_failures(tmp_path, "native-session") == [
        "Missing parse-result completion record for role reviewer-verifier."
    ]

    result_file = tmp_path / "reviewer-result.json"
    result_file.write_text(
        json.dumps(
            {
                "role": "reviewer",
                "verdict": "accept",
                "verificationResults": [
                    {"command": "pytest -q", "status": "passed", "evidence": "ok"}
                ],
                "findings": [],
            }
        ),
        encoding="utf-8",
    )
    parsed = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "runner",
            "parse-result",
            "--role",
            "reviewer-verifier",
            "--session-id",
            "native-session",
            "--request-id",
            request_id,
            "--agent-id",
            "agent-123",
            "--input",
            str(result_file),
        ],
    )
    assert parsed.exit_code == 0, parsed.output
    assert native_handoff_gate_failures(tmp_path, "native-session") == []
