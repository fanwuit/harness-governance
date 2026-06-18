"""Internationalized CLI messages for ``harness-governance``.

The CLI speaks English by default. Setting the ``HARNESS_LANG`` environment
variable to ``zh-CN`` switches the user-facing strings to Chinese; when
Chinese is active, each message is rendered bilingually as ``中文 / English``
so a mixed-language team can still grep the English text.

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
    "init.skill_outdated": {
        "en": (
            "Skill file at {path} is v{disk_ver}, but the installed "
            "harness-governance template is v{template_ver}. Re-run "
            "`harness init --force` (or this command with --force) to upgrade."
        ),
        "zh-CN": (
            "{path} 的 skill 文件版本为 v{disk_ver}，但已安装的 "
            "harness-governance 模板是 v{template_ver}。重新运行 "
            "`harness init --force`（或本命令加 --force）升级。"
        ),
    },
    "init.all_skills_header": {
        "en": "Created skill adapters for all platforms:",
        "zh-CN": "已创建所有平台的 skill 适配文件：",
    },
    "init.done": {
        "en": "Done. Your agent will now use harness governance for engineering work.",
        "zh-CN": "完成。智能体现在会使用 harness 治理方法进行工程工作。",
    },
    "init.minimal_done": {
        "en": "Done. Minimal config written. Run `harness init` (without --minimal) for full setup.",
        "zh-CN": "完成。已写入最小配置。运行 `harness init`（不带 --minimal）获取完整设置。",
    },
    "init.quickstart_header": {
        "en": "Quick start guide:",
        "zh-CN": "快速上手:",
    },
    "init.quickstart_task": {
        "en": "Describe your task: `harness governed-start \"your task here\"`",
        "zh-CN": "描述任务: `harness governed-start \"你的任务\"`",
    },
    "init.quickstart_status": {
        "en": "View current state: `harness status`",
        "zh-CN": "查看当前状态: `harness status`",
    },
    "init.quickstart_guide": {
        "en": "Read the current layer guide: `harness layer guide`",
        "zh-CN": "阅读当前层指南: `harness layer guide`",
    },
    "init.quickstart_docs": {
        "en": "Full walkthrough: QUICKSTART.md",
        "zh-CN": "完整 walkthrough: QUICKSTART.md",
    },
    "init.prompt_platform": {
        "en": "Could not auto-detect platform. Select your AI coding tool:",
        "zh-CN": "无法自动检测平台。请选择你的 AI 编程工具：",
    },
    "init.prompt_platform_with_default": {
        "en": "Detected: {default}. Press Enter to confirm, or select another:",
        "zh-CN": "检测到: {default}。按 Enter 确认，或选择其他平台：",
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
    "governed_start.rigor_tier": {
        "en": "Rigor tier: {tier}",
        "zh-CN": "严格程度: {tier}",
    },
    "governed_start.layer_path": {
        "en": "Layer path: {path}",
        "zh-CN": "层路径: {path}",
    },
    "governed_start.next_layer": {
        "en": "Next layer: {layer}",
        "zh-CN": "下一层: {layer}",
    },
    "governed_start.path_hint": {
        "en": "Inspect progress: `harness layer show`; inspect gates: `harness gate status`",
        "zh-CN": "查看进度: `harness layer show`; 查看门控: `harness gate status`",
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
        "zh-CN": ("直接修改代码并运行验证命令。琐碎修改无需加入队列。"),
    },
    "governed_start.recommendation.governed": {
        "en": (
            "Run `harness governed-start '<task>'` to classify; "
            "use `harness layer advance <layer> --confirmed` to progress "
            "through layers with gate enforcement."
        ),
        "zh-CN": (
            "运行 `harness governed-start '<任务>'` 进行分类；"
            "使用 `harness layer advance <层> --confirmed` 在有门控保护下"
            "逐层推进。"
        ),
    },
    # rigor detection -----------------------------------------------------
    "rigor.auto_detected": {
        "en": "Rigor tier auto-detected: {tier} (keyword: {keyword})",
        "zh-CN": "自动检测严格程度: {tier}（关键词: {keyword}）",
    },
    "rigor.resolved": {
        "en": "Rigor tier resolved: {tier}",
        "zh-CN": "严格程度已确定: {tier}",
    },
    "rigor.default_strict": {
        "en": "Defaulting to STRICT tier (safe default).",
        "zh-CN": "默认使用 STRICT 严格级别（安全默认值）。",
    },
    "rigor.override_applied": {
        "en": "Rigor tier overridden: {tier} (user override)",
        "zh-CN": "严格程度已覆盖: {tier}（用户指定）",
    },
    "rigor.invalid": {
        "en": "Invalid rigor tier: {value!r}. Valid: {valid}",
        "zh-CN": "无效的严格程度: {value!r}。可用: {valid}",
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
        "zh-CN": ("{label}/contracts.md 必须声明契约产物或显式的 blocked 原因。"),
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
    "check.docs_stale_adr": {
        "en": "ADR {path} references missing file: {ref}",
        "zh-CN": "ADR {path} 引用了不存在的文件: {ref}",
    },
    "check.docs_broken_link": {
        "en": "{source} links to non-existent file: {target}",
        "zh-CN": "{source} 链接到不存在的文件: {target}",
    },
    "check.docs_version_mismatch": {
        "en": "{path} references harness v{old_version}; current is v{current_version}",
        "zh-CN": "{path} 引用了 harness v{old_version}；当前版本为 v{current_version}",
    },
    "check.docs_empty_section": {
        "en": '{path}: section "{section}" is empty or missing',
        "zh-CN": '{path}: "{section}" 段落为空或缺失',
    },
    # priority --------------------------------------------------------------
    "priority.no_competing": {
        "en": "No competing skills found across {platforms} platform(s).",
        "zh-CN": "在 {platforms} 个平台上未发现竞争 skill。",
    },
    "priority.competing_summary": {
        "en": "{count} competing skill(s) found across {platforms} platform(s).",
        "zh-CN": "在 {platforms} 个平台上发现 {count} 个竞争 skill。",
    },
    "priority.fix_hint": {
        "en": "Run `harness check priority --fix` to neutralize them.",
        "zh-CN": "运行 `harness check priority --fix` 以消除它们。",
    },
    "priority.finding_reason": {
        "en": "{path}: {reason}",
        "zh-CN": "{path}: {reason}",
    },
    "priority.reason.always_apply": {
        "en": "alwaysApply=true in frontmatter",
        "zh-CN": "frontmatter 中声明了 alwaysApply=true",
    },
    "priority.reason.before_any_response": {
        "en": "'before any response' in description",
        "zh-CN": "描述中包含 'before any response'",
    },
    "priority.reason.session_start": {
        "en": "'session start' in description",
        "zh-CN": "描述中包含 'session start'",
    },
    "priority.reason.starting_any_conversation": {
        "en": "'starting any conversation' in description",
        "zh-CN": "描述中包含 'starting any conversation'",
    },
    "priority.reason.body_trigger": {
        "en": "trigger phrase in skill body: {phrase}",
        "zh-CN": "skill 正文含触发短语: {phrase}",
    },
    "priority.nothing_to_fix": {
        "en": "No competing skills to fix.",
        "zh-CN": "没有需要修复的竞争 skill。",
    },
    "priority.fix_applied": {
        "en": "[{action}] {path} -> {new_path}",
        "zh-CN": "[{action}] {path} -> {new_path}",
    },
    "priority.fix_failed": {
        "en": "Failed to fix {path}: {detail}",
        "zh-CN": "修复 {path} 失败: {detail}",
    },
    "priority.fix_skipped_exists": {
        "en": "Skipped {path}: target {new_path} already exists.",
        "zh-CN": "跳过 {path}: 目标 {new_path} 已存在。",
    },
    "priority.runtime_warning": {
        "en": "WARNING: {count} competing skill(s) detected: {names}. Run `harness check priority --fix`.",
        "zh-CN": "警告: 检测到 {count} 个竞争 skill: {names}。运行 `harness check priority --fix`。",
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
    "runner.heartbeat_progress": {
        "en": "[harness runner] elapsed: {elapsed}s, stdout: {stdout_lines} lines, stderr: {stderr_lines} lines",
        "zh-CN": "[harness runner] 已运行: {elapsed}s, stdout: {stdout_lines} 行, stderr: {stderr_lines} 行",
    },
    "runner.round_started": {
        "en": "[harness runner] round {round_index} started: {item}",
        "zh-CN": "[harness runner] 第 {round_index} 轮开始: {item}",
    },
    "runner.scope_exceeded": {
        "en": "Scope budget exceeded: {violations}. Task decomposed — see NEXT.md for sub-items.",
        "zh-CN": "范围预算超限: {violations}。任务已拆分 — 查看 NEXT.md 中的子任务。",
    },
    # session --------------------------------------------------------------
    "session.created": {
        "en": "Session created: {session_id}",
        "zh-CN": "已创建会话: {session_id}",
    },
    "session.created_with_rigor": {
        "en": "Session created: {session_id} (rigor: {rigor})",
        "zh-CN": "已创建会话: {session_id}（严格程度: {rigor}）",
    },
    "session.not_found": {
        "en": "Session not found: {session_id}",
        "zh-CN": "未找到会话: {session_id}",
    },
    "session.no_active": {
        "en": "No active session. Run `harness governed-start` first.",
        "zh-CN": "没有活跃会话。请先运行 `harness governed-start`。",
    },
    "session.closed": {
        "en": "Session closed: {session_id}",
        "zh-CN": "已关闭会话: {session_id}",
    },
    "session.already_closed": {
        "en": "Session already closed: {session_id}",
        "zh-CN": "会话已关闭: {session_id}",
    },
    "session.require_session": {
        "en": "require_session is enabled but no active session found. Run `harness governed-start` first.",
        "zh-CN": "require_session 已启用但未找到活跃会话。请先运行 `harness governed-start`。",
    },
    "session.header": {
        "en": "Session: {session_id}",
        "zh-CN": "会话: {session_id}",
    },
    "session.description": {
        "en": "Description: {text}",
        "zh-CN": "描述: {text}",
    },
    "session.routing_path": {
        "en": "Routing path: {path}",
        "zh-CN": "路由路径: {path}",
    },
    "session.current_layer": {
        "en": "Current layer: {layer}",
        "zh-CN": "当前层: {layer}",
    },
    "session.status_line": {
        "en": "Status: {status}",
        "zh-CN": "状态: {status}",
    },
    "session.change_id": {
        "en": "Change ID: {change_id}",
        "zh-CN": "变更 ID: {change_id}",
    },
    "session.transitions_header": {
        "en": "Transitions ({count}):",
        "zh-CN": "层转换记录 ({count}):",
    },
    "session.no_sessions": {
        "en": "No sessions found.",
        "zh-CN": "未找到任何会话。",
    },
    # layer ----------------------------------------------------------------
    "layer.advanced": {
        "en": "Layer advanced: {from_layer} -> {to_layer}",
        "zh-CN": "层推进: {from_layer} -> {to_layer}",
    },
    "layer.transition_blocked": {
        "en": "Layer transition blocked: {from_layer} -> {to_layer}",
        "zh-CN": "层转换被阻止: {from_layer} -> {to_layer}",
    },
    "layer.no_session": {
        "en": "No active session to advance. Run `harness governed-start` first.",
        "zh-CN": "没有可推进的活跃会话。请先运行 `harness governed-start`。",
    },
    "layer.same_layer": {
        "en": "Already at layer: {layer}",
        "zh-CN": "已在当前层: {layer}",
    },
    "layer.guide_header": {
        "en": "Author Interaction Guide: {layer}",
        "zh-CN": "作者交互指南: {layer}",
    },
    "layer.guide_not_found": {
        "en": "No guide defined for layer: {layer}. Required output: {output}",
        "zh-CN": "层 {layer} 暂无交互指南。要求产出: {output}",
    },
    "layer.confirmed_recorded": {
        "en": "Author confirmation recorded in audit trail.",
        "zh-CN": "作者确认已记录到审计日志。",
    },
    "layer.skip_gate_requires_confirmed": {
        "en": "--skip-gate requires --confirmed (safety interlock).",
        "zh-CN": "--skip-gate 必须配合 --confirmed 使用（安全联动）。",
    },
    "layer.gate_blocked": {
        "en": "Advance blocked: complete the current layer's gate requirements first, or use --skip-gate --confirmed to override.",
        "zh-CN": "推进被阻止: 请先完成当前层的门控要求，或使用 --skip-gate --confirmed 强制跳过。",
    },
    # gate ---------------------------------------------------------------
    "gate.no_session": {
        "en": "No active governance session found. Run `harness governed-start` first.",
        "zh-CN": "未找到活跃的治理会话。请先运行 `harness governed-start`。",
    },
    "gate.check.passed": {
        "en": "Gate {layer}: PASSED ({questions}/{required} questions answered)",
        "zh-CN": "门控 {layer}: 通过 ({questions}/{required} 问题已答)",
    },
    "gate.check.failed": {
        "en": "Gate {layer}: FAILED ({questions}/{required} questions answered; artifacts missing: {missing})",
        "zh-CN": "门控 {layer}: 失败 ({questions}/{required} 问题已答; 缺失工件: {missing})",
    },
    "gate.failure.details_header": {
        "en": "Missing requirements:",
        "zh-CN": "缺失要求:",
    },
    "gate.failure.questions_missing": {
        "en": "Questions answered: {answered}/{required}.",
        "zh-CN": "问题回答进度: {answered}/{required}。",
    },
    "gate.failure.artifacts_missing": {
        "en": "Required artifacts not found: {missing}.",
        "zh-CN": "未找到必需工件: {missing}。",
    },
    "gate.failure.blocking_artifacts_missing": {
        "en": "Blocking artifacts not found: {missing}.",
        "zh-CN": "未找到阻塞性工件: {missing}。",
    },
    "gate.failure.confirmations_unmet": {
        "en": "Confirmation checks not met:",
        "zh-CN": "确认检查未满足:",
    },
    "gate.failure.red_flags_header": {
        "en": "Red flags we do not accept:",
        "zh-CN": "不接受的红旗借口:",
    },
    "gate.failure.red_flag.small_change": {
        "en": "\"This is just a small change, tests or evidence are not needed.\"",
        "zh-CN": "“这只是小改动，不需要测试或证据。”",
    },
    "gate.failure.red_flag.later": {
        "en": "\"I'll add the missing gate evidence later.\"",
        "zh-CN": "“缺失的门控证据之后再补。”",
    },
    "gate.failure.red_flag.existing": {
        "en": "\"The existing checks probably cover this.\"",
        "zh-CN": "“现有检查应该已经覆盖了。”",
    },
    "gate.failure.red_flag.skip": {
        "en": "\"I'll skip the gate because it is slowing me down.\"",
        "zh-CN": "“门控拖慢了进度，所以先跳过。”",
    },
    "gate.failure.actions_header": {
        "en": "Required actions:",
        "zh-CN": "必需动作:",
    },
    "gate.failure.action.guide": {
        "en": "Run `harness layer guide {layer}` and answer the required questions.",
        "zh-CN": "运行 `harness layer guide {layer}` 并回答必需问题。",
    },
    "gate.failure.action.complete": {
        "en": "Create or record the missing evidence listed above.",
        "zh-CN": "创建或记录上方列出的缺失证据。",
    },
    "gate.failure.action.rerun": {
        "en": "Re-run `harness gate check {layer}`.",
        "zh-CN": "重新运行 `harness gate check {layer}`。",
    },
    "gate.status.locked": {
        "en": "[LOCKED]  {layer} — session: {session}, at: {passed_at}",
        "zh-CN": "[已锁定] {layer} — 会话: {session}, 时间: {passed_at}",
    },
    "gate.status.unlocked": {
        "en": "[  OPEN]  {layer}",
        "zh-CN": "[ 开放] {layer}",
    },
    "gate.reset.requires_confirmed": {
        "en": "Must pass --confirmed to reset a gate lock.",
        "zh-CN": "必须传入 --confirmed 才能重置门锁。",
    },
    "gate.reset.removed": {
        "en": "Lock removed: {layer}",
        "zh-CN": "已移除锁: {layer}",
    },
    "gate.reset.not_found": {
        "en": "No lock found for: {layer}",
        "zh-CN": "未找到锁: {layer}",
    },
    "gate.reset.all_removed": {
        "en": "Removed {count} lock file(s).",
        "zh-CN": "已移除 {count} 个锁文件。",
    },
    # v0.7.1 gate timing ------------------------------------------------
    "gate.timing.header": {
        "en": "Timing for session: {session}",
        "zh-CN": "会话 {session} 的耗时统计",
    },
    "gate.timing.no_transitions": {
        "en": "No transitions recorded.",
        "zh-CN": "未记录任何层转换。",
    },
    "gate.timing.transition_row": {
        "en": "  {from_layer} -> {to_layer}  [{verdict}]  {duration}s",
        "zh-CN": "  {from_layer} -> {to_layer}  [{verdict}]  {duration}s",
    },
    "gate.timing.summary": {
        "en": "Total: {total}s across {count} transitions (avg: {avg}s)",
        "zh-CN": "总计: {total}s，共 {count} 次转换（平均: {avg}s）",
    },
    # -- v0.8.0 Gap 4: Tech stack -----------------------------------------
    "tech_stack.captured": {
        "en": "Technology stack captured: {languages}",
        "zh-CN": "技术栈已捕获：{languages}",
    },
    "tech_stack.lint_tools_found": {
        "en": "Lint tools detected: {count}",
        "zh-CN": "检测到 {count} 个 lint 工具",
    },
    "tech_stack.pkg_managers": {
        "en": "Package managers: {pkgs}",
        "zh-CN": "包管理器：{pkgs}",
    },
    "tech_stack.saved": {
        "en": "Manifest saved to {path}",
        "zh-CN": "清单已保存到 {path}",
    },
    "tech_stack.check_passed": {
        "en": "Tech stack check passed — no issues found.",
        "zh-CN": "技术栈检查通过 — 未发现问题。",
    },
    "tech_stack.lint_gaps_header": {
        "en": "Languages with unconfirmed lint tools:",
        "zh-CN": "以下语言未确认 lint 工具：",
    },
    "tech_stack.doc_gaps_header": {
        "en": "Languages with unconfirmed doc comment styles:",
        "zh-CN": "以下语言未确认文档注释风格：",
    },
    "tech_stack.pending_tools_header": {
        "en": "Tools pending confirmation:",
        "zh-CN": "以下工具待确认：",
    },
    "tech_stack.tool_added": {
        "en": "Tool registered: {tool} @ {version}",
        "zh-CN": "工具已注册：{tool} @ {version}",
    },
    "tech_stack.tool_pending_confirmation": {
        "en": "⚠  This tool must be confirmed before the gate will pass.",
        "zh-CN": "⚠  该工具需确认后门禁才能通过。",
    },
    "tech_stack.no_manifest": {
        "en": "No tech stack manifest found. Run 'harness tech-stack capture' first.",
        "zh-CN": "未找到技术栈清单。请先运行 'harness tech-stack capture'。",
    },
    "tech_stack.languages": {
        "en": "Languages: {langs}",
        "zh-CN": "语言：{langs}",
    },
    "tech_stack.lint_header": {
        "en": "Lint tools:",
        "zh-CN": "Lint 工具：",
    },
    "tech_stack.formatter_header": {
        "en": "Formatters:",
        "zh-CN": "格式化工具：",
    },
    "tech_stack.doc_header": {
        "en": "Doc comment styles:",
        "zh-CN": "文档注释风格：",
    },
    "tech_stack.introduced_header": {
        "en": "Introduced tools:",
        "zh-CN": "已引入的工具：",
    },
    "tech_stack.not_configured": {
        "en": "not configured",
        "zh-CN": "未配置",
    },
    "tech_stack.suggestions": {
        "en": "suggested",
        "zh-CN": "建议",
    },
    "tech_stack.no_languages_detected": {
        "en": "No programming languages detected in this project.",
        "zh-CN": "未在此项目中检测到编程语言。",
    },
    "tech_stack.unknown_language": {
        "en": "Unknown or undetected language: {lang}",
        "zh-CN": "未知或未检测到的语言：{lang}",
    },
    "tech_stack.lint_confirmed": {
        "en": "Lint tool confirmed: {language} → {tool} @ {version}",
        "zh-CN": "Lint 工具已确认：{language} → {tool} @ {version}",
    },
    "tech_stack.detected": {
        "en": "detected",
        "zh-CN": "检测到",
    },
    "tech_stack.docstyle_confirmed": {
        "en": "Doc comment style confirmed: {language} → {style}",
        "zh-CN": "文档注释风格已确认：{language} → {style}",
    },
    # -- v0.8.0 Gap 1: Isolation ------------------------------------------
    "isolation.workspace_created": {
        "en": "  {role}: {path}",
        "zh-CN": "  {role}: {path}",
    },
    "isolation.init_done": {
        "en": "Created {count} isolation workspace(s) for session {session}.",
        "zh-CN": "已为会话 {session} 创建 {count} 个隔离工作区。",
    },
    "isolation.roles_found": {
        "en": "Roles isolated: {roles}",
        "zh-CN": "已隔离的角色：{roles}",
    },
    "isolation.workspaces_valid": {
        "en": "Workspaces valid: {valid}",
        "zh-CN": "工作区状态：{valid}",
    },
    "isolation.violations_header": {
        "en": "Cross-role violations:",
        "zh-CN": "跨角色违规：",
    },
    "isolation.out_of_scope_header": {
        "en": "Files outside declared scope:",
        "zh-CN": "超出声明范围的文件：",
    },
    "isolation.not_created": {
        "en": "not created",
        "zh-CN": "未创建",
    },
    "isolation.paths_label": {
        "en": "allowed paths",
        "zh-CN": "允许路径",
    },
    "isolation.roles_label": {
        "en": "allowed roles",
        "zh-CN": "允许角色",
    },
    # -- v0.8.0 Gap 3: Drift ---------------------------------------------
    "drift.base_ref": {
        "en": "Diff base: {ref}",
        "zh-CN": "差异基准：{ref}",
    },
    "drift.files_changed": {
        "en": "Files changed: {count}",
        "zh-CN": "变更文件：{count} 个",
    },
    "drift.line_stats": {
        "en": "Lines: +{added} / -{deleted}",
        "zh-CN": "行数：+{added} / -{deleted}",
    },
    "drift.out_of_scope": {
        "en": "Files outside declared scope:",
        "zh-CN": "超出声明范围的文件：",
    },
    "drift.forbidden_paths": {
        "en": "Files in forbidden paths:",
        "zh-CN": "禁止路径中的文件：",
    },
    "drift.decomposition_triggered": {
        "en": "Decomposition triggers:",
        "zh-CN": "分解触发：",
    },
    "drift.detected": {
        "en": "✗ Scope drift detected — return to contract to expand scope.",
        "zh-CN": "✗ 检测到范围漂移 — 请回到契约层扩展范围。",
    },
    "drift.clean": {
        "en": "✓ No scope drift detected.",
        "zh-CN": "✓ 未检测到范围漂移。",
    },
    "drift.scope_saved": {
        "en": "Scope saved for {change_id}: {files} file(s), max_files={max_files}, max_lines={max_lines} → {path}",
        "zh-CN": "范围已保存 {change_id}：{files} 个文件，max_files={max_files}，max_lines={max_lines} → {path}",
    },
    "drift.no_scope": {
        "en": "No scope declaration found for this change.",
        "zh-CN": "未找到此变更的范围声明。",
    },
    "drift.boundary_header": {
        "en": "Scope boundary for {change_id}:",
        "zh-CN": "{change_id} 的范围边界：",
    },
    # -- v0.8.0 Gap 2: Alignment -----------------------------------------
    "alignment.summary": {
        "en": "Fields: {expected} expected, {matched} matched",
        "zh-CN": "字段：预期 {expected}，匹配 {matched}",
    },
    "alignment.unsupported": {
        "en": "Note: alignment skipped for unsupported languages: {langs} (Python only in v0.8.0)",
        "zh-CN": "注意：以下语言不支持对齐检查：{langs}（v0.8.0 仅支持 Python）",
    },
    "alignment.no_findings": {
        "en": "No alignment findings — all fields match.",
        "zh-CN": "未发现对齐问题 — 所有字段均匹配。",
    },
    "alignment.failed": {
        "en": "✗ Field alignment failed — review findings above.",
        "zh-CN": "✗ 字段对齐未通过 — 请查看上述发现。",
    },
    "alignment.passed": {
        "en": "✓ Field alignment passed.",
        "zh-CN": "✓ 字段对齐已通过。",
    },
    "alignment.trace_summary": {
        "en": "Traceability: {total} fields, {traced} traced across all layers",
        "zh-CN": "可追溯性：{total} 个字段，{traced} 个跨层追溯",
    },
    # -- v0.8.0 Gap 5: Skill chain ---------------------------------------
    "skill_chain.summary_line": {
        "en": "Total: {total} invocations, max depth: {depth}, skills: {skills}",
        "zh-CN": "总计：{total} 次调用，最大深度：{depth}，技能：{skills}",
    },
    "skill_chain.report_header": {
        "en": "Skill chain: {total} invocations, max depth: {depth}",
        "zh-CN": "技能调用链：{total} 次调用，最大深度：{depth}",
    },
    "skill_chain.skills_list": {
        "en": "Skills invoked: {skills}",
        "zh-CN": "已调用技能：{skills}",
    },
    "skill_chain.orphans": {
        "en": "Orphan invocations: {count} (no parent record found)",
        "zh-CN": "孤儿调用：{count} 个（未找到父记录）",
    },
    "skill_chain.longest_chain": {
        "en": "Longest chain: {length} call(s)",
        "zh-CN": "最长调用链：{length} 次",
    },
    "skill_chain.issues_header": {
        "en": "Chain integrity issues:",
        "zh-CN": "调用链完整性问题：",
    },
    "skill_chain.clean": {
        "en": "✓ Skill chain integrity verified.",
        "zh-CN": "✓ 技能调用链完整性已验证。",
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
