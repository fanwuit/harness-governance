"""Structured result parser for subagent outputs.

Parses the JSON output from subagent role executions (implementer,
reviewer, planner, contract-writer) into :class:`SubagentResult`
dataclass instances. Also provides helpers to append parsed results
to the invocation log.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class SubagentResult:
    """Parsed structured output from a subagent role execution."""

    role: str
    raw_json: dict
    files_changed: list[str] = field(default_factory=list)
    summary: str = ""

    # Implementer / Contract Writer
    contract_blocked: bool = False
    verification_results: list[dict] = field(default_factory=list)
    open_risks: list[str] = field(default_factory=list)

    # Reviewer specific
    verdict: str | None = (
        None  # accept|accept_with_advisory|reject|insufficient_evidence
    )
    findings: list[dict] = field(default_factory=list)
    residual_risks: list[str] = field(default_factory=list)

    # Planner specific
    scope: str = ""
    owner_files: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    non_goals: list[str] = field(default_factory=list)
    forbidden_shortcuts: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)

    # Contract Writer specific
    contracts_defined: list[str] = field(default_factory=list)
    acceptance_checks: list[str] = field(default_factory=list)

    # v0.8.0 Gap 1 — Role isolation (isolation.py)
    isolation_workspace: str | None = None
    isolation_violations: list[str] = field(default_factory=list)

    # v0.8.0 Gap 3 — Scope drift (drift.py)
    actual_scope: list[str] = field(default_factory=list)
    scope_violations: list[str] = field(default_factory=list)

    # v0.8.0 Gap 5 — Skill chain tracing (skill_chain.py)
    parent_skill: str = ""
    skill_call_id: str = ""
    parent_call_id: str | None = None

    @staticmethod
    def generate_call_id() -> str:
        """Return a new unique skill-call identifier (UUID4 hex)."""
        return uuid.uuid4().hex

    @property
    def verification_passed(self) -> bool:
        """True if all verification results are 'passed'."""
        if not self.verification_results:
            return False
        return all(
            r.get("status", "").lower() == "passed" for r in self.verification_results
        )

    @property
    def has_blocking_findings(self) -> bool:
        """True if any reviewer finding has severity 'blocking'."""
        return any(f.get("severity", "").lower() == "blocking" for f in self.findings)

    @property
    def is_acceptable(self) -> bool:
        """True if the result can advance the queue."""
        if self.contract_blocked:
            return False
        if self.verdict in ("reject", "insufficient_evidence"):
            return False
        if self.has_blocking_findings:
            return False
        return True

    def to_ndjson(self, *, round_index: int = 0, queue_item: str = "") -> str:
        """Serialize to an NDJSON line for the invocation log."""
        return json.dumps(
            {
                "round": round_index,
                "queueItem": queue_item,
                "role": self.role,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "filesChanged": self.files_changed,
                "summary": self.summary,
                "contractBlocked": self.contract_blocked,
                "verdict": self.verdict,
                "verificationPassed": self.verification_passed,
                "findingsCount": len(self.findings),
                "openRisks": self.open_risks,
            },
            ensure_ascii=False,
        )


class ResultParser:
    """Parse subagent output into :class:`SubagentResult`."""

    def parse(self, output: str, role: str = "") -> SubagentResult:
        """Parse subagent output text into a structured result.

        Tries three strategies in order:
        1. Parse the entire output as JSON.
        2. Find a JSON code block (```json ... ```) in the output.
        3. Find a JSON object by matching ``{`` ... ``}`` braces.

        If all strategies fail, returns a minimal result with the raw
        text as summary and ``role`` as specified.
        """
        data = self._try_parse_json(output)
        if data is None:
            return SubagentResult(
                role=role or "unknown",
                raw_json={},
                summary=output[:500],
            )

        return self._from_dict(data, role)

    def parse_file(self, path: Path, role: str = "") -> SubagentResult:
        """Parse a result file."""
        text = path.read_text(encoding="utf-8")
        return self.parse(text, role=role)

    # Internal ---------------------------------------------------------------

    def _try_parse_json(self, output: str) -> dict | None:
        """Try multiple strategies to extract JSON from output."""
        # Strategy 1: entire output is JSON
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: JSON code block
        code_block = re.search(r"```(?:json)?\s*\n(.*?)\n```", output, re.DOTALL)
        if code_block:
            try:
                data = json.loads(code_block.group(1))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 3: find first { ... } pair
        brace_match = re.search(r"\{[\s\S]*?\}", output)
        if brace_match:
            try:
                data = json.loads(brace_match.group(0))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, ValueError):
                pass

        return None

    def _from_dict(self, data: dict, role: str = "") -> SubagentResult:
        """Build a SubagentResult from a parsed JSON dict."""
        detected_role = data.get("role", role) or role

        result = SubagentResult(
            role=detected_role,
            raw_json=data,
            files_changed=data.get("filesChanged", []),
            summary=data.get("summary", ""),
            contract_blocked=data.get("contractBlocked", False),
            verification_results=data.get("verificationResults", []),
            open_risks=data.get("openRisks", []),
        )

        # Reviewer fields
        if "verdict" in data:
            result.verdict = data["verdict"]
        if "findings" in data:
            result.findings = data["findings"]
        if "residualRisks" in data:
            result.residual_risks = data["residualRisks"]

        # Planner fields
        if "scope" in data:
            result.scope = data["scope"]
        if "ownerFiles" in data:
            result.owner_files = data["ownerFiles"]
        if "successCriteria" in data:
            result.success_criteria = data["successCriteria"]
        if "nonGoals" in data:
            result.non_goals = data["nonGoals"]
        if "forbiddenShortcuts" in data:
            result.forbidden_shortcuts = data["forbiddenShortcuts"]
        if "verificationCommands" in data:
            result.verification_commands = data["verificationCommands"]
        if "stopConditions" in data:
            result.stop_conditions = data["stopConditions"]

        # Contract Writer fields
        if "contractsDefined" in data:
            result.contracts_defined = data["contractsDefined"]
        if "acceptanceChecks" in data:
            result.acceptance_checks = data["acceptanceChecks"]

        return result


def append_invocation_log(
    log_path: Path,
    result: SubagentResult,
    *,
    round_index: int = 0,
    queue_item: str = "",
) -> None:
    """Append a parsed result as an NDJSON line to the invocation log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            result.to_ndjson(round_index=round_index, queue_item=queue_item) + "\n"
        )


__all__ = [
    "SubagentResult",
    "ResultParser",
    "append_invocation_log",
]
