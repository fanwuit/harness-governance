"""Queue validation and role-isolation checks."""

from __future__ import annotations

from pathlib import Path

from .config import load_config
from .file_ops.queue import read_queue
from .queue_policy import load_queue_policy
from .models.schemas import CheckFinding, CheckResult, QueueItem

_VALID_STATUSES = {"planned", "ready", "active", "blocked", "done", "not-now"}
_MVP_ROLES = {"implementer", "reviewer-verifier"}


def _target(item: QueueItem, index: int) -> str:
    return item.id or item.session_id or item.change_id or f"queue item #{index}"


def _has_waiver(item: QueueItem) -> bool:
    text = item.raw.lower()
    return "role-isolation waiver" in text or "reviewer waiver" in text


def _item_by_id(items: list[QueueItem]) -> dict[str, QueueItem]:
    result: dict[str, QueueItem] = {}
    for item in items:
        if item.id:
            result[item.id] = item
        if item.session_id:
            result.setdefault(item.session_id, item)
        if item.change_id:
            result.setdefault(item.change_id, item)
    return result


def _policy_expected_role(item: QueueItem, policy) -> str | None:
    if item.layer and item.layer.value in policy.role_required_by_layer:
        return policy.role_required_by_layer[item.layer.value]
    if item.change_kind and item.change_kind.lower() in policy.role_required_by_change_kind:
        return policy.role_required_by_change_kind[item.change_kind.lower()]
    return None


def validate_queue(repo_root: Path) -> CheckResult:
    """Validate queue item syntax and MVP structured fields."""
    cfg = load_config(repo_root)
    items = read_queue(cfg.queue_file)
    try:
        policy = load_queue_policy(repo_root)
    except ValueError as exc:
        return CheckResult(
            check="queue",
            passed=False,
            findings=(
                CheckFinding(
                    check="queue",
                    target=".harness/queue-policy.json",
                    level="error",
                    message=str(exc),
                ),
            ),
            inspected=0,
        )
    item_by_id = _item_by_id(items)
    findings: list[CheckFinding] = []

    for index, item in enumerate(items, start=1):
        target = _target(item, index)
        if item.status and item.status not in _VALID_STATUSES:
            findings.append(
                CheckFinding(
                    check="queue",
                    target=target,
                    level="error",
                    message=(
                        f"Invalid queue status '{item.status}'. Use one of: "
                        + ", ".join(sorted(_VALID_STATUSES))
                    ),
                )
            )
        if item.role and item.role not in _MVP_ROLES:
            findings.append(
                CheckFinding(
                    check="queue",
                    target=target,
                    level="error",
                    message=(
                        f"Unsupported MVP queue role '{item.role}'. Use "
                        "implementer or reviewer-verifier."
                    ),
                )
            )
        if item.role:
            for field_name, field_value in (
                ("id", item.id),
                ("sessionId", item.session_id),
            ):
                if not field_value:
                    findings.append(
                        CheckFinding(
                            check="queue",
                            target=target,
                            level="error",
                            message=(
                                f"Structured queue item with role={item.role} "
                                f"must declare {field_name}."
                            ),
                        )
                    )

        expected_role = _policy_expected_role(item, policy)
        if expected_role and item.role != expected_role:
            findings.append(
                CheckFinding(
                    check="queue",
                    target=target,
                    level="error",
                    message=(
                        f"Queue role must be {expected_role!r} for this layer or "
                        f"change kind, not {item.role!r}."
                    ),
                )
            )

        if item.verification:
            preset = None
            if item.role and item.role in policy.verification_presets:
                preset = policy.verification_presets[item.role]
            elif item.layer and item.layer.value in policy.verification_presets:
                preset = policy.verification_presets[item.layer.value]
            if preset and preset not in item.verification:
                findings.append(
                    CheckFinding(
                        check="queue",
                        target=target,
                        level="error",
                        message=(
                            f"Verification must include preset {preset!r}."
                        ),
                    )
                )
        else:
            preset = None
            if item.role and item.role in policy.verification_presets:
                preset = policy.verification_presets[item.role]
            elif item.layer and item.layer.value in policy.verification_presets:
                preset = policy.verification_presets[item.layer.value]
            if preset:
                findings.append(
                    CheckFinding(
                        check="queue",
                        target=target,
                        level="error",
                        message=(
                            f"Verification preset {preset!r} requires a "
                            "Verification field."
                        ),
                    )
                )

        if item.owner_files and policy.forbidden_owner_overlap:
            owner_set = {path.lower() for path in item.owner_files}
            for forbidden in policy.forbidden_owner_overlap:
                overlap = {path.lower() for path in forbidden} & owner_set
                if len(overlap) > 1:
                    findings.append(
                        CheckFinding(
                            check="queue",
                            target=target,
                            level="error",
                            message=(
                                "Owner files violate forbidden overlap policy: "
                                + ", ".join(sorted(overlap))
                            ),
                        )
                    )

        if item.gate_id:
            dep_items = [item_by_id.get(dep_id) for dep_id in item.depends_on]
            dep_gate_ids = {
                dep.gate_id.lower()
                for dep in dep_items
                if dep and dep.gate_id
            }
            for parent_gate, children in policy.child_gate_ordering.items():
                if item.gate_id.lower() not in children:
                    continue
                index = children.index(item.gate_id.lower())
                expected_parent = parent_gate if index == 0 else children[index - 1]
                if expected_parent not in dep_gate_ids:
                    findings.append(
                        CheckFinding(
                            check="queue",
                            target=target,
                            level="error",
                            message=(
                                f"Gate {item.gate_id!r} must depend on gate "
                                f"{expected_parent!r} before advancing."
                            ),
                        )
                    )
                break

    return CheckResult(
        check="queue",
        passed=not findings,
        findings=tuple(findings),
        inspected=len(items),
    )


