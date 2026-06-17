# Debugging Fact Workflow / 调试事实工作流

Localizes effective actions from systematic debugging into this project's Fact Discovery / Implementation / Verification chain. Use this workflow preferentially during active troubleshooting; `debugging-checklist` only handles lightweight handoff.

用于把 systematic debugging 的有效动作落到本项目 Fact Discovery / Implementation / Verification 链路。主动排障时优先使用本 workflow；`debugging-checklist` 只负责轻量 handoff。

## Local Owner / 本地所有者

- Owner skill: `observable-fact-discovery`
- Supporting skills: `debugging-checklist`, `contract-first-development`, `review-next-governance`
- Stable evidence: repro steps, logs, fixtures, probes, minimal failing command, fix verification / 稳定证据：repro steps、logs、fixture、probe、minimal failing command、fix verification

## Workflow / 工作流

### 1. Reproduce / 复现

Record a stable reproduction path:

记录稳定复现路径：

```markdown
## Reproduce
- Command / steps:
- Frequency:
- Environment:
- Expected:
- Actual:
- If not reproducible:
```

When not reproducible, do not guess-fix; record the missing environment, input, permissions, or sample.

不能复现时，不要猜修；记录缺失的环境、输入、权限或样本。

### 2. Observe / 观察

Record direct evidence:

记录直接证据：

- Error text, stack trace, exit code. / 错误文本、stack trace、exit code。
- Input, output, configuration, version. / 输入、输出、配置、版本。
- Log fragments or traces. / 日志片段或 trace。
- Related fixtures / samples. / 相关 fixture / sample。

Separate evidence from inference. Do not write "looks like" as fact.

把证据和推断分开写。不要把"看起来像"写成事实。

### 3. Isolate / 隔离

Narrow the failure boundary:

缩小失败边界：

- Minimal failing command. / 最小失败命令。
- Minimal input sample. / 最小输入样本。
- Working control sample. / 工作对照样例。
- Recent changes or dependency differences. / 最近变更或依赖差异。
- First confirmed error location. / 首个确定错误的位置。

### 4. Hypothesis / 假设

Test one hypothesis at a time:

一次只验证一个假设：

```markdown
## Hypothesis
- Hypothesis:
- Why plausible:
- Test:
- Result:
- Decision: keep | reject | refine
```

When the same failing action recurs, you must change approach: switch evidence sources, use a smaller sample, try a control path, or pause as blocked.

同一个失败动作连续出现时，必须改变方法：换证据源、换更小样本、换对照路径，或暂停为 blocked。

### 5. Fix / Verify / 修复 / 验证

The fix must return to the minimal failing command and related regression checks:

修复必须回到最小失败命令和相关回归检查：

```markdown
## Fix / Verify
- Fix boundary:
- Commands run:
- Result:
- Regression coverage:
- Residual risk:
- Next layer:
```

## Forbidden Shortcuts / 禁止的捷径

- Do not guess-fix first. / 不先猜修。
- Do not replace reproducible facts with screenshots, subjective impressions, or "log contains X". / 不用截图、主观观感或日志包含某词替代可复现事实。
- Do not treat a single successful path as full coverage. / 不把一次成功路径当完整覆盖。
- Do not expand implementation scope when facts are insufficient. / 不在事实不足时扩大实现范围。
