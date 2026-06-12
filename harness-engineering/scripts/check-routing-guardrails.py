#!/usr/bin/env python3
"""Check local skill routing guardrails.

This script flags two failure modes:
- enabled local skills missing the harness precondition
- routing docs missing the companion containment rules that keep Superpowers
  from owning harness entry or transitions
"""

from __future__ import annotations

import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS_PRECONDITION = "## Harness Precondition"

ENTRY_DOCS = [
    ROOT / "AGENTS.md",
    ROOT / "harness-engineering" / "SKILL.md",
    ROOT / "harness-engineering" / "references" / "superpowers-routing.md",
]

ALLOWED_RISK_FILES = {
    pathlib.Path("AGENTS.md"),
    pathlib.Path("harness-engineering") / "SKILL.md",
    pathlib.Path("brainstorm-to-brief") / "SKILL.md",
}

REQUIRED_PHRASES = {
    ROOT / "AGENTS.md": [
        "Fast Path",
        "Trivial Safe Change",
        "Governed Path",
        "superpowers:using-superpowers",
        "terminal state",
        "REQUIRED SUB-SKILL",
    ],
    ROOT / "harness-engineering" / "SKILL.md": [
        "fast-path",
        "trivial-safe-change",
        "governed-path",
        "Entry lock",
        "Classify current layer",
        "Transition gate",
        "superpowers:using-superpowers",
    ],
    ROOT / "harness-engineering" / "references" / "superpowers-routing.md": [
        "Companion Capability Adapter",
        "starting any conversation",
        "before ANY response",
        "required sub-skills",
    ],
}

CANONICAL_LAYER_TERMS = [
    "Intake / Orientation",
    "Fact Discovery",
    "Implementation Readiness",
]

OLD_LAYER_CHAIN_PATTERN = re.compile(
    r"Idea\s*(?:->|\n\s*->\s*\n)\s*Brainstorming\s*(?:->|\n\s*->\s*\n)\s*Brief\s*"
    r"(?:->|\n\s*->\s*\n)\s*Architecture\s*(?:->|\n\s*->\s*\n)\s*ADR\s*"
    r"(?:->|\n\s*->\s*\n)\s*Contract\s*(?:->|\n\s*->\s*\n)\s*Implementation\s*"
    r"(?:->|\n\s*->\s*\n)\s*Verification\s*(?:->|\n\s*->\s*\n)\s*Review / Next",
    re.MULTILINE,
)


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def enabled_skill_files() -> list[pathlib.Path]:
    skill_files = []
    for path in ROOT.glob("*/SKILL.md"):
        if path.parts[-2] in {".system", "harness-engineering", "skill-use-transparency"}:
            continue
        skill_files.append(path)
    return sorted(skill_files)


def check_preconditions(errors: list[str]) -> None:
    for path in enabled_skill_files():
        text = read_text(path)
        if HARNESS_PRECONDITION not in text:
            errors.append(f"{path.relative_to(ROOT)} missing {HARNESS_PRECONDITION}")


def check_required_phrases(errors: list[str]) -> None:
    for path, phrases in REQUIRED_PHRASES.items():
        if not path.exists():
            errors.append(f"{path.relative_to(ROOT)} missing")
            continue
        text = read_text(path)
        for phrase in phrases:
            if phrase not in text:
                errors.append(f"{path.relative_to(ROOT)} missing phrase: {phrase}")


def check_companion_risks(errors: list[str]) -> None:
    risky = re.compile(
        r"(starting any conversation|before ANY response|MUST use this before|REQUIRED SUB-SKILL|terminal state)",
        re.IGNORECASE,
    )
    local_hits = []
    for path in enabled_skill_files() + ENTRY_DOCS:
        text = read_text(path)
        if "superpowers-routing.md" in str(path):
            continue
        for match in risky.finditer(text):
            local_hits.append((path.relative_to(ROOT), match.group(0)))

    for rel_path, term in local_hits:
        if rel_path not in ALLOWED_RISK_FILES:
            errors.append(f"{rel_path} contains uncontained risky routing phrase: {term}")


def check_layer_progression_drift(errors: list[str]) -> None:
    for path in [ROOT / "README.md", ROOT / "harness-engineering" / "SKILL.md"]:
        text = read_text(path)
        missing = [term for term in CANONICAL_LAYER_TERMS if term not in text]
        if missing:
            errors.append(f"{path.relative_to(ROOT)} missing canonical layer term(s): {', '.join(missing)}")
        if OLD_LAYER_CHAIN_PATTERN.search(text) and "简化视图" not in text:
            errors.append(
                f"{path.relative_to(ROOT)} contains the old layer chain without marking it as a simplified view"
            )


def main() -> int:
    errors: list[str] = []
    check_preconditions(errors)
    check_required_phrases(errors)
    check_companion_risks(errors)
    check_layer_progression_drift(errors)

    if errors:
        print("Routing guardrail check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Routing guardrail check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