def check_role_isolation(repo_root: Path) -> CheckResult:
    """Check implementation/review queue separation for structured items."""
    cfg = load_config(repo_root)
    items = read_queue(cfg.queue_file)
    try:
        policy = load_queue_policy(repo_root)
    except ValueError as exc:
        return CheckResult(
            check="role-isolation",
            passed=False,
            findings=(
                CheckFinding(
                    check="role-isolation",
                    target=".harness/queue-policy.json",
                    level="error",
                    message=str(exc),
                ),
            ),
            inspected=0,
        )
    by_id = _item_by_id(items)
    findings: list[CheckFinding] = []

    implementers = [
        item for item in items if item.role == "implementer" and item.status == "done"
    ]
    reviewers = [item for item in items if item.role == "reviewer-verifier"]

    for index, reviewer in enumerate(reviewers, start=1):
        target = _target(reviewer, index)
        if not reviewer.depends_on:
            findings.append(
                CheckFinding(
                    check="role-isolation",
                    target=target,
                    level="error",
                    message="reviewer-verifier queue item must dependOn an implementation item.",
                )
            )
            continue

        deps = [by_id.get(dep_id) for dep_id in reviewer.depends_on]
        missing = [
            dep_id for dep_id, dep in zip(reviewer.depends_on, deps, strict=False) if dep is None
        ]
        for dep_id in missing:
            findings.append(
                CheckFinding(
                    check="role-isolation",
                    target=target,
                    level="error",
                    message=f"dependsOn item '{dep_id}' does not exist.",
                )
            )

        implementation_deps = [dep for dep in deps if dep and dep.role == "implementer"]
        if not implementation_deps:
            findings.append(
                CheckFinding(
                    check="role-isolation",
                    target=target,
                    level="error",
                    message="reviewer-verifier must dependOn an implementer item.",
                )
            )
        for dep in implementation_deps:
            if dep.status != "done":
                findings.append(
                    CheckFinding(
                        check="role-isolation",
                        target=target,
                        level="error",
                        message=(
                            f"dependsOn implementation item '{_target(dep, 0)}' "
                            "must be done before review."
                        ),
                    )
                )
            if dep.session_id and reviewer.session_id == dep.session_id:
                findings.append(
                    CheckFinding(
                        check="role-isolation",
                        target=target,
                        level="error",
                        message=(
                            "reviewer-verifier sessionId must differ from the "
                            "implementation sessionId."
                        ),
                    )
                )
        expected_role = _policy_expected_role(reviewer, policy)
        if expected_role and reviewer.role != expected_role:
            findings.append(
                CheckFinding(
                    check="role-isolation",
                    target=target,
                    level="error",
                    message=(
                        f"Queue role must be {expected_role!r} for this gate."
                    ),
                )
            )

    for item in implementers:
        target = _target(item, 0)
        if _has_waiver(item):
            continue
        has_review = any(
            reviewer.role == "reviewer-verifier"
            and target in reviewer.depends_on
            for reviewer in reviewers
        )
        if not has_review:
            findings.append(
                CheckFinding(
                    check="role-isolation",
                    target=target,
                    level="error",
                    message=(
                        "Done implementer item requires a reviewer-verifier queue "
                        "item depending on it, or a role-isolation waiver."
                    ),
                )
            )
        if item.role and item.role in policy.verification_presets:
            preset = policy.verification_presets[item.role]
            if not item.verification or preset not in item.verification:
                findings.append(
                    CheckFinding(
                        check="role-isolation",
                        target=target,
                        level="error",
                        message=(
                            f"Verification must include preset {preset!r}."
                        ),
                    )
                )

    for index, item in enumerate(items, start=1):
        if item.status != "done":
            continue
        target = _target(item, index)
        if item.role in _MVP_ROLES and not (item.evidence or item.verification):
            findings.append(
                CheckFinding(
                    check="role-isolation",
                    target=target,
                    level="error",
                    message=(
                        "Done queue items must record evidence or verification "
                        "content."
                    ),
                )
            )

    return CheckResult(
        check="role-isolation",
        passed=not findings,
        findings=tuple(findings),
        inspected=len(items),
    )


__all__ = ["check_role_isolation", "validate_queue"]
