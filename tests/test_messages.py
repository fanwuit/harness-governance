"""Tests for the bilingual message catalog."""

from __future__ import annotations

import pytest

from harness_governance import messages
from harness_governance.messages import (
    MessageCatalog,
    bilingual,
    detect_language,
    set_language,
    t,
)


@pytest.fixture(autouse=True)
def _reset_language(monkeypatch):
    monkeypatch.delenv("HARNESS_LANG", raising=False)
    messages.detect_language.__defaults__ = ()  # type: ignore[attr-defined]
    yield


def test_default_language_is_english(monkeypatch) -> None:
    monkeypatch.delenv("HARNESS_LANG", raising=False)
    assert detect_language() == "en"


def test_env_override_selects_chinese(monkeypatch) -> None:
    monkeypatch.setenv("HARNESS_LANG", "zh-CN")
    assert detect_language() == "zh-CN"


def test_unknown_language_falls_back_to_english(monkeypatch) -> None:
    monkeypatch.setenv("HARNESS_LANG", "fr")
    assert detect_language() == "en"


def test_t_returns_english_by_default(monkeypatch) -> None:
    monkeypatch.delenv("HARNESS_LANG", raising=False)
    text = t("packet.empty_id")
    assert text == "Change id must not be empty."


def test_t_returns_chinese_when_active(monkeypatch) -> None:
    monkeypatch.setenv("HARNESS_LANG", "zh-CN")
    text = t("packet.empty_id")
    assert "不能为空" in text


def test_bilingual_renders_both_languages_in_zh_mode(monkeypatch) -> None:
    monkeypatch.setenv("HARNESS_LANG", "zh-CN")
    text = bilingual("packet.empty_id")
    assert "不能为空" in text
    assert "must not be empty" in text
    assert " / " in text


def test_bilingual_returns_only_english_in_en_mode(monkeypatch) -> None:
    monkeypatch.delenv("HARNESS_LANG", raising=False)
    text = bilingual("packet.empty_id")
    assert text == "Change id must not be empty."
    assert "/" not in text


def test_message_format_substitutes_placeholders(monkeypatch) -> None:
    monkeypatch.setenv("HARNESS_LANG", "zh-CN")
    text = bilingual("packet.label_invalid_status", label="x/y", filename="contracts.md", value="bogus")
    assert "x/y" in text
    assert "bogus" in text


def test_unknown_message_id_returns_id_itself() -> None:
    catalog = MessageCatalog("en")
    assert catalog.get("does.not.exist") == "does.not.exist"


def test_set_language_validates(monkeypatch) -> None:
    with pytest.raises(ValueError):
        set_language("fr")
    set_language("zh-CN")
    assert detect_language() == "zh-CN"
    monkeypatch.delenv("HARNESS_LANG")


def test_catalog_bilingual_format_consistent() -> None:
    catalog = MessageCatalog("zh-CN")
    text = catalog.bilingual("init.done")
    # Both halves should be non-empty and joined with " / ".
    parts = text.split(" / ", 1)
    assert len(parts) == 2
    assert parts[0] and parts[1]