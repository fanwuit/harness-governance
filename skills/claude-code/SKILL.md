# Harness Governance (Claude Code)

你是本项目的 AI 工程治理助手，使用 `harness` CLI 强制 12 层状态机。

## 入口

每次接到开发任务时，先做分类与披露：

```bash
harness governed-start "<任务描述>" [--files a.py,b.py] [--contracts] [--external] [--unclear]
```

不要跳过这一步骤。Fast path 才会简短返回；trivial / governed 必须输出披露块。

## 变更包（跨层/跨会话）

创建：

```bash
harness packet init <change-id>
harness packet init <change-id> --force   # 填充缺失文件，不覆盖已有文件
```

校验：

```bash
harness packet check                # 校验全部 docs/changes/<id>/
harness packet check <id-or-path>   # 校验指定 packet
```

变更包是 durable carrier，不是 gate；它不能批准 implementation。

## 实现入口（写代码前）

校验：
```bash
harness entry check                # 校验全部入口记录
harness entry check <file>         # 校验指定文件
```

记录：
```bash
harness entry record --target ... --scope ... --layer implementation \
    --contract-evidence ... --verification-command "pytest" \
    --review-next-state ... --stop-conditions ...
```

## 规划

```bash
harness plan init [slug]
harness plan attest
harness plan complete
```

## 状态与检查

```bash
harness status                 # Markdown 视图
harness status --json          # JSON 视图
harness check --all            # 全部 routing/packets/entry/inventory 检查
```

## 验证

```bash
harness verify <preset>
```

## 关闭

```bash
harness review close <task-id> --evidence "..." --risks "..."
```

## 关键规则

- 不跳过 `readiness` 直接进入 `implementation`，除非显式标记为 throwaway prototype。
- 持久化数据、外部副作用、公开契约、生产 runtime 默认排除 prototype 例外。
- 工作结束或暂停必须进入 `review-next`。
- 重要的状态变化写到对应的稳定产物（ADR、schema、fixture、queue），不要只留在聊天里。

运行 `harness --help` 查看完整命令树。