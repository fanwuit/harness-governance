"""Role and subagent isolation — Gap 1 of the v0.8.0 governance release.

Creates per-role working directories under ``.harness/isolation/`` and
records cross-role file-access events to ``.isolation.ndjson``.  The
READINESS gate hook validates that all roles are isolated and no violations
occurred.

v0.8.0 enforcement is **detective** (post-hoc logging), not preventive
(sandboxing).  Future versions may add OS-level sandboxing.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..file_ops.ndjson_writer import NDJSONWriter
from ..models.schemas import IsolationRecord, IsolationSummary, IsolationWorkspace

logger = logging.getLogger("harness.isolation")

# Canonical role list — maps to the roles the orchestrator dispatches.
_CANONICAL_ROLES = (
    "planner",
    "spec-writer",
    "contract-writer",
    "test-writer",
    "product-implementer",
    "implementer",
    "verifier",
    "reviewer",
)

# Default allowed paths per role (glob patterns relative to project root).
_DEFAULT_ROLE_PATHS: dict[str, list[str]] = {
    "planner": [
        "docs/briefs/**",
        "docs/architecture/**",
        "docs/adr/**",
        "docs/facts/**",
        "docs/brainstorming/**",
        ".harness/**",
        "*.md",
    ],
    "spec-writer": [
        "docs/changes/*/proposal.md",
        ".harness/specs/**",
        ".harness/**",
    ],
    "contract-writer": [
        "docs/contracts/**",
        "docs/briefs/**",
        "docs/adr/**",
        "docs/changes/*/contracts.md",
        "src/**/contracts/**",
        ".harness/**",
    ],
    "test-writer": [
        "docs/changes/*/tests.md",
        "tests/**",
        "fixtures/**",
        "e2e/**",
        "playwright/**",
        ".harness/**",
    ],
    "product-implementer": [
        "src/**",
        "config/**",
        "migrations/**",
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        ".harness/**",
    ],
    "implementer": [
        "src/**",
        "docs/adr/**",
        ".harness/**",
    ],
    "verifier": [
        "docs/changes/*/verification.md",
        "docs/verification/**",
        ".harness/**",
    ],
    "reviewer": [
        "tests/**",
        "docs/**",
        ".harness/**",
    ],
}

# Default allowed cross-role collaboration.
_DEFAULT_ROLE_ALLOWANCES: dict[str, list[str]] = {
    "planner": ["spec-writer", "contract-writer"],
    "spec-writer": ["planner", "contract-writer"],
    "contract-writer": ["planner", "spec-writer", "test-writer"],
    "test-writer": ["contract-writer", "product-implementer", "verifier"],
    "product-implementer": ["test-writer", "verifier"],
    "implementer": ["contract-writer", "reviewer"],
    "verifier": ["test-writer", "product-implementer", "reviewer"],
    "reviewer": ["implementer", "verifier"],
}


class IsolationManager:
    """Create and verify per-role isolation workspaces.

    Usage::

        mgr = IsolationManager(project_root)
        ws = mgr.create_workspace("planner", "sess-abc", "chg-001")
        violations = mgr.check_violations("planner", ["src/main.py"])
        mgr.append_event(record)
        summary = mgr.verify_workspace("sess-abc")
    """

    ISOLATION_DIR = Path(".harness/isolation")

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._ndjson = NDJSONWriter()

    # -- Public API -------------------------------------------------------

    def create_workspace(
        self,
        role: str,
        session_id: str,
        change_id: str = "",
        *,
        allowed_paths: list[str] | None = None,
        allowed_roles: list[str] | None = None,
    ) -> IsolationWorkspace:
        """Create an isolated working directory for *role*.

        Writes ``workspace.json`` into the session-level isolation
        directory so that subsequent checks can read the boundaries.
        """
        session_dir = self._session_dir(session_id)
        role_dir = session_dir / role
        role_dir.mkdir(parents=True, exist_ok=True)

        paths = allowed_paths or _DEFAULT_ROLE_PATHS.get(role, [".harness/**"])
        roles = allowed_roles or _DEFAULT_ROLE_ALLOWANCES.get(role, [])

        ws = IsolationWorkspace(
            role=role,
            workspace_path=str(role_dir.relative_to(self._project_root)),
            isolation_kind="directory",
            session_id=session_id,
            allowed_paths=tuple(paths),
            allowed_roles=tuple(roles),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Persist workspace config.
        self._write_workspace_config(session_id, role, ws)

        # Log creation event.
        self.append_event(
            IsolationRecord(
                event="workspace_created",
                role=role,
                workspace_path=ws.workspace_path,
                session_id=session_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            session_id=session_id,
        )

        return ws

    def check_violations(
        self,
        role: str,
        files_touched: list[str],
        *,
        session_id: str = "",
        cross_role_accesses: list[str] | None = None,
    ) -> list[str]:
        """Return *files_touched* paths that fall outside the role's declared scope.

        Loads the persisted workspace config to get the role's
        ``allowed_paths`` and ``allowed_roles``.
        """
        ws = self._load_workspace_config(session_id, role) if session_id else None

        allowed_globs = (
            list(ws.allowed_paths) if ws else _DEFAULT_ROLE_PATHS.get(role, [])
        )
        violations: list[str] = []

        for file_path in files_touched:
            if not self._matches_any_glob(file_path, allowed_globs):
                violations.append(file_path)

        # Also check cross-role access.
        if cross_role_accesses and ws:
            allowed_roles = set(ws.allowed_roles)
            for accessed_role in cross_role_accesses:
                if accessed_role not in allowed_roles and accessed_role != role:
                    violations.append(f"cross-role:{accessed_role}")

        return violations

    def append_event(
        self,
        record: IsolationRecord,
        session_id: str = "",
    ) -> bool:
        """Append an isolation event to the NDJSON log.

        Events are written under ``.harness/isolation/<session_id>/.isolation.ndjson``.
        """
        log_path = self._ndjson_path(session_id)
        data = record.model_dump(exclude_none=True)
        return self._ndjson.append(log_path, data)

    def verify_workspace(self, session_id: str) -> IsolationSummary:
        """Read the isolation event log and produce a verification summary.

        Returns an ``IsolationSummary`` that the READINESS gate hook
        can inspect for violations.
        """
        log_path = self._ndjson_path(session_id)
        records = self._read_events(log_path)

        roles_found: set[str] = set()
        violations: list[IsolationRecord] = []
        out_of_scope: set[str] = set()

        for rec in records:
            roles_found.add(rec.role)
            if rec.event == "violation_detected":
                violations.append(rec)
                out_of_scope.update(rec.files_touched)

        # Also read workspace configs to find all roles.
        session_dir = self._session_dir(session_id)
        if session_dir.exists():
            for ws_file in session_dir.glob("*/workspace.json"):
                try:
                    cfg = json.loads(ws_file.read_text(encoding="utf-8"))
                    roles_found.add(cfg.get("role", ""))
                except Exception:
                    pass

        return IsolationSummary(
            roles_isolated=tuple(sorted(roles_found)),
            cross_role_violations=tuple(violations),
            files_outside_scope=tuple(sorted(out_of_scope)),
            workspaces_valid=len(violations) == 0,
            enforcement_level="detective",
        )

    def load_workspace(self, session_id: str, role: str) -> IsolationWorkspace | None:
        """Load the persisted workspace config for *role* in *session_id*."""
        return self._load_workspace_config(session_id, role)

    # -- Internal ---------------------------------------------------------

    def _session_dir(self, session_id: str) -> Path:
        return self._project_root / self.ISOLATION_DIR / session_id

    def _ndjson_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / ".isolation.ndjson"

    def _workspace_config_path(self, session_id: str, role: str) -> Path:
        return self._session_dir(session_id) / role / "workspace.json"

    def _write_workspace_config(
        self, session_id: str, role: str, ws: IsolationWorkspace
    ) -> None:
        path = self._workspace_config_path(session_id, role)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ws.model_dump_json(indent=2), encoding="utf-8")

    def _load_workspace_config(
        self, session_id: str, role: str
    ) -> IsolationWorkspace | None:
        path = self._workspace_config_path(session_id, role)
        if not path.is_file():
            return None
        try:
            return IsolationWorkspace.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except Exception:
            logger.warning("Failed to parse workspace config: %s", path, exc_info=True)
            return None

    @staticmethod
    def _read_events(log_path: Path) -> list[IsolationRecord]:
        """Parse all NDJSON isolation records from *log_path*."""
        records: list[IsolationRecord] = []
        if not log_path.is_file():
            return records
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(IsolationRecord.model_validate_json(line))
            except Exception:
                logger.debug("Skipping unparseable isolation event", exc_info=True)
        return records

    @staticmethod
    def _matches_any_glob(file_path: str, patterns: list[str]) -> bool:
        """Return True if *file_path* matches any of the glob *patterns*."""
        from fnmatch import fnmatch

        for pat in patterns:
            if fnmatch(file_path, pat):
                return True
        return False


# ---------------------------------------------------------------------------
# Gate hook registration — called at import time
# ---------------------------------------------------------------------------


def _gate_hook_isolation(
    session,  # SessionState
    project_root: Path,
) -> list[str]:
    """READINESS hook: verify isolation workspaces and check for violations.

    Returns a list of failure message strings (empty = all passed).
    """
    failures: list[str] = []
    mgr = IsolationManager(project_root)
    session_id = getattr(session, "session_id", "")

    if not session_id:
        return failures  # no session → nothing to check

    summary = mgr.verify_workspace(session_id)

    # Require at least one role workspace exists.
    if not summary.roles_isolated:
        failures.append(
            "No isolation workspaces found — run 'harness isolation init' "
            "to create per-role workspaces before implementation."
        )

    # Check for cross-role violations.
    if summary.cross_role_violations:
        for v in summary.cross_role_violations[:5]:  # cap at 5 messages
            failures.append(
                f"Isolation violation: role '{v.role}' accessed "
                f"{', '.join(v.files_touched) if v.files_touched else 'cross-role resources'}"
            )

    # Check for out-of-scope files.
    if summary.files_outside_scope:
        failures.append(
            f"Files accessed outside declared scope: "
            f"{', '.join(list(summary.files_outside_scope)[:10])}"
        )

    return failures


# Module-level registration — fires when isolation is imported.
try:
    from .gates import HarnessLayer, register_gate_hook

    register_gate_hook(HarnessLayer.READINESS, _gate_hook_isolation)
except ImportError:
    pass
