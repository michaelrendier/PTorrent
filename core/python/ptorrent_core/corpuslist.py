"""The `[TAG] URL` acquisition list — a companion .txt named by a corpus .ptorrent.

Every line of the source becomes a record with a status and its 1-based line
number. Nothing is ever discarded: a line cannot go missing to a regex that
failed to match or a `continue` three frames up.

FIX vs the Android reference (`skills/corpus.parse_corpus_txt`):
  - tag regex is [A-Za-z0-9_]+, not [A-Z]+ — DARK_MATTER etc. no longer vanish
  - lines that are data-shaped and unparseable are counted as MALFORMED, not skipped
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from itertools import count

_ENTRY_RE = re.compile(r"^\[([A-Za-z0-9_]+)\]\s+(https?://\S+)\s*$")
_gen = count(1)


class ItemStatus(str, Enum):
    OK = "ok"              # parsed; usable
    IGNORED = "ignored"    # comment or blank — not data by construction
    MALFORMED = "malformed"  # data-shaped and unparseable — a hole


@dataclass
class CorpusRecord:
    index: int
    line: int
    status: ItemStatus
    raw: str
    tag: str | None = None
    url: str | None = None


class CorpusList:
    def __init__(self, records: list[CorpusRecord]):
        self.records = records
        self.generation = next(_gen)   # a fresh index space per parse

    @classmethod
    def parse(cls, text: str) -> "CorpusList":
        records: list[CorpusRecord] = []
        for i, raw in enumerate(text.splitlines()):
            lineno = i + 1
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                records.append(CorpusRecord(i, lineno, ItemStatus.IGNORED, raw))
                continue
            m = _ENTRY_RE.match(stripped)
            if m:
                records.append(CorpusRecord(i, lineno, ItemStatus.OK, raw,
                                            tag=m.group(1), url=m.group(2)))
            else:
                records.append(CorpusRecord(i, lineno, ItemStatus.MALFORMED, raw))
        return cls(records)

    @classmethod
    def load(cls, path: str) -> "CorpusList":
        with open(path, encoding="utf-8") as f:
            return cls.parse(f.read())

    # ── views ──
    def usable(self) -> list[CorpusRecord]:
        return [r for r in self.records if r.status is ItemStatus.OK]

    def count_status(self, s: ItemStatus) -> int:
        return sum(1 for r in self.records if r.status is s)

    def duplicates(self) -> list[tuple[int, int]]:
        """(index, first_index) pairs for exact-URL repeats among OK records.
        A separate pass — dedup policy is not a property of a line."""
        seen: dict[str, int] = {}
        out = []
        for r in self.usable():
            if r.url in seen:
                out.append((r.index, seen[r.url]))
            else:
                seen[r.url] = r.index
        return out

    def summary(self) -> dict:
        return {
            "generation": self.generation,
            "total": len(self.records),
            "ok": self.count_status(ItemStatus.OK),
            "ignored": self.count_status(ItemStatus.IGNORED),
            "malformed": self.count_status(ItemStatus.MALFORMED),
            "duplicates": len(self.duplicates()),
        }
