from __future__ import annotations

import re

SCORER_VERSION = "concept-v1"
WORD_RE = re.compile(r"[a-z0-9]+")

SEMANTIC_KEYWORD_ALIASES: dict[str, tuple[str, ...]] = {
    "focus": (
        "focus",
        "pay attention to",
        "pays attention to",
    ),
    "relevant context": (
        "relevant context",
        "important context",
    ),
    "context": (
        "context",
        "surrounding information",
    ),
    "tools": (
        "tools",
        "external tools",
    ),
    "guardrails": (
        "guardrails",
        "safety boundaries",
    ),
}


def normalized_phrase(text: str) -> str:
    return " ".join(WORD_RE.findall(text.lower()))


def phrase_present(answer: str, phrase: str) -> bool:
    normalized_answer = f" {normalized_phrase(answer)} "
    normalized = normalized_phrase(phrase)
    return bool(normalized) and f" {normalized} " in normalized_answer


def keyword_match_mode(answer: str, keyword: str) -> str | None:
    if phrase_present(answer, keyword):
        return "literal"

    normalized_keyword = normalized_phrase(keyword)
    for alias in SEMANTIC_KEYWORD_ALIASES.get(normalized_keyword, ()):
        if alias != normalized_keyword and phrase_present(answer, alias):
            return "semantic_alias"
    return None
