# Check Frequency Guidance / 检查频率指引

## Purpose / 目的

Reduce the daily overhead of governance chains while maintaining trustworthy verification before completion declarations, phase closeouts, and external deliveries. Check frequency is layered by impact scope rather than running full checks on every small change.

降低治理链路的日常开销，同时保持完成声明、阶段收口和对外交付前的验证可信。检查频率按影响范围分层，而不是每次小改都跑全量。

## Default Rule / 默认规则

- During iteration: run targeted checks that match the files or behavior changed.
- 迭代期间：运行与所改文件或行为匹配的定向检查。
- At phase closeout: run `harness check all`.
- 阶段收口时：运行 `harness check all`。
- Before commit, PR, push, release, publish, or handoff: run `harness check all`.
- 在 commit、PR、push、release、publish 或 handoff 前：运行 `harness check all`。
- When verification machinery changed or impact scope is unclear: run `harness check all`.
- 当验证机制变更或影响范围不明确时：运行 `harness check all`。

## Targeted Checks / 定向检查

Use targeted checks while still editing:

仍在编辑时使用定向检查：

- Script behavior changed: run the script's focused test file.
- 脚本行为变更：运行该脚本的聚焦测试文件。
- README skill inventory or important asset list changed: run `harness check inventory`.
- README skill 清单或重要资产列表变更：运行 `harness check inventory`。
- Implementation Entry Record checker or remediation records changed: run `harness check entry` and its tests.
- Implementation Entry Record 检查器或修复记录变更：运行 `harness check entry` 及其测试。
- Change packets changed: run `harness check packets`.
- Change packet 变更：运行 `harness check packets`。
- Routing, layer, companion, or governance wording changed: run `harness check routing` and governance docs tests.
- Routing、layer、companion 或治理措辞变更：运行 `harness check routing` 及治理文档测试。
- Harness visualization output or status parsing changed: run harness visualization tests.
- Harness 可视化输出或状态解析变更：运行 harness visualization 测试。

If a targeted check is failing, fix that failure before spending time on `check:all`.

如果定向检查失败，先修复该失败，再花时间跑 `check:all`。

## Full Check Triggers / 全量检查触发条件

Run `harness check all` when any of these are true:

以下任一条件为真时运行 `harness check all`：

- A remediation item or implementation phase is about to be marked done.
- 一个修复项或实现阶段即将标记为完成。
- A batch of related governance changes is being closed out.
- 一批相关治理变更正在收口。
- You are about to commit, open a PR, push, release, publish, or hand off to another person/agent.
- 即将 commit、开 PR、push、release、publish 或交接给其他人/agent。
- `package.json` scripts, test globs, checker scripts, or `check:all` itself changed.
- `package.json` 脚本、测试 glob、检查器脚本或 `check:all` 本身发生变更。
- Multiple governance owners were touched, or the blast radius is not obvious.
- 涉及多个治理 owner，或影响范围不明显。
- A long-running or multi-agent task has completed and the final worktree needs one trusted readout.
- 一个长时间运行或多 agent 任务已完成，最终工作树需要一次可信读出。

## Recurring Jobs / 周期任务

Recurring jobs should not amplify verification cost by default:

周期任务默认不应放大验证成本：

- Nightly `document-gardener` should default to scan-only and lightweight structure checks.
- 每夜 `document-gardener` 应默认为仅扫描和轻量结构检查。
- Repair mode or stable-state edits may run targeted checks first.
- 修复模式或稳定状态编辑可先运行定向检查。
- `check:all` belongs to repair closeout, phase closeout, or explicit release/commit readiness, not every nightly scan.
- `check:all` 属于修复收口、阶段收口或显式 release/commit 就绪检查，不属于每次每夜扫描。

## Output Expectation / 输出期望

Final reports should name the checks that actually ran and their result. If `check:all` was intentionally skipped, say why and name the targeted checks that were sufficient for the current scope.

最终报告应列出实际运行的检查及其结果。如果有意跳过了 `check:all`，应说明原因并列出对当前范围已足够的定向检查。
