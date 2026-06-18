# State Contract Closure

Any CLI command that claims persisted governance state is `confirmed`,
`recorded`, `passed`, or otherwise durable must have evidence for the full
writer-to-consumer path.

Required coverage:

1. Writer test: the CLI command writes the expected persisted state.
2. Consumer test: the downstream `check` or `gate` command accepts that state.
3. Negative test: missing or mismatched state still blocks the consumer.
4. E2E smoke: at least one governed-path flow uses the public CLI only.

Current required contracts:

| Contract | Writer | Consumer | Evidence |
|---|---|---|---|
| Author questions | `harness layer answer`, `harness layer ask` | `harness gate check <layer>` | `tests/test_commands/test_layer_cmd.py` |
| Tech-stack lint confirmation | `harness tech-stack lint <language> --tool <tool>` | `harness tech-stack check`, intake gate | `tests/test_commands/test_tech_stack_cmd.py` |
| Strict governed-path smoke | `harness governed-start` and public state writers | `harness gate check`, `harness layer advance` | `tests/test_e2e/test_governed_path_smoke.py` |

Run:

```bash
harness state-contract check
```
