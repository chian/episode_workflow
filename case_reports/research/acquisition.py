"""Strategy > search > page > table/report/lexical reading episode bindings."""

from datetime import datetime, timezone
from dataclasses import replace
import json

from ...method_loop import SourceEnd
from ...task_executors._http import ProviderError
from ...task_executors.outbreak_search.queries import (
    source_locator, source_text, search_results_from_provider,
)
from .admission import extract_and_admit, exact_span
from .assumptions import text as required_text
from .documents import Document, Span, rank_spans
from .engine import ResearchSource, selected_choice
from .records import ResearchResult


class StrategySource(ResearchSource):
    def __init__(self, run, inherited, *, approach):
        super().__init__(run, inherited)
        self.approach = approach
        self.queries = []

    def propose(self, view):
        proposal = self.run.agent(self.inputs(view, operation="propose_strategy_query",
            approach=self.approach, previous_queries=self.queries,
            instruction="Propose a search within this evidence approach using prior source findings and failures. Do not stop; numerical yield controls continuation. Do not repeat an identical query.",
            response_contract={"type": "object", "additionalProperties": False,
                "required": ["query", "objective"], "properties": {
                    "query": {"type": "string", "minLength": 1, "description": "New concrete search query"},
                    "objective": {"type": "string", "minLength": 1, "description": "Information this search should resolve"},
                    "child_model_calls": self.child_budget_schema()}}))
        self.last_proposal = proposal
        query = required_text(proposal.get("query"), "query")
        if query.casefold().strip() in {q.casefold().strip() for q in self.queries}:
            raise ValueError("This strategy has already searched that query")
        objective = required_text(proposal.get("objective"), "objective")
        child = self.run.child(view, SearchSource(self.run, self.ledger.result(), query=query),
            "search", objective, self.focus, proposal=proposal,
            contract=self.contract(f"Determine how results for {query!r} bear on {self.approach}", self.focus))
        self.queries.append(query)
        return self.edge(child)


class SearchSource(ResearchSource):
    def __init__(self, run, inherited, *, query):
        super().__init__(run, inherited)
        self.query, self.candidates = query, None
        self.visited = set()

    def propose(self, view):
        if self.candidates is None:
            try:
                raw = search_results_from_provider(self.run.providers.search(self.query, self.run.limits.search_limit))
            except (ProviderError, OSError, ValueError) as exc:
                self.failure = "search_provider_failure"
                return self.leaf(lambda error=exc: self.failure_result(error, "search"), "search_failure")
            unique = {source_locator(r): r for r in raw if source_locator(r)}
            self.candidates = {f"source:{i}": r for i, r in enumerate(unique.values(), 1)}
        remaining = {k: r for k, r in self.candidates.items() if k not in self.visited}
        if not remaining:
            return None
        proposal = self.run.agent(self.inputs(view, operation="choose_research_source", query=self.query,
            candidates={k: {"url": source_locator(r), "title": r.get("title", ""),
                            "description": r.get("description", r.get("snippet", ""))} for k, r in remaining.items()},
            response_contract={"type": "object", "additionalProperties": False,
                "required": ["option", "question"], "properties": {
                    "option": {"type": "string", "enum": list(remaining)},
                    "child_model_calls": self.child_budget_schema(),
                    "question": {"type": "string", "minLength": 1,
                                 "description": "Evidence to seek in the selected source"}}},
            instruction="Select using actual prior source findings. Return an instance of the JSON Schema: the source choice belongs in the top-level field option. Selection is not permission to stop."))
        self.last_proposal = proposal
        if "option" not in proposal:
            raise ValueError(f"Missing required top-level field 'option'; received fields {list(proposal)!r}. "
                             f"Set 'option' to one of {list(remaining)!r}. No source was selected or visited.")
        option = selected_choice(proposal.get("option"), remaining, "option")
        question = required_text(proposal.get("question"), "question")
        source = PageSource(self.run, self.ledger.result(), candidate=remaining[option])
        child = self.run.child(view, source, "page", question, self.focus, proposal=proposal,
            contract=self.contract(f"Judge what this source establishes about {question}", self.focus))
        self.visited.add(option)
        return self.edge(child)


