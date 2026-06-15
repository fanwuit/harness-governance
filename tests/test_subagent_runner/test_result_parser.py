"""Tests for runner/result_parser.py — ResultParser and SubagentResult."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness_governance.runner.result_parser import (
    ResultParser,
    SubagentResult,
    append_invocation_log,
)


@pytest.fixture
def parser() -> ResultParser:
    return ResultParser()


class TestResultParserImplementer:
    def test_parse_implementer_result(self, parser: ResultParser) -> None:
        data = {
            "role": "implementer",
            "filesChanged": ["src/dashboard.py"],
            "summary": "Implemented status dashboard component.",
            "verificationResults": [
                {"command": "npm test", "status": "passed", "evidence": "42 passed"},
            ],
            "contractBlocked": False,
            "openRisks": [],
        }
        result = parser.parse(json.dumps(data), role="implementer")

        assert result.role == "implementer"
        assert result.files_changed == ["src/dashboard.py"]
        assert result.contract_blocked is False
        assert result.verification_passed is True
        assert result.is_acceptable is True

    def test_parse_contract_blocked(self, parser: ResultParser) -> None:
        data = {
            "role": "implementer",
            "filesChanged": [],
            "contractBlocked": True,
            "openRisks": ["Contract X conflicts with existing code"],
        }
        result = parser.parse(json.dumps(data))

        assert result.contract_blocked is True
        assert result.is_acceptable is False


class TestResultParserReviewer:
    def test_parse_accept_verdict(self, parser: ResultParser) -> None:
        data = {
            "role": "reviewer",
            "verdict": "accept",
            "findings": [],
            "verificationResults": [
                {"command": "npm test", "status": "passed", "evidence": "ok"},
            ],
            "residualRisks": [],
        }
        result = parser.parse(json.dumps(data))

        assert result.verdict == "accept"
        assert result.is_acceptable is True
        assert result.has_blocking_findings is False

    def test_parse_reject_verdict(self, parser: ResultParser) -> None:
        data = {
            "role": "reviewer",
            "verdict": "reject",
            "findings": [
                {
                    "severity": "blocking",
                    "file": "src/main.py",
                    "line": 42,
                    "description": "Missing error handling",
                    "contractReference": "contracts.md#error-handling",
                },
            ],
            "verificationResults": [],
            "residualRisks": ["Incomplete error paths"],
        }
        result = parser.parse(json.dumps(data))

        assert result.verdict == "reject"
        assert result.is_acceptable is False
        assert result.has_blocking_findings is True
        assert len(result.findings) == 1

    def test_parse_insufficient_evidence(self, parser: ResultParser) -> None:
        data = {
            "role": "reviewer",
            "verdict": "insufficient_evidence",
            "findings": [],
            "verificationResults": [],
            "residualRisks": [],
        }
        result = parser.parse(json.dumps(data))

        assert result.verdict == "insufficient_evidence"
        assert result.is_acceptable is False

    def test_parse_accept_with_advisory(self, parser: ResultParser) -> None:
        data = {
            "role": "reviewer",
            "verdict": "accept_with_advisory",
            "findings": [
                {"severity": "advisory", "description": "Consider refactoring"},
            ],
            "verificationResults": [],
            "residualRisks": [],
        }
        result = parser.parse(json.dumps(data))

        assert result.verdict == "accept_with_advisory"
        assert result.is_acceptable is True


class TestResultParserPlanner:
    def test_parse_planner_result(self, parser: ResultParser) -> None:
        data = {
            "role": "planner",
            "scope": "Implement status dashboard",
            "ownerFiles": ["src/dashboard.py"],
            "successCriteria": ["Dashboard renders"],
            "nonGoals": ["API changes"],
            "forbiddenShortcuts": ["Direct DB access"],
            "verificationCommands": ["npm test"],
            "stopConditions": ["Context 70%"],
        }
        result = parser.parse(json.dumps(data))

        assert result.role == "planner"
        assert result.scope == "Implement status dashboard"
        assert result.owner_files == ["src/dashboard.py"]
        assert result.success_criteria == ["Dashboard renders"]


class TestResultParserStrategies:
    def test_parse_json_code_block(self, parser: ResultParser) -> None:
        output = 'Some text before\n```json\n{"role": "implementer", "filesChanged": ["a.py"]}\n```\nMore text'
        result = parser.parse(output)

        assert result.role == "implementer"
        assert result.files_changed == ["a.py"]

    def test_parse_bare_json_object(self, parser: ResultParser) -> None:
        output = 'Leading text\n{"role": "reviewer", "verdict": "accept", "findings": []}\nTrailing'
        result = parser.parse(output)

        assert result.role == "reviewer"
        assert result.verdict == "accept"

    def test_parse_non_json(self, parser: ResultParser) -> None:
        output = "Just some plain text output"
        result = parser.parse(output, role="implementer")

        assert result.role == "implementer"
        assert result.raw_json == {}
        assert "plain text" in result.summary

    def test_parse_file(self, parser: ResultParser, tmp_path: Path) -> None:
        data = {"role": "implementer", "filesChanged": ["x.py"]}
        f = tmp_path / "result.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = parser.parse_file(f)
        assert result.role == "implementer"
        assert result.files_changed == ["x.py"]


class TestSubagentResult:
    def test_to_ndjson(self) -> None:
        result = SubagentResult(
            role="implementer",
            raw_json={"role": "implementer"},
            files_changed=["a.py"],
            verification_results=[{"status": "passed"}],
        )
        line = result.to_ndjson(round_index=1, queue_item="test item")
        parsed = json.loads(line)

        assert parsed["round"] == 1
        assert parsed["role"] == "implementer"
        assert parsed["queueItem"] == "test item"
        assert parsed["verificationPassed"] is True

    def test_verification_passed_empty_results(self) -> None:
        result = SubagentResult(role="test", raw_json={})
        assert result.verification_passed is False

    def test_verification_passed_all_passed(self) -> None:
        result = SubagentResult(
            role="test",
            raw_json={},
            verification_results=[
                {"status": "passed"},
                {"status": "passed"},
            ],
        )
        assert result.verification_passed is True

    def test_verification_passed_one_failed(self) -> None:
        result = SubagentResult(
            role="test",
            raw_json={},
            verification_results=[
                {"status": "passed"},
                {"status": "failed"},
            ],
        )
        assert result.verification_passed is False


class TestAppendInvocationLog:
    def test_append_creates_file(self, tmp_path: Path) -> None:
        log_path = tmp_path / ".harness" / "invocations.ndjson"
        result = SubagentResult(
            role="implementer",
            raw_json={},
            files_changed=["a.py"],
        )
        append_invocation_log(log_path, result, round_index=1, queue_item="task")

        assert log_path.is_file()
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["role"] == "implementer"

    def test_append_to_existing(self, tmp_path: Path) -> None:
        log_path = tmp_path / "log.ndjson"
        log_path.write_text('{"existing": true}\n', encoding="utf-8")

        result = SubagentResult(role="reviewer", raw_json={})
        append_invocation_log(log_path, result, round_index=2)

        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
