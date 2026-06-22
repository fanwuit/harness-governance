# Change Packet Model / 变更包模型

## Purpose / 目的

Use a change packet as a temporary, durable work folder for complex changes. It keeps proposal, design, tasks, contracts, tests, and verification context together while the harness layer model remains the authority.

将变更包（change packet）作为复杂变更的临时、持久化工作文件夹。它将提案、设计、任务、契约和验证上下文集中管理，同时 harness 层模型仍然是权威。

The packet is a carrier, not a gate. Harness layers still decide what can move next.

包是载体，不是关卡。Harness 层仍然决定什么可以推进。

## When To Use / 何时使用

Create or request a packet when at least one condition is true:

当以下至少一个条件成立时，创建或请求一个包：

- The work spans two or more harness layers.
- The work touches multiple modules, services, repositories, tools, or runtimes.
- The work will likely continue across multiple agent sessions.
- The work needs ADR, contract, readiness, implementation, and verification context linked together.
- NEXT, TODO, backlog, or checkpoint text would become too large if it held all context.
- The user asks for OpenSpec-like proposal, design, task, spec delta, or archive behavior.

- 工作跨越两个或更多 harness 层。
- 工作涉及多个模块、服务、仓库、工具或运行时。
- 工作可能跨多个 agent 会话持续进行。
- 工作需要将 ADR、契约、就绪、实现和验证上下文关联在一起。
- NEXT、TODO、backlog 或 checkpoint 文本如果承载所有上下文会变得过大。
- 用户要求类似 OpenSpec 的提案、设计、任务、规范增量或归档行为。

Do not use a packet for:

以下情况不要使用包：

- A single command or direct factual answer.
- A narrow one-file documentation edit.
- A small bugfix whose contract and verification path are already obvious.
- Work already fully captured by an existing ADR, contract, issue, or checkpoint.

- 单条命令或直接的事实回答。
- 窄范围的单文件文档编辑。
- 契约和验证路径已经明显的小型 bug 修复。
- 已被现有 ADR、契约、issue 或 checkpoint 完全捕获的工作。

## Suggested Shape / 建议结构

Prefer a project-local convention over importing a tool-specific layout:

优先使用项目本地约定，而非导入工具特定的布局：

```text
docs/changes/
  <change-id>/
    proposal.md
    design.md
    tasks.md
    contracts.md
    tests.md
    verification.md
  archive/
    <YYYY-MM-DD>-<change-id>/
      proposal.md
      design.md
      tasks.md
      contracts.md
      tests.md
      verification.md
```

If the project already has another durable task packet convention, adapt this model to that convention instead of creating a competing source of truth.

如果项目已有其他持久化任务包约定，请将此模型适配到该约定，而非创建竞争性的真相来源。

OpenSpec is only a reference source for artifact discipline. Do not create or read `openspec/changes/*`, do not require OpenSpec installation, and do not expose `openspec init/update/apply/archive` as this harness model.

OpenSpec 仅作为制品纪律的参考来源。不要创建或读取 `openspec/changes/*`，不要要求安装 OpenSpec，不要将 `openspec init/update/apply/archive` 暴露为本 harness 模型。

## Native Templates / 原生模板

Use the bundled templates when a complex task needs a packet:

当复杂任务需要包时，使用捆绑模板：

```text
src/harness_governance/data/templates/change-packet/
  proposal.md
  design.md
  tasks.md
  contracts.md
  tests.md
  verification.md
```

Initialize a packet with:

使用以下命令初始化包：

```text
harness packet init <change-id>
```

The command writes `docs/changes/<change-id>/` using the native templates. It does not create `openspec/`, does not apply changes, and does not archive completed work.

该命令使用原生模板写入 `docs/changes/<change-id>/`。它不会创建 `openspec/`，不会应用变更，也不会归档已完成的工作。

## File Responsibilities / 文件职责

