# Contributing to harness-governance

Thank you for your interest in contributing! This document covers setup, development workflow, and project conventions.

## Development Setup

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/fanwuit/my-agent-first-skills.git
cd my-agent-first-skills
pip install -e ".[dev]"
```

The `[dev]` extra includes pytest, pytest-cov, ruff, mypy, and pre-commit.

## Running Tests

```bash
# Full test suite
pytest

# With coverage report
pytest --cov=src/harness_governance --cov-report=term-missing

# Single test file
pytest tests/test_cli.py -v
```

Current target: **94% coverage**, all tests green.

## Code Style

This project uses standard Python conventions with type hints throughout:

- **Type hints**: all public function signatures are annotated.
- **Docstrings**: Google-style for public APIs; one-line summaries for private helpers.
- **Imports**: `from __future__ import annotations` at the top of every module.
- **Path handling**: always use `pathlib.Path`, never string concatenation.
- **i18n**: all user-facing strings go through `messages.py` with both `en` and `zh-CN` translations.

Linting tools (optional but recommended):

```bash
ruff check src/ tests/
mypy src/
```

## Project Structure

```
src/harness_governance/
├── cli.py                    # Click entry point
├── logging_setup.py          # --verbose / --debug configuration
├── messages.py               # bilingual message catalog
├── config/                   # defaults.py + settings.py (TOML loader)
├── models/                   # Pydantic v2 schemas
├── commands/                 # one module per CLI subcommand
├── state_machine/            # layers, classification, transitions, engine
├── file_ops/                 # Markdown file read/write helpers
├── runner/                   # autonomous runner + adapters
├── plugins/                  # optional extensions
└── data/                     # templates, references, fixtures
```

## Making Changes

1. Create a feature branch from `main`.
2. Write tests for new functionality.
3. Run the full test suite: `pytest`.
4. Ensure coverage does not regress: `pytest --cov=src/harness_governance`.
5. Submit a pull request with a clear description.

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) in Chinese or English:

```
feat: 新增 xxx 功能
fix: 修复 xxx 问题
docs: 更新 xxx 文档
refactor: 重构 xxx 模块
test: 补充 xxx 测试
chore: 更新依赖/配置
```

## Adding New Commands

1. Create `commands/<name>.py` with a `@click.command` or `@click.group`.
2. Add the command to `commands/__init__.py` and register it in `cli.py`.
3. Add bilingual message IDs to `messages.py`.
4. Write tests in `tests/test_commands/`.

## Adding New Platforms

Adding a new agent platform requires changes in **8 files**:

1. `config/defaults.py` — add to `PLATFORM_SKILL_PATHS`, `PLATFORM_HINTS`, `ENV_HINTS`.
2. `models/schemas.py` — add to `HarnessConfig.agent_platform` Literal.
3. `runner/orchestrator.py` — add to dispatch dicts.
4. `data/skills/<platform>.md` — platform skill adapter.
5. `tests/` — at least 2 tests (detection + skill path).
6. `README.md` — update platform table.
7. `QUICKSTART.md` — add runner instructions.
8. This file — update the platform count if mentioned elsewhere.

## License

MIT — see [LICENSE](LICENSE).
