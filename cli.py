"""Command-line entry point for configured episodic workflow runs."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from typing import Any, TextIO

from .configured_providers import (
    ProviderConfigurationError,
    run_configured_safety_guideline_request,
)


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run an env-configured disease workflow."""

    out = sys.stdout if stdout is None else stdout
    err = sys.stderr if stderr is None else stderr
    args = None
    try:
        args = _parser().parse_args(argv)
        if args.target_scenario is not None or args.scenarios_file is not None or args.source_url or args.legacy_workflow:
            raise ProviderConfigurationError("Legacy input bypasses and seeded sources are disabled. Use --scenario for caller-defined cases; answers and evidence cannot be supplied.")
        if not args.disease:
            raise ProviderConfigurationError("Supply the disease of interest; no disease is built in")
        request = Path(args.request_file).read_text() if args.request_file else ""
        from .case_reports.research import ResearchLimits
        limits = ResearchLimits(**{name: getattr(args, name) for name in (
            "max_model_calls", "max_total_units", "text_window_chars", "yield_window")})
        with ExitStack() as streams:
            trace_stream = streams.enter_context(Path(args.trace_path).open("x")) if args.trace_path else None

            def trace_event(event):
                print(json.dumps(_json_record(event), allow_nan=False), file=trace_stream, flush=True)

            record, report = run_configured_safety_guideline_request(
                disease=args.disease, research_request=request, scenario=args.scenario,
                transmission_model=args.transmission_model, search_limit=args.search_limit,
                require_transmissibility_evidence=args.require_transmissibility_evidence,
                progress=args.progress, trace_event=trace_event if trace_stream is not None else None,
                metrics=args.metric, limits=limits,
            )
        if args.audit_path:
            Path(args.audit_path).write_text(json.dumps(_json_record(record.as_record()), indent=2, allow_nan=False) + "\n")
        if args.report_path:
            content = _markdown(report) if args.format == "markdown" else json.dumps(_json_record(report.as_record()), indent=args.indent, allow_nan=False)
            with Path(args.report_path).open("x") as stream:
                stream.write(content + "\n")
    except (ProviderConfigurationError, ValueError, OSError) as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "errors": [
                        {
                            "child": "configured_providers",
                            "field": "environment",
                            "code": "configuration_error",
                            "message": str(exc),
                        }
                    ],
                },
                indent=args.indent if args else 2,
                sort_keys=True,
            ),
            file=err,
        )
        return 2

    if args.format == "markdown":
        print(_markdown(report), file=out)
        return 0 if report.passed else 1
    print(
        json.dumps(
            _json_record(report.as_record()),
            indent=args.indent,
            sort_keys=True,
            allow_nan=False,
        ),
        file=out,
    )
    return 0 if report.passed else 1


def _json_record(value: Any) -> Any:
    """Preserve non-finite diagnostics and unbounded results in strict JSON."""

    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "NaN"
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, Mapping):
        return {key: _json_record(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_record(item) for item in value]
    return value


def _markdown(report):
    if hasattr(report, "markdown"):
        return report.markdown()
    data = report.as_record()
    lines = ["# Safety Guideline", "", f"Status: {'conditional result' if report.passed else 'incomplete'}", ""]
    for child, outputs in data.get("main_outputs", {}).items():
        lines.extend([f"## {child}", "", "```json", json.dumps(_json_record(outputs), indent=2, allow_nan=False), "```", ""])
    for name, assumption in data.get("admitted_assumptions", {}).items():
        lines.extend([f"## Assumption: {name}", "", "```json", json.dumps(_json_record(assumption), indent=2, allow_nan=False), "```", ""])
    for error in data.get("errors", []):
        lines.append(f"- {error['child']}: {error['message']}")
    lines.extend(["", "Conditional model calculation, not a guarantee of safety or independent validation."])
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m episodic_workflow",
        description=(
            "Run an env-configured Firecrawl/Jev episodic workflow for a "
            "requested disease or pathogen."
        ),
    )
    parser.add_argument(
        "disease", nargs="?",
        help="Disease of interest; there is no default pathogen.",
    )
    parser.add_argument("--request-file", help="Optional additional natural-language instructions, without supplied scientific answers.")
    parser.add_argument("--scenario", default="bazant-bush",
                        help="Caller-selected cases: bazant-bush (default), classroom, nursing-home, a built-in case name, or a scenario JSON file.")
    parser.add_argument(
        "--search-limit",
        type=int,
        default=10,
        help="Maximum Firecrawl results requested from each scoped query.",
    )
    parser.add_argument("--target-scenario", help=argparse.SUPPRESS)
    parser.add_argument("--scenarios-file", help=argparse.SUPPRESS)
    parser.add_argument("--legacy-workflow", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--transmission-model", help=argparse.SUPPRESS)
    parser.add_argument("--require-transmissibility-evidence", action="store_true", help=argparse.SUPPRESS)
    from .task_executors.scenario_metrics.evaluate import DEFAULT_METRICS
    from .case_reports.research import ResearchLimits
    parser.add_argument("--metric", action="append", choices=DEFAULT_METRICS, help=argparse.SUPPRESS)
    for name in ("max_model_calls", "max_total_units", "text_window_chars", "yield_window"):
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=getattr(ResearchLimits(), name))
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--audit-path", help="Write the complete recursive episode trace, contracts, and numerical verdicts.")
    parser.add_argument("--trace-path", help="Stream model/provider attempts and credit verdicts as JSON Lines to a new file.")
    parser.add_argument("--report-path", help="Also save the report to a new file (never overwrite an existing report).")
    parser.add_argument("--progress", action="store_true", help="Log model operation names to stderr without source content or credentials.")
    parser.add_argument("--source-url", action="append", default=[], help=argparse.SUPPRESS)
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation for the emitted credit report.",
    )
    return parser


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
