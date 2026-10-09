"""Addressable source spans and parsed Markdown tables, using only the stdlib."""

import csv
from dataclasses import dataclass, field
import hashlib
import re

from .lexical import rank_spans


@dataclass(frozen=True)
class Span:
    key: str
    start: int
    end: int
    text: str

    def as_record(self):
        return vars(self)


@dataclass(frozen=True)
class Table:
    key: str
    header: Span
    columns: tuple[str, ...]
    rows: tuple[Span, ...]
    cells: tuple[tuple[str, ...], ...]

    def summary(self):
        return {"columns": list(self.columns), "row_count": len(self.rows),
                "header": self.header.text, "opening_rows": [r.text for r in self.rows[:3]]}


def cells(line):
    return tuple(cell.strip() for cell in next(csv.reader(
        [line.strip().strip("|")], delimiter="|", escapechar="\\", quoting=csv.QUOTE_NONE)))


def table_regions(text):
    lines, offset = [], 0
    for line in text.splitlines(keepends=True):
        lines.append((offset, line))
        offset += len(line)
    tables, index = [], 0
    while index + 1 < len(lines):
        start, header = lines[index]
        delimiter = lines[index + 1][1]
        widths = cells(delimiter) if "|" in delimiter else ()
        if "|" not in header or len(widths) < 2 or not all(re.fullmatch(r":?-{3,}:?", c) for c in widths):
            index += 1
            continue
        columns, rows, values = cells(header), [], []
        if len(columns) != len(widths):
            index += 1
            continue
        key = f"table:{len(tables) + 1}"
        index += 2
        while index < len(lines) and "|" in lines[index][1]:
            row_start, raw = lines[index]
            parsed = cells(raw)
            if len(parsed) != len(columns):
                break
            rows.append(Span(f"{key}:row:{len(rows) + 1}", row_start, row_start + len(raw), raw))
            values.append(parsed)
            index += 1
        if rows:
            tables.append(Table(key, Span(f"{key}:header", start, start + len(header), header),
                                columns, tuple(rows), tuple(values)))
    return tuple(tables)


@dataclass
class Document:
    source: str
    title: str
    text: str
    window_size: int
    processed: set[str] = field(default_factory=set)
    attempted_tables: set[str] = field(default_factory=set)
    report_attempted: bool = False

    def __post_init__(self):
        self.tables = table_regions(self.text)
        spans, start = [], 0
        # Smaller addressable chunks allow either ordered windows or ranked probes.
        chunk_size = max(100, self.window_size // 3)
        while start < len(self.text):
            end = min(len(self.text), start + chunk_size)
            if end < len(self.text):
                newline = self.text.rfind("\n", start + chunk_size // 2, end)
                if newline >= 0:
                    end = newline + 1
            spans.append(Span(f"chunk:{len(spans) + 1}", start, end, self.text[start:end]))
            start = end
        self.spans = tuple(spans)
        self.sha256 = hashlib.sha256(self.text.encode()).hexdigest()

    def remaining(self):
        return tuple(s for s in self.spans if s.key not in self.processed)

    def summary(self):
        return {"source": self.source, "title": self.title, "characters": len(self.text),
                "opening": self.text[:500], "chunks": len(self.spans),
                "outline": [line[:240] for line in self.text.splitlines() if line.startswith("#")][:50],
                "tables": {t.key: t.summary() for t in self.tables}}