class PageSource(ResearchSource):
    def __init__(self, run, inherited, *, candidate):
        super().__init__(run, inherited)
        self.candidate, self.document = candidate, None

    def prepare(self):
        locator = source_locator(self.candidate)
        text = source_text(self.candidate) or self.run.documents.get(locator, {}).get("text", "")
        if not text:
            retrieved = self.run.providers.retrieve(self.candidate)
            text = retrieved if isinstance(retrieved, str) else source_text(retrieved or {})
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Source retrieval returned no document text; this is not negative evidence")
        self.document = Document(locator, self.candidate.get("title", ""), text, self.run.limits.text_window_chars)
        version = {"text": text, "sha256_utf8": self.document.sha256,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "spans": [s.as_record() for s in self.document.spans],
            "tables": {t.key: t.summary() for t in self.document.tables}}
        versions = dict(self.run.documents.get(locator, {}).get("versions", {}))
        versions[self.document.sha256] = version
        self.run.documents[locator] = {**version, "versions": versions}

    def propose(self, view):
        if self.document is None:
            try:
                self.prepare()
            except (ProviderError, OSError, ValueError) as exc:
                self.failure = "source_retrieval_failure"
                return self.leaf(lambda error=exc: self.failure_result(error, "retrieval"), "retrieval_failure")
        document = self.document
        tables = {t.key: t for t in document.tables if t.key not in document.attempted_tables}
        options = {key: {"episode": "source_table", **t.summary()} for key, t in tables.items()}
        if document.remaining():
            if not document.report_attempted:
                options["report"] = {"episode": "report", "meaning": "Read remaining text in document order with cross-window context"}
            options["lexical_probe"] = {"episode": "lexical_probe", "meaning": "Rank remaining chunks by a literal source-local query"}
        if not options:
            return None
        proposal = self.run.agent(self.inputs(view, operation="propose_page_child",
            source_summary=document.summary(), available_children=options,
            instruction="Choose among the actual available reading scopes. Use report for information distributed across sections, source_table for a detected table, or lexical_probe for a targeted query. No fixed reading order. You do not decide continuation.",
            response_contract={"type": "object", "additionalProperties": False,
                "required": ["option", "question"], "properties": {
                    "option": {"type": "string", "enum": list(options)},
                    "question": {"type": "string", "minLength": 1, "description": "Child information need"},
                    "child_model_calls": self.child_budget_schema(),
                    "query": {"type": "string", "minLength": 1, "description": "Literal query for lexical_probe"}},
                "allOf": [{"if": {"properties": {"option": {"const": "lexical_probe"}}},
                           "then": {"required": ["query"]}}]}))
        self.last_proposal = proposal
        option = selected_choice(proposal.get("option"), options, "option")
        question = required_text(proposal.get("question"), "question")
        inherited = self.ledger.result()
        if option in tables:
            source = SourceTableSource(self.run, inherited, document=document, table=tables[option])
            grain = "source_table"
        elif option == "report":
            source = ReportSource(self.run, inherited, document=document)
            grain = "report"
        else:
            source = LexicalProbeSource(self.run, inherited, document=document,
                query=required_text(proposal.get("query"), "query"))
            grain = "lexical_probe"
        child = self.run.child(view, source, grain, question, self.focus, proposal=proposal,
            contract=self.contract(f"Establish source-grounded evidence for {question}", self.focus))
        if option in tables:
            document.attempted_tables.add(option)
        elif option == "report":
            document.report_attempted = True
        return self.edge(child)


