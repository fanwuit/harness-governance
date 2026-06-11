# Debugging Fact Workflow

用于把 systematic debugging 的有效动作落到本项目 Fact Discovery / Implementation / Verification 链路。主动排障时优先使用本 workflow；`debugging-checklist` 只负责轻量 handoff。

## Local Owner

- Owner skill: `observable-fact-discovery`
- Supporting skills: `debugging-checklist`, `contract-first-development`, `review-next-governance`
- Stable evidence: repro steps、logs、fixture、probe、minimal failing command、fix verification

## Workflow

### 1. Reproduce

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

不能复现时，不要猜修；记录缺失的环境、输入、权限或样本。

### 2. Observe

记录直接证据：

- 错误文本、stack trace、exit code。
- 输入、输出、配置、版本。
- 日志片段或 trace。
- 相关 fixture / sample。

把证据和推断分开写。不要把“看起来像”写成事实。

### 3. Isolate

缩小失败边界：

- 最小失败命令。
- 最小输入样本。
- 工作对照样例。
- 最近变更或依赖差异。
- 首个确定错误的位置。

### 4. Hypothesis

一次只验证一个假设：

```markdown
## Hypothesis
- Hypothesis:
- Why plausible:
- Test:
- Result:
- Decision: keep | reject | refine
```

同一个失败动作连续出现时，必须改变方法：换证据源、换更小样本、换对照路径，或暂停为 blocked。

### 5. Fix / Verify

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

## Forbidden Shortcuts

- 不先猜修。
- 不用截图、主观观感或日志包含某词替代可复现事实。
- 不把一次成功路径当完整覆盖。
- 不在事实不足时扩大实现范围。