| File | Responsibility |
|---|---|
| `proposal.md` | Goal, motivation, scope, non-goals, affected users or systems. |
| `design.md` | Boundaries, responsibilities, data/control flow, alternatives, ADR candidates. |
| `tasks.md` | Layered task list with current blocking layer and ready/blocked state. |
| `contracts.md` | Schemas, fixtures, examples, API shapes, probes, checks, and acceptance criteria. |
| `tests.md` | Test owner, unit/integration/E2E applicability, test files or waiver, and red/green commands. |
| `verification.md` | Commands, evidence, failures, freshness, screenshots, traces, and remaining risk. |

Keep each file short. Move stable conclusions into the long-lived project sources instead of letting the packet become permanent documentation.

保持每个文件简短。将稳定的结论移入长期项目源，而非让包成为永久文档。

## Contract Delta Shape / 契约增量结构

In `contracts.md`, use these sections:

在 `contracts.md` 中，使用以下章节：

- `Current behavior`
- `Proposed behavior / contract delta`
- `Contract artifacts`
- `Acceptance checks`
- `Failure cases`

This borrows the useful part of spec delta thinking while keeping the output in the Contract layer. `contracts.md` can describe the delta, but it does not replace executable schema, fixture, probe, check script, acceptance test, or an explicitly justified documentation invariant.

这借鉴了规范增量思维的有用部分，同时将输出保持在 Contract 层。`contracts.md` 可以描述增量，但不能替代可执行的模式、夹具、探针、检查脚本、验收测试或明确论证的文档不变量。

## Layer Relationship / 层级关系

| Harness layer | Packet use |
|---|---|
| Idea / Brainstorming | Capture intent, options, risks, and non-goals. |
| Brief | Fix goal, success criteria, and current exclusions. |
| Architecture | Record boundaries, data flow, ownership, and ADR candidates. |
| ADR | Link to accepted decisions; do not replace ADRs with packet prose. |
| Contract | Link to schemas, fixtures, examples, probes, and checks. |
| Readiness | Confirm target-local rules, test plan, verification commands, and scope limits. |
| Implementation | Run test-writer first, record expected red evidence or waiver, then product-implementer works only on approved implementation slices. Do not expand scope from tasks alone. |
| Verification | Record fresh evidence and unresolved failures. |
| Review / Next | Archive stable conclusions back to official project state. |

## Status Rules / 状态规则

Use simple status words:

使用简单的状态词：

```text
draft
ready
active
blocked
done
archived
```

Rules:

规则：

- `ready` means the current layer has enough durable evidence to proceed.
- `active` means work is in progress at the stated layer.
- `blocked` must state the missing evidence, decision, contract, or external condition.
- `done` means the packet goal is satisfied, but archive may still be pending.
- `archived` means stable conclusions were copied or linked back to official project sources and the packet has moved under `docs/changes/archive/<YYYY-MM-DD>-<change-id>/` or the project's equivalent archive.

- `ready` 表示当前层有足够的持久化证据可以推进。
- `active` 表示工作在声明的层正在进行。
- `blocked` 必须说明缺失的证据、决策、契约或外部条件。
- `done` 表示包目标已满足，但归档可能仍在待定。
- `archived` 表示稳定结论已复制或链接回官方项目源，包已移至 `docs/changes/archive/<YYYY-MM-DD>-<change-id>/` 或项目的等效归档位置。

## Mechanical Packet Check / 机械包检查

Run:

运行：

```text
harness packet check [packet-path-or-id ...]
```

or through the root wrapper:

或通过根包装器：

```text
harness check packets
```

The checker enforces only mechanical packet hygiene:

检查器仅强制执行机械包卫生：

- required files exist: `proposal.md`, `design.md`, `tasks.md`, `contracts.md`, `tests.md`, `verification.md`;
- `tasks.md` contains a checkbox checklist;
- `contracts.md` declares a contract artifact or an explicit blocked reason;
- `tests.md` declares a test owner, unit/integration/E2E applicability, test files or blocked reason, and red/green commands, or a waiver with replacement verification and residual risk;
- `verification.md` records a command, result, or unable-to-verify reason;
- every `Status:` value is one of `draft`, `ready`, `active`, `blocked`, `done`, `archived`;
- archived packets link stable conclusions back to ADR, README, contract, verification, queue, or project index.

