"""Internationalized CLI messages for ``harness-governance``.

The CLI speaks English by default. Setting the ``HARNESS_LANG`` environment
variable to ``zh-CN`` (or passing ``--lang zh-CN`` on the top-level CLI)
switches the user-facing strings to Chinese; when Chinese is active,
each message is rendered bilingually as ``中文 / English`` so a
mixed-language team can still grep the English text.

The translation table is intentionally flat (a :class:`dict` keyed by
message ID) — every user-visible string in the project is registered
here so it is easy to audit completeness and add more languages later.
"""

from __future__ import annotations

import os
from typing import Any, Mapping


SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "zh-CN")


def detect_language() -> str:
    """Return the active language code.

    Honors the ``HARNESS_LANG`` environment variable. Falls back to
    English when the value is unknown or unset.
    """
    raw = os.environ.get("HARNESS_LANG", "").strip()
    if raw in SUPPORTED_LANGUAGES:
        return raw
    return "en"


# ---------------------------------------------------------------------------
# Message catalog
# ---------------------------------------------------------------------------
#
# Each entry: message_id -> {"en": str, "zh-CN": str}
#
# Use ``{name}`` placeholders for runtime interpolation. Keep English
# terse (CLI line budget matters); keep Chinese idiomatic.

_MESSAGES: dict[str, Mapping[str, str]] = {
    # init -----------------------------------------------------------------
    "init.detected": {
        "en": "Detected: {platform}",
        "zh-CN": "检测到: {platform}",
    },
    "init.config_created": {
        "en": "Created: {path}",
        "zh-CN": "已创建配置: {path}",
    },
    "init.skill_created": {
        "en": "Created skill file: {path}",
        "zh-CN": "已创建 skill 文件: {path}",
    },
    "init.skill_exists": {
        "en": "Skill file already exists at {path}; use --force to overwrite.",
        "zh-CN": "skill 文件已存在于 {path}；使用 --force 覆盖。",
    },
    "init.done": {
        "en": "Done. Your agent will now use harness governance for engineering work.",
        "zh-CN": "完成。智能体现在会使用 harness 治理方法进行工程工作。",
    },
    "init.minimal_done": {
        "en": "Done. Minimal config written. Run `harness init` (without --minimal) for full setup.",
        "zh-CN": "完成。已写入最小配置。运行 `harness init`（不带 --minimal）获取完整设置。",
    },
    "init.prompt_platform": {
        "en": "Could not auto-detect platform. Select your AI coding tool:",
        "zh-CN": "无法自动检测平台。请选择你的 AI 编程工具：",
    },
    "init.platform_selected": {
        "en": "Selected: {platform}",
        "zh-CN": "已选择: {platform}",
    },
    # governed-start -------------------------------------------------------
    "governed_start.routing": {
        "en": "Routing: {path}",
        "zh-CN": "路径: {path}",
    },
    "governed_start.rationale": {
        "en": "Rationale: {text}",
        "zh-CN": "依据: {text}",
    },
    "governed_start.current_layer": {
        "en": "Current layer: {layer}",
        "zh-CN": "当前层: {layer}",
    },
    "governed_start.primary_skill": {
        "en": "Primary skill: {skill}",
        "zh-CN": "主 skill: {skill}",
    },
    "governed_start.disclosure": {
        "en": "Disclosure:",
        "zh-CN": "披露:",
    },
    "governed_start.next": {
        "en": "Next: {cmd}",
        "zh-CN": "下一步: {cmd}",
    },
    "governed_start.fast_ok": {
        "en": "fast-path: go ahead",
        "zh-CN": "fast-path: 直接进行",
    },
    "governed_start.recommendation.fast": {
        "en": "Answer the question directly; no harness command needed.",
        "zh-CN": "直接回答问题；不需要执行 harness 命令。",
    },
    "governed_start.recommendation.trivial": {
        "en": (
            "Make the change directly, run the verification command. "
            "No need to add to the queue for trivial changes."
        ),
        "zh-CN": (
            "直接修改代码并运行验证命令。"
            "琐碎修改无需加入队列。"
        ),
    },
    "governed_start.recommendation.governed": {
        "en": (
            "Load `skill-use-transparency` and `harness-engineering`, then "
            "`harness packet init <change-id>` when the work spans more than "
            "one layer."
        ),
        "zh-CN": (
            "先加载 `skill-use-transparency` 和 `harness-engineering`；"
            "当工作跨越多层时再 `harness packet init <change-id>`。"
        ),
    },
    # packet ---------------------------------------------------------------
    "packet.initialized": {
        "en": "Initialized change packet: {path}",
        "zh-CN": "已初始化变更包: {path}",
    },
    "packet.created_files": {
        "en": "Created files: {files}",
        "zh-CN": "已创建文件: {files}",
    },
    "packet.no_new_files": {
        "en": "No new files were written (packet already populated).",
        "zh-CN": "未写入新文件（变更包已填充）。",
    },
    "packet.check_failed_header": {
        "en": "Change packet check failed:",
        "zh-CN": "变更包检查未通过:",
    },
    "packet.check_passed_with_count": {
        "en": "Change packet check passed: {n} packet(s).",
        "zh-CN": "变更包检查通过: 共 {n} 个。",
    },
    "packet.check_passed_empty": {
        "en": "Change packet check passed: no change packets found.",
        "zh-CN": "变更包检查通过: 未发现变更包。",
    },
    "packet.invalid_id": {
        "en": "Change id must match ^[A-Za-z0-9][A-Za-z0-9._-]*$ (got: {value!r}).",
        "zh-CN": "变更 ID 必须匹配 ^[A-Za-z0-9][A-Za-z0-9._-]*$（当前: {value!r}）。",
    },
    "packet.reserved_archive": {
        "en": "Change id 'archive' is reserved.",
        "zh-CN": "变更 ID 'archive' 是保留字。",
    },
    "packet.empty_id": {
        "en": "Change id must not be empty.",
        "zh-CN": "变更 ID 不能为空。",
    },
    "packet.exists": {
        "en": "Change packet already exists: {path} (use --force to fill missing files).",
        "zh-CN": "变更包已存在: {path}（使用 --force 填充缺失文件）。",
    },
    "packet.not_found": {
        "en": "Change packet not found: {target}",
        "zh-CN": "未找到变更包: {target}",
    },
    "packet.label_missing_file": {
        "en": "{label} missing {filename}.",
        "zh-CN": "{label} 缺少 {filename}。",
    },
    "packet.label_not_a_dir": {
        "en": "{label} is not a directory.",
        "zh-CN": "{label} 不是目录。",
    },
    "packet.label_does_not_exist": {
        "en": "{label} does not exist.",
        "zh-CN": "{label} 不存在。",
    },
    "packet.label_missing_checkbox": {
        "en": "{label}/tasks.md must contain at least one checkbox checklist item.",
        "zh-CN": "{label}/tasks.md 必须至少包含一项 checkbox 清单条目。",
    },
    "packet.label_invalid_status": {
        "en": "{label}/{filename} has invalid status '{value}'. Use draft/ready/active/blocked/done/archived.",
        "zh-CN": (
            "{label}/{filename} 的状态 '{value}' 不合法。"
            "请使用 draft/ready/active/blocked/done/archived 之一。"
        ),
    },
    "packet.label_missing_contract_artifact": {
        "en": "{label}/contracts.md must declare a contract artifact or an explicit blocked reason.",
        "zh-CN": (
            "{label}/contracts.md 必须声明契约产物或显式的 blocked 原因。"
        ),
    },
    "packet.label_missing_verification": {
        "en": (
            "{label}/verification.md must record verification commands, "
            "results, or an unable-to-verify reason."
        ),
        "zh-CN": (
            "{label}/verification.md 必须记录验证命令、结果或 unable-to-verify 原因。"
        ),
    },
    "packet.label_archived_no_backlink": {
        "en": (
            "{label}: Archived packet must link stable conclusions back to ADR, "
            "README, contract, verification, queue, or project index."
        ),
        "zh-CN": (
            "{label}: 已归档的变更包必须把稳定结论回链到 ADR、README、契约、"
            "验证、队列或项目索引。"
        ),
    },
    "packet.refuse_outside_repo": {
        "en": "Refusing to operate outside project root {root}: {target}",
        "zh-CN": "拒绝在仓库根目录 {root} 之外操作: {target}",
    },
    # entry ----------------------------------------------------------------
    "entry.record_written": {
        "en": "Wrote Implementation Entry Record to {path}",
        "zh-CN": "已将 Implementation Entry Record 写入 {path}",
    },
    "entry.check_failed_header": {
        "en": "Entry record check failed:",
        "zh-CN": "Implementation Entry Record 检查未通过:",
    },
    "entry.check_passed_with_count": {
        "en": "Entry record check passed: {n} file(s).",
        "zh-CN": "Implementation Entry Record 检查通过: 共 {n} 个文件。",
    },
    "entry.check_passed_empty": {
        "en": "Entry record check passed: no entry records found.",
        "zh-CN": "Implementation Entry Record 检查通过: 未发现记录。",
    },
    "entry.missing_field": {
        "en": "{label}: Missing field: {field}",
        "zh-CN": "{label}: 缺少字段: {field}",
    },
    "entry.empty_field": {
        "en": "{label}: Empty or placeholder value: {field}",
        "zh-CN": "{label}: 字段为空或占位符: {field}",
    },
    "entry.missing_heading": {
        "en": (
            "{label}: Missing 'Implementation Entry Record:' or "
            "'Trivial Safe Change Entry:' heading."
        ),
        "zh-CN": (
            "{label}: 缺少 'Implementation Entry Record:' 或 "
            "'Trivial Safe Change Entry:' 标题。"
        ),
    },
    "entry.readiness_format": {
        "en": "{label}: Readiness gate must include pass or fail.",
        "zh-CN": "{label}: Readiness gate 字段必须包含 pass 或 fail。",
    },
    "entry.packetization_format": {
        "en": "{label}: Packetization must include ready, not-needed, or missing.",
        "zh-CN": "{label}: Packetization 字段必须包含 ready、not-needed 或 missing。",
    },
    # plan -----------------------------------------------------------------
    "plan.initialized": {
        "en": "Initialized planning session: {plan_id}",
        "zh-CN": "已初始化规划会话: {plan_id}",
    },
    "plan.dir": {
        "en": "Plan dir: {path}",
        "zh-CN": "规划目录: {path}",
    },
    "plan.attest_locked": {
        "en": "Locked SHA-256: {short}... (full hash stored in .attestation)",
        "zh-CN": "已锁定 SHA-256: {short}…（完整哈希保存在 .attestation）",
    },
    "plan.show_header": {
        "en": "Plan: {plan_path}\nAttestation: {attestation_path}\nSHA-256: {digest}",
        "zh-CN": "规划文件: {plan_path}\n锁定文件: {attestation_path}\nSHA-256: {digest}",
    },
    "plan.no_attestation": {
        "en": "No attestation set for {plan_id}.",
        "zh-CN": "{plan_id} 尚未设置锁定。",
    },
    "plan.cleared": {
        "en": "Cleared attestation for {plan_id}.",
        "zh-CN": "已清除 {plan_id} 的锁定。",
    },
    "plan.no_attestation_to_clear": {
        "en": "No attestation to clear for {plan_id}.",
        "zh-CN": "{plan_id} 没有可清除的锁定。",
    },
    "plan.all_complete": {
        "en": "ALL PHASES COMPLETE.",
        "zh-CN": "所有阶段已完成。",
    },
    "plan.incomplete": {
        "en": "Task in progress; not all phases are complete yet.",
        "zh-CN": "任务进行中；并非所有阶段都已完成。",
    },
    "plan.no_active": {
        "en": "No active planning session. Run `harness plan init` first.",
        "zh-CN": "没有活动的规划会话。请先执行 `harness plan init`。",
    },
    # check ----------------------------------------------------------------
    "check.failed_header": {
        "en": "{check} check failed:",
        "zh-CN": "{check} 检查未通过:",
    },
    "check.passed_with_count": {
        "en": "{check} check passed: {n} item(s).",
        "zh-CN": "{check} 检查通过: 共 {n} 项。",
    },
    "check.passed": {
        "en": "{check} check passed.",
        "zh-CN": "{check} 检查通过。",
    },
    "check.missing_precondition": {
        "en": "{path} missing ## Harness Precondition",
        "zh-CN": "{path} 缺少 ## Harness Precondition 段落",
    },
    "check.missing_layer_term": {
        "en": "{path} missing canonical layer term: {term}",
        "zh-CN": "{path} 缺少规范层名: {term}",
    },
    "check.old_chain_without_marker": {
        "en": "{path} contains the old layer chain without marking it as a simplified view",
        "zh-CN": "{path} 含旧版层链但未标记为简化视图",
    },
    "check.state_machine_bypass": {
        "en": "state machine allowed idea → implementation without readiness",
        "zh-CN": "状态机允许 idea → implementation 但缺少 readiness 校验",
    },
    "check.inventory_no_readme": {
        "en": "README.md not found",
        "zh-CN": "未找到 README.md",
    },
    "check.inventory_count_drift": {
        "en": "declared count {declared}, on-disk count {actual}",
        "zh-CN": "声明的数量 {declared} 与磁盘实际数量 {actual} 不一致",
    },
    "check.inventory_missing_skill": {
        "en": "missing enabled skill: {skill}",
        "zh-CN": "缺少已启用的 skill: {skill}",
    },
    "check.inventory_extra_skill": {
        "en": "lists missing/disabled skill: {skill}",
        "zh-CN": "列出了不存在或已禁用的 skill: {skill}",
    },
    "check.frequency_note": {
        "en": "Check frequency: {frequency}",
        "zh-CN": "检查频率: {frequency}",
    },
    # status ---------------------------------------------------------------
    "status.header": {
        "en": "Harness status for {path}",
        "zh-CN": "{path} 的 Harness 状态",
    },
    "status.generated": {
        "en": "Generated: {ts}",
        "zh-CN": "生成时间: {ts}",
    },
    "status.current_layer": {
        "en": "Current layer: {layer}",
        "zh-CN": "当前层: {layer}",
    },
    "status.scheduler_queue": {
        "en": "Scheduler queue: total={total} ready={ready} active={active}",
        "zh-CN": "调度队列: 总计={total} 待执行={ready} 进行中={active}",
    },
    "status.queue_items": {
        "en": "Queue items:",
        "zh-CN": "队列条目:",
    },
    "status.change_packets": {
        "en": "Change packets:",
        "zh-CN": "变更包:",
    },
    "status.no_scheduled_items": {
        "en": "No scheduler items found.",
        "zh-CN": "调度器中无待执行条目。",
    },
    "status.no_change_packets": {
        "en": "No change packets found.",
        "zh-CN": "未发现变更包。",
    },
    "status.active_plan": {
        "en": "Active plan: {plan_id} ({state})",
        "zh-CN": "活动规划: {plan_id}（{state}）",
    },
    "status.plan_state_attested": {
        "en": "attested",
        "zh-CN": "已锁定",
    },
    "status.plan_state_unattested": {
        "en": "not attested",
        "zh-CN": "未锁定",
    },
    "status.checkpoint_header": {
        "en": "Checkpoint:",
        "zh-CN": "运行检查点:",
    },
    "status.last_worker": {
        "en": "last worker: {value}",
        "zh-CN": "上次 worker: {value}",
    },
    "status.stop_reason": {
        "en": "stop reason: {value}",
        "zh-CN": "停止原因: {value}",
    },
    "status.verification_line": {
        "en": "Verification: {state} ({summary})",
        "zh-CN": "验证: {state}（{summary}）",
    },
    "status.verification_stale": {
        "en": "stale",
        "zh-CN": "过期",
    },
    "status.verification_fresh": {
        "en": "fresh",
        "zh-CN": "新鲜",
    },
    "status.warnings_header": {
        "en": "Warnings:",
        "zh-CN": "警告:",
    },
    "status.wrote_md": {
        "en": "Wrote {path}",
        "zh-CN": "已写入 {path}",
    },
    "status.not_initialized": {
        "en": "Project not initialized. Run `harness init` to set up governance.",
        "zh-CN": "项目未初始化。运行 `harness init` 设置治理。",
    },
    # verify ---------------------------------------------------------------
    "verify.passed": {
        "en": "verify {preset}: passed",
        "zh-CN": "verify {preset}: 通过",
    },
    "verify.failed": {
        "en": "verify {preset}: failed",
        "zh-CN": "verify {preset}: 失败",
    },
    "verify.unknown_preset": {
        "en": "Unknown preset: {preset!r}. Built-in presets: {available}.",
        "zh-CN": "未知的 preset: {preset!r}。内置 preset: {available}。",
    },
    # review ---------------------------------------------------------------
    "review.recorded": {
        "en": "Recorded review/next state for {task_id} in {path}",
        "zh-CN": "已将 {task_id} 的 review/next 状态写入 {path}",
    },
    # config ---------------------------------------------------------------
    "config.created": {
        "en": "Created: {path}",
        "zh-CN": "已创建: {path}",
    },
    "config.platform": {
        "en": "Agent platform: {platform}",
        "zh-CN": "智能体平台: {platform}",
    },
    "config.show_header": {
        "en": "Configuration: {path}",
        "zh-CN": "配置文件: {path}",
    },
    "config.not_found": {
        "en": "Config file not found: {path}. Run `harness config init` first.",
        "zh-CN": "未找到配置文件: {path}。请先运行 `harness config init`。",
    },
    "config.set_bad_format": {
        "en": "Invalid format: {value!r}. Expected key=value.",
        "zh-CN": "格式无效: {value!r}。请使用 key=value 格式。",
    },
    "config.unknown_field": {
        "en": "Unknown config field: {field!r}.",
        "zh-CN": "未知的配置字段: {field!r}。",
    },
    "config.set_ok": {
        "en": "Set {key} = {value}",
        "zh-CN": "已设置 {key} = {value}",
    },
    "config.validate_passed": {
        "en": "Configuration is valid.",
        "zh-CN": "配置文件验证通过。",
    },
    "config.validate_failed": {
        "en": "Configuration validation failed: {error}",
        "zh-CN": "配置文件验证失败: {error}",
    },
    "config.migrate_done": {
        "en": "Config migrated from schema v{old} to v{new}.",
        "zh-CN": "配置已从 schema v{old} 迁移到 v{new}。",
    },
    "config.migrate_already_current": {
        "en": "Config is already at schema v{version}; no migration needed.",
        "zh-CN": "配置已是 schema v{version}；无需迁移。",
    },
    # runner ---------------------------------------------------------------
    "runner.dry_run_no_item": {
        "en": "dry-run: no ready or active queue item",
        "zh-CN": "dry-run: 队列中没有 ready 或 active 条目",
    },
    "runner.orchestrator_written": {
        "en": "Orchestrator prompt written to: {path}",
        "zh-CN": "编排提示已写入: {path}",
    },
    "runner.unresolved_variables": {
        "en": "Warning: {count} unresolved variables: {vars}",
        "zh-CN": "警告: {count} 个未解析变量: {vars}",
    },
    "runner.command_required": {
        "en": "--command is required when --executor=subprocess.",
        "zh-CN": "--executor=subprocess 时必须指定 --command。",
    },
    "runner.unknown_verification": {
        "en": "Unknown verification preset: {preset!r}. Available: {available}.",
        "zh-CN": "未知的验证 preset: {preset!r}。可用: {available}。",
    },
    "runner.no_ready_item": {
        "en": "No [ready] or [active] item found in queue.",
        "zh-CN": "队列中未找到 [ready] 或 [active] 条目。",
    },
    "runner.render_written": {
        "en": "Rendered {role} prompt written to: {path}",
        "zh-CN": "{role} 提示已渲染并写入: {path}",
    },
    "runner.render_unresolved": {
        "en": "Warning: {count} unresolved variables: {vars}",
        "zh-CN": "警告: {count} 个未解析变量: {vars}",
    },
    "runner.codex_not_found": {
        "en": "codex CLI not found on PATH. Install Codex CLI or use SubprocessAgentExecutor with a different command.",
        "zh-CN": "PATH 中未找到 codex CLI。请安装 Codex CLI 或使用其他命令的 SubprocessAgentExecutor。",
    },
    "runner.timed_out": {
        "en": "[harness runner] timed out after {seconds}s",
        "zh-CN": "[harness runner] 超时，已运行 {seconds}s",
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class MessageCatalog:
    """Resolve a message ID in the active language, with bilingual fallback."""

    def __init__(self, language: str | None = None) -> None:
        self.language = language or detect_language()

    def get(self, message_id: str, **kwargs: Any) -> str:
        entry = _MESSAGES.get(message_id)
        if entry is None:
            # Fall back to the ID itself so unknown keys are visible.
            return message_id
        primary = entry.get(self.language) or entry.get("en") or message_id
        if not kwargs:
            return primary
        try:
            return primary.format(**kwargs)
        except (KeyError, IndexError):
            return primary

    def bilingual(self, message_id: str, **kwargs: Any) -> str:
        """Return ``zh / en`` (or just the active language when it is English)."""
        primary = self.get(message_id, **kwargs)
        if self.language == "en":
            return primary
        entry = _MESSAGES.get(message_id, {})
        english = entry.get("en", primary)
        if english == primary:
            return primary
        return f"{primary} / {english}"


def t(message_id: str, **kwargs: Any) -> str:
    """Convenience wrapper around :meth:`MessageCatalog.get` using env language."""
    return MessageCatalog().get(message_id, **kwargs)


def bilingual(message_id: str, **kwargs: Any) -> str:
    """Convenience wrapper around :meth:`MessageCatalog.bilingual`."""
    return MessageCatalog().bilingual(message_id, **kwargs)


def set_language(language: str) -> None:
    """Set the active language for the current process (mainly for tests)."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language: {language!r}. Supported: {SUPPORTED_LANGUAGES}."
        )
    os.environ["HARNESS_LANG"] = language


__all__ = [
    "SUPPORTED_LANGUAGES",
    "MessageCatalog",
    "bilingual",
    "detect_language",
    "set_language",
    "t",
]