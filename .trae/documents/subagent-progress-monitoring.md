# Plan: Subagent 执行进度监控 + 遗留清理

## 问题

1. subagent 执行过程中无法判断是卡死还是正在执行——无心跳、无进度、无 running 状态 checkpoint
2. 代码中存在多处过时残留：DEPRECATED 标记、"3 tiers" 注释、legacy codex-exec 路径等

## 遗留清理清单（完整排查结果）

| # | 文件 | 行号 | 残留内容 | 处理方式 |
|---|------|------|----------|----------|
| R1 | `commands/runner.py` | 74, 201 | `DEPRECATED` 标记 + warning | 改为"headless 自动化模式"定位 |
| R2 | `commands/init.py` | 386 | 注释 "3 tiers each" | 改为 "4 tiers each" |
| R3 | `commands/init.py` | 443 | 注释 "Write all 3 tier skills (strict / standard / light)" | 改为 "4 tier skills (strict / standard / light / monitor)" |
| R4 | `commands/check.py` | 494,498,502 | `_obsolete_paths` 提示 "3 tiers" | 改为 "4 tiers" |
| R5 | `commands/status.py` | 55,158-160 | `_LEGACY_INVOCATION_LOG` codex-exec 兼容路径 | 保留（向后兼容，但注释更新为"migration compat"） |
| R6 | `runner/adapters/codex_cli.py` | 3 | docstring "Mirrors the legacy..." | 更新为双模式定位 |
| R7 | `runner/loop.py` | 3 | docstring "Mirrors the legacy..." | 更新措辞 |
| R8 | `tests/test_subagent_runner/test_codex_cli.py` | 15 | `PATCH_RUN = "...subprocess.run"` | 改为 `subprocess.Popen`（随 codex_cli.py 重构） |
| R9 | `tests/test_parity_legacy.py` | 4 | 提及 "legacy scripts were deleted" | 文件名和注释更新（功能保留） |

**不清理的项**（有实际用途）：
- `check.py` 的 `_obsolete_names` / `_obsolete_paths` 检查逻辑本身——这是 check 命令的功能，用于检测用户项目中的过时引用
- `status.py` 的 `_LEGACY_INVOCATION_LOG`——向后兼容，用户可能有旧的 codex-exec 日志
- `entry.py` / `check.py` / `file_ops/entry.py` 中的 "legacy" 注释——仅是文档性说明，不影响功能
- `data/references/` 中的 `harness-engineering`、`superpowers:*` 引用——这些是参考文档，记录了历史命名映射

## 改动方案

### 1. 遗留清理

#### R1: runner.py — 去除 DEPRECATED 标记，重新定位

```python
# 旧:
"DEPRECATED — they spawn external CLI processes, not subagents."
# 新:
"for headless/CI automation. Use 'orchestrator' for interactive agent sessions."

# 旧 (line 197-204):
logging.warning("DEPRECATED: --executor %s spawns an external CLI process, ...")
# 新:
# 删除整个 if 块（warning 不再需要）
```

#### R2-R4: "3 tiers" → "4 tiers"

- `init.py:386`: `"3 tiers each"` → `"4 tiers each"`
- `init.py:443`: `"Write all 3 tier skills (strict / standard / light)"` → `"Write all 4 tier skills (strict / standard / light / monitor)"`
- `check.py:494,498,502`: `"(3 tiers)"` → `"(4 tiers)"`

#### R5: status.py legacy 注释更新

```python
# 旧:
_LEGACY_INVOCATION_LOG = ".harness/codex-exec-invocations.ndjson"
# 新:
# Migration compat: pre-0.8 projects may have codex-exec invocation logs.
_LEGACY_INVOCATION_LOG = ".harness/codex-exec-invocations.ndjson"
```

#### R6-R7: adapter/loop docstring 更新

`codex_cli.py`:
```python
# 旧:
"""Codex CLI adapter... Mirrors the legacy run-autonomous-ready-loop.sh..."""
# 新:
"""Codex CLI headless executor for CI/CD automation.

Use ``--executor codex`` for unattended runs where the agent is invoked
as an external process. For interactive sessions, prefer ``--executor
orchestrator`` which generates a prompt for native platform subagent
dispatch.
"""
```

`loop.py`:
```python
# 旧:
"""Mirrors the legacy run-autonomous-ready-loop.sh semantics:"""
# 新:
"""Autonomous-ready execution loop:"""
```

### 2. 心跳公共逻辑

**新建**: `src/harness_governance/runner/adapters/_heartbeat.py`