- 必需文件存在：`proposal.md`、`design.md`、`tasks.md`、`contracts.md`、`verification.md`；
- `tasks.md` 包含复选框清单；
- `contracts.md` 声明契约制品或明确的阻塞原因；
- `verification.md` 记录命令、结果或无法验证的原因；
- 每个 `Status:` 值是 `draft`、`ready`、`active`、`blocked`、`done`、`archived` 之一；
- 已归档的包将稳定结论链接回 ADR、README、契约、验证、队列或项目索引。

Passing the checker does not approve implementation. Readiness and the Implementation Entry Record still decide whether implementation can proceed.

通过检查器不等于批准实现。Readiness 和 Implementation Entry Record 仍然决定实现是否可以推进。

## Archive Rules / 归档规则

Before marking a packet archived, check whether stable conclusions need to be reflected in:

在将包标记为已归档之前，检查稳定结论是否需要反映到：

- ADR or decision notes.
- Schemas, fixtures, examples, probes, or checks.
- Verification documentation or verification records.
- NEXT, TODO, backlog, or checkpoint state.
- Documentation maps, README navigation, or agent instructions.

- ADR 或决策笔记。
- 模式、夹具、示例、探针或检查。
- 验证文档或验证记录。
- NEXT、TODO、backlog 或 checkpoint 状态。
- 文档地图、README 导航或 agent 指令。

If a conclusion stays only inside the packet, the packet is not archived.

如果结论仅留在包内，则包未被归档。

Keep the scheduler queue lean during archive:

归档期间保持调度器队列精简：

- Remove completed `[done]` items from `NEXT.md`; do not use the scheduler as a history log.
- Keep only executable `[ready]` items in `NEXT.md`, with at most a short-lived `[active]` item while a runner owns work.
- Preserve completed history in the archive directory or in the project's official issue/done record before deleting or moving old queue text.

- 从 `NEXT.md` 中移除已完成的 `[done]` 项；不要将调度器用作历史日志。
- 在 `NEXT.md` 中只保留可执行的 `[ready]` 项，当 runner 占用工作时最多保留一个短期的 `[active]` 项。
- 在删除或移动旧队列文本之前，将已完成的历史保留在归档目录或项目的官方 issue/done 记录中。

## Queue Integration / 队列集成

Queue items may point to a packet instead of repeating context:

队列项可以指向包而非重复上下文：

```text
[ready] Implement public projection contract fixture
Layer: contract
Change: docs/changes/public-projection-contract/
Evidence: contracts.md#fixtures
```

The queue remains the scheduler. The packet remains the context holder. Completed packets leave the scheduler and move to the archive; historical done facts must not be dropped during that move.

队列仍然是调度器。包仍然是上下文持有者。已完成的包离开调度器并移至归档；在该移动过程中不得丢弃历史完成事实。

## Common Mistakes / 常见错误

| Mistake | Correction |
|---|---|
| Treating packet tasks as implementation approval. | Readiness and contract gates still decide implementation. |
| Creating packets for every small task. | Use packets only when context would otherwise fragment. |
| Letting packets become permanent docs. | Archive stable conclusions back to official sources. |
| Replacing ADRs with `design.md`. | Use `design.md` to identify ADR candidates, then write ADRs. |
| Replacing checks with `contracts.md`. | Use `contracts.md` to link or specify executable checks. |
| Hiding blocked scope inside a packet. | Mirror blocked state to the project queue or checkpoint. |

## Minimal Decision Check / 最小决策检查

Before creating a packet, answer:

创建包之前，回答：

```text
Will a future agent need more than the queue item, ADR, and contract files to resume safely?
```

If yes, create or request a packet. If no, keep the existing harness artifacts lean.

如果是，创建或请求一个包。如果否，保持现有 harness 制品精简。
