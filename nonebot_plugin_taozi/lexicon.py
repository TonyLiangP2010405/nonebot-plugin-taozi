from __future__ import annotations

import difflib
import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from .models import LexiconEntry

_ENTRY_LIST_ADAPTER = TypeAdapter(list[LexiconEntry])
_SPACE_RE = re.compile(r"\s+")


def normalize_term(value: str) -> str:
    """Normalize user input without changing the displayed canonical term."""

    return _SPACE_RE.sub("", value).casefold()


class TaoziLexicon:
    def __init__(self, entries: list[LexiconEntry]) -> None:
        if not entries:
            raise ValueError("桃系词典不能为空")

        self._entries = tuple(entries)
        self._index: dict[str, LexiconEntry] = {}
        for entry in self._entries:
            for name in (entry.term, *entry.aliases):
                normalized = normalize_term(name)
                previous = self._index.get(normalized)
                if previous is not None and previous.term != entry.term:
                    raise ValueError(f"词条别名冲突：{name}")
                self._index[normalized] = entry

    @classmethod
    def from_json_text(cls, payload: str) -> TaoziLexicon:
        raw: Any = json.loads(payload)
        return cls(_ENTRY_LIST_ADAPTER.validate_python(raw))

    @classmethod
    def from_path(cls, path: Path) -> TaoziLexicon:
        return cls.from_json_text(path.read_text(encoding="utf-8"))

    @property
    def entries(self) -> tuple[LexiconEntry, ...]:
        return self._entries

    def find(self, query: str) -> LexiconEntry | None:
        return self._index.get(normalize_term(query))

    def suggest(self, query: str, *, limit: int = 3) -> list[str]:
        normalized = normalize_term(query)
        if not normalized:
            return []

        contained = [
            entry.term
            for entry in self._entries
            if normalized in normalize_term(entry.term)
            or any(normalized in normalize_term(alias) for alias in entry.aliases)
        ]
        if contained:
            return contained[:limit]

        matches = difflib.get_close_matches(normalized, self._index.keys(), n=limit, cutoff=0.45)
        suggestions: list[str] = []
        for match in matches:
            term = self._index[match].term
            if term not in suggestions:
                suggestions.append(term)
        return suggestions

    def list_terms(self) -> str:
        return "、".join(entry.term for entry in self._entries)


def load_builtin_lexicon() -> TaoziLexicon:
    resource = resources.files("nonebot_plugin_taozi").joinpath("resources/lexicon.json")
    return TaoziLexicon.from_json_text(resource.read_text(encoding="utf-8"))


def render_entry(
    entry: LexiconEntry,
    *,
    show_sources: bool = True,
    compact: bool = False,
) -> str:
    lines = [
        f"【{entry.term}】",
        f"所指对象：{entry.subject}",
        f"解释：{entry.meaning}",
        f"可信度：{entry.confidence}",
        f"边界：{entry.boundary}",
    ]
    if entry.aliases and not compact:
        lines.insert(1, f"别名：{'、'.join(entry.aliases)}")

    if show_sources:
        lines.append("代表出处：")
        sources = entry.sources[:1] if compact else entry.sources
        for index, source in enumerate(sources, start=1):
            lines.append(f"{index}. {source.title}")
            lines.append(source.url)

    if not compact:
        lines.append(f"最后核验：{entry.verified_at}")
        lines.append("注：非官方粉丝整理，含义会随社区语境变化。")
    return "\n".join(lines)


BUILTIN_LEXICON = load_builtin_lexicon()