```python
@dataclass(slots=True)
class HeartbeatCounters:
    stdout_lines: int = 0
    stderr_lines: int = 0

def start_heartbeat_thread(
    proc, heartbeat_path, counters, interval_seconds, started_at,
) -> threading.Thread:
    """Daemon thread: writes NDJSON heartbeat entries while proc is alive."""
    def _loop():
        while proc.poll() is None:
            time.sleep(interval_seconds)
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "elapsed_s": round(time.monotonic() - started_at, 1),
                "stdout_lines": counters.stdout_lines,
                "stderr_lines": counters.stderr_lines,
                "pid": proc.pid,
            }
            with heartbeat_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t

def format_progress_line(elapsed_s, stdout_lines, stderr_lines) -> str:
    return f"[harness runner] elapsed: {elapsed_s:.0f}s, stdout: {stdout_lines} lines, stderr: {stderr_lines} lines"
```

### 3. SubprocessAgentExecutor: 心跳 + 进度行

**文件**: `src/harness_governance/runner/adapters/generic.py`

- 新增 `heartbeat_interval_seconds: int = 30` 参数（0 禁用）
- 新增 `heartbeat_dir: Path | None = None` 参数
- `execute()` 中：启动心跳线程 + 逐行计数 + 每 60s stderr 进度行

### 4. CodexCliExecutor: Popen 化 + 心跳

**文件**: `src/harness_governance/runner/adapters/codex_cli.py`

- 从 `subprocess.run(capture_output=True)` 改为 `subprocess.Popen` + 逐行读
- 新增 `heartbeat_interval_seconds: int = 30` 参数
- 复用 `_heartbeat.py` 的心跳逻辑

### 5. AutonomousReadyLoop: running checkpoint

**文件**: `src/harness_governance/runner/loop.py`

- `execute()` 调用前写 "running" checkpoint
- 新增 `heartbeat_interval_seconds: int = 30` 参数，传给 executor

### 6. CLI: `--heartbeat-interval` 选项

**文件**: `src/harness_governance/commands/runner.py`

- 新增 `--heartbeat-interval` 选项（默认 30s，0 禁用）
- 传给 `AutonomousReadyLoop`

### 7. messages.py: 新增 i18n 消息

- `runner.heartbeat_progress` — 进度行
- `runner.round_started` — round 开始

### 8. 测试更新

**文件**: `tests/test_subagent_runner/test_codex_cli.py`

- `PATCH_RUN` 从 `subprocess.run` 改为 `subprocess.Popen`（随 codex_cli.py 重构）
- 新增心跳相关测试：`test_heartbeat_writes_ndjson`、`test_heartbeat_disabled_when_zero`、`test_progress_line_output`

**文件**: `tests/test_runner.py`

- 新增 `test_running_checkpoint_before_execute` 测试
- 新增心跳集成测试

**文件**: `tests/test_subagent_runner/test_cli_integration.py`

- 更新 subprocess executor 相关测试（去除 DEPRECATED 预期）

## 不改动的部分

- `AgentExecutor` ABC 接口不变
- `ExecutionResult` 不变
- `OrchestratorPromptBuilder` 不变
- `ResultParser` / `SubagentResult` 不变
- `adapters/__init__.py` 导出不变
- `check.py` 的 `_obsolete_names` / `_obsolete_paths` 检查逻辑保留（是功能不是残留）
- `status.py` 的 `_LEGACY_INVOCATION_LOG` 保留（向后兼容）
- `data/references/` 中的历史命名引用保留（参考文档）

## 验证步骤

1. `harness runner start --executor subprocess --command "python -c 'import time; [print(i) or time.sleep(10) for i in range(12)]'" --timeout-seconds 180 --heartbeat-interval 10`
   - 验证：heartbeat.ndjson 每 10s 写一行，stderr 每 60s 输出进度行
2. `harness runner start --executor codex --timeout-seconds 180 --heartbeat-interval 15`
   - 验证：执行期间不再完全静默
3. 超时场景：`--timeout-seconds 5` 执行一个 sleep 30 的命令
   - 验证：5s 后被 kill，heartbeat 文件记录到超时前一刻
4. `cat .harness/run-checkpoint.md` 在 round 执行期间查看
   - 验证：stop_reason 显示 "running: round 1, ..."
5. `--heartbeat-interval 0` 禁用心跳
   - 验证：无 heartbeat 文件，无进度行
6. `harness runner start --executor orchestrator` 不受影响
7. `harness check docs-self` 不再报告 "3 tiers" 过时路径
8. 测试套件全部通过