class ReadingSource(ResearchSource):
    def __init__(self, run, inherited, *, document):
        super().__init__(run, inherited)
        self.document = document
        self.memory = {"summary": "", "unresolved_links": [], "anchors": []}
        self.seen_spans = {}
        self.pending_spans, self.pending_memory = (), None

    def read(self, spans, question):
        allowed = {}
        for anchor in self.memory["anchors"]:
            original = self.seen_spans[anchor["span"]]
            quote = exact_span(anchor["quote"], original.text)
            start = original.start + original.text.index(quote)
            key = f"anchor:{start}:{start + len(quote)}"
            allowed[key] = Span(key, start, start + len(quote), quote)
        allowed.update((s.key, s) for s in spans)
        if spans and all(left.end == right.start for left, right in zip(spans, spans[1:])):
            start, end = spans[0].start, spans[-1].end
            window = Span(f"window:{start}:{end}", start, end, self.document.text[start:end])
            allowed[window.key] = window
        proposed_memory = None
        memory_diagnostics = []

        def agent(request):
            nonlocal proposed_memory
            if request["operation"] == "extract_research_evidence":
                request = {**request, "reading_memory": self.memory,
                    "source_spans": {k: s.as_record() for k, s in allowed.items()},
                    "response_contract": {**request["response_contract"],
                        "properties": {**request["response_contract"]["properties"], "reading_memory": {
                            "type": "object", "additionalProperties": False,
                            "required": ["summary", "unresolved_links", "anchors"], "properties": {
                                "summary": {"type": "string", "description": "Concise working context, not evidence"},
                                "unresolved_links": {"type": "array", "items": {"type": "string"}},
                                "anchors": {"type": "array", "items": {
                                    "type": "object", "additionalProperties": False, "required": ["span", "quote"],
                                    "properties": {"span": {"type": "string", "description": "Available or retained source span key"},
                                                   "quote": {"type": "string", "minLength": 1}}}}}}}},
                    "reading_instruction": "Use retained context to resolve subjects across windows. Evidence must cite an available original span, never memory prose. Keep memory concise; it earns no credit."}
            response = self.run.agent(request)
            if request["operation"] == "extract_research_evidence":
                proposed_memory = response.get("reading_memory", self.memory)
                try:
                    self.validate_memory(proposed_memory, {**self.seen_spans, **allowed})
                except ValueError as exc:
                    memory_diagnostics.append({"stage": "reading_memory", "category": "invalid_memory",
                                               "why": str(exc), "source": self.document.source})
                    proposed_memory = self.memory
            return response

        result = extract_and_admit(agent, text="\n".join(s.text for s in spans),
            source=self.document.source, focus=self.focus, objective=self.goal.as_record()["objective"],
            context=self.context(), question=question, feedback=(*self.ledger.findings, *self.ledger.issues),
            source_spans={k: s.text for k, s in allowed.items()}, source_version=self.document.sha256)
        if memory_diagnostics:
            result = replace(result, diagnostics=(*result.diagnostics, *memory_diagnostics),
                             issues=(*result.issues, *(f"Reading memory not updated: {d['why']}" for d in memory_diagnostics)))
        if result.evaluated:
            self.pending_spans, self.pending_memory = spans, proposed_memory
            self.seen_spans.update(allowed)
        return result

    def validate_memory(self, memory, allowed):
        if not isinstance(memory, dict) or set(memory) != {"summary", "unresolved_links", "anchors"}:
            raise ValueError("Reading memory requires summary, unresolved_links, and source anchors")
        if len(json.dumps(memory)) > self.run.limits.text_window_chars:
            raise ValueError("Reading memory exceeds its declared context capacity")
        if not isinstance(memory["summary"], str) or len(memory["summary"]) > self.run.limits.text_window_chars:
            raise ValueError("Reading summary exceeds its declared context capacity")
        if not isinstance(memory["unresolved_links"], list) or any(not isinstance(v, str) for v in memory["unresolved_links"]):
            raise ValueError("Reading unresolved links must be text")
        if not isinstance(memory["anchors"], list):
            raise ValueError("Reading anchors must be a list")
        for anchor in memory["anchors"]:
            if not isinstance(anchor, dict) or anchor.get("span") not in allowed:
                raise ValueError("Reading anchor must refer to a seen source span")
            exact_span(anchor.get("quote"), allowed[anchor["span"]].text)

    def after_verdict(self, unit, contribution, view):
        if self.pending is not None and self.pending.evaluated:
            self.document.processed.update(s.key for s in self.pending_spans)
            self.seen_spans.update((s.key, s) for s in self.pending_spans)
            if self.pending_memory is not None:
                self.memory = self.pending_memory
        super().after_verdict(unit, contribution, view)
        self.pending_spans, self.pending_memory = (), None


class ReportSource(ReadingSource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spans, self.position = self.document.remaining(), 0

    def propose(self, view):
        if self.position >= len(self.spans):
            return None
        spans, size = [], 0
        while self.position < len(self.spans):
            span = self.spans[self.position]
            if spans and size + len(span.text) > self.run.limits.text_window_chars:
                break
            spans.append(span)
            size += len(span.text)
            self.position += 1
        return self.leaf(lambda: self.read(tuple(spans), str(view.goal.objective)),
                         f"report_window:{view.units_consumed + 1}")


class LexicalProbeSource(ReadingSource):
    def __init__(self, *args, query, **kwargs):
        super().__init__(*args, **kwargs)
        self.query, self.position = query, 0
        # Preserve actual neighbors even where earlier readers consumed a chunk.
        self.ranked = tuple(span for span in rank_spans(self.document.spans, query)
                            if span.key not in self.document.processed)

    def propose(self, view):
        while self.position < len(self.ranked):
            span = self.ranked[self.position]
            self.position += 1
            if span.key not in self.document.processed:
                return self.leaf(lambda: self.read((span,), self.query), f"chunk:{span.start}:{span.end}")
        return None


class SourceTableSource(ReadingSource):
    def __init__(self, *args, table, **kwargs):
        super().__init__(*args, **kwargs)
        self.table, self.queried = table, set()
        self.queries = []

    def propose(self, view):
        remaining = {s.key: (s, values) for s, values in zip(self.table.rows, self.table.cells)
                     if s.key not in self.queried}
        if not remaining:
            return None
        question_schema = {"type": "string", "minLength": 1,
                           "description": "Claim to examine using selected rows and the exact header"}
        response_contract = {"oneOf": [
            {"type": "object", "additionalProperties": False, "required": ["rows", "question"],
             "properties": {
                 "rows": {"type": "array", "minItems": 1, "uniqueItems": True,
                          "items": {"type": "string", "pattern": rf"^{self.table.key}:row:[1-9][0-9]*$"},
                          "description": "Exact unqueried row keys, not row numbers or row contents"},
                 "question": question_schema}},
            {"type": "object", "additionalProperties": False, "required": ["query", "question"],
             "properties": {
                 "query": {"type": "string", "description": "Literal text; empty string scans remaining rows"},
                 "column": {"type": ["string", "null"], "enum": [*self.table.columns, None]},
                 "question": question_schema}},
        ]}
        proposal = self.run.agent(self.inputs(view, operation="propose_table_query",
            table=self.table.summary(),
            available_rows={k: {"cells": list(values), "raw": s.text} for k, (s, values) in list(remaining.items())[:8]},
            remaining_row_count=len(remaining), previous_queries=self.queries,
            row_addressing={"format": f"{self.table.key}:row:NUMBER", "first": 1, "last": len(self.table.rows)},
            response_contract=response_contract,
            instruction="Return an instance of one JSON Schema alternative: rows plus question, OR query plus question and an optional column. Omit rows entirely for a text query; do not send rows: []. The preview is not the whole table: a text query searches all remaining rows and returns one bounded execution window. Subsequent queries can examine the remaining matches. Execution returns exact spans, not inferred cells."))
        self.last_proposal = proposal
        if ("rows" in proposal) == ("query" in proposal):
            raise ValueError("Choose exactly one table selection: 'rows' with nonempty exact row keys OR "
                             "'query' with literal text. Omit 'rows' for a text query. "
                             f"Received fields {list(proposal)!r}; no rows were queried.")
        rows = proposal.get("rows")
        question = required_text(proposal.get("question"), "question")
        if "query" in proposal:
            query, column = proposal.get("query"), proposal.get("column")
            if not isinstance(query, str) or (column is not None and column not in self.table.columns):
                raise ValueError("Table query needs literal text and an existing optional column")
            rows, size, matches = [], len(self.table.header.text), 0
            for key, (span, values) in remaining.items():
                searched = values if column is None else (values[self.table.columns.index(column)],)
                if not any(query.casefold() in cell.casefold() for cell in searched):
                    continue
                matches += 1
                if size + len(span.text) <= self.run.limits.text_window_chars:
                    rows.append(key)
                    size += len(span.text)
            self.queries.append({"query": query, "column": column, "matches": matches, "selected_rows": rows})
            if not rows:
                if matches:
                    raise ValueError("A matching table row exceeds the execution window")
                return self.leaf(lambda: self.no_matches(query), f"table_query:{view.units_consumed + 1}")
        if not isinstance(rows, list) or not rows or any(not isinstance(k, str) or k not in remaining for k in rows):
            invalid = [k for k in rows if not isinstance(k, str) or k not in remaining] if isinstance(rows, list) else rows
            raise ValueError("'rows' must be a nonempty list of exact unqueried row keys, not row numbers. "
                             f"Unavailable or invalid selection: {invalid!r}. "
                             f"Available key preview: {list(remaining)[:8]!r}. No rows were queried.")
        if len(set(rows)) != len(rows):
            raise ValueError("'rows' must contain unique row keys; no rows were queried")
        spans = (self.table.header, *(s for s in self.table.rows if s.key in rows))
        if sum(len(s.text) for s in spans) > self.run.limits.text_window_chars:
            raise ValueError("Table query exceeds one execution window; select fewer rows")
        return self.leaf(lambda: self.read(spans, question), f"table_query:{view.units_consumed + 1}")

    def after_verdict(self, unit, contribution, view):
        if self.pending is not None and self.pending.evaluated:
            self.queried.update(s.key for s in self.pending_spans if s.key != self.table.header.key)
        super().after_verdict(unit, contribution, view)

    @staticmethod
    def no_matches(query):
        return ResearchResult(findings=(f"No remaining table rows match literal query {query!r}; this is not a scientific refutation.",))
