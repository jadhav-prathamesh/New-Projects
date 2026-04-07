import argparse
import html
import json
from collections import Counter
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable, TextIO

from adapters import SUPPORTED_ADAPTERS, ParsedLine, iter_parsed_lines
from rules import (
    DETECTION_RULES,
    ERROR_FREQUENCY_THRESHOLD,
    ERROR_RATIO_THRESHOLD,
    EXAMPLE_LIMIT,
    SEVERITY_ORDER,
)
ERROR_LEVELS = {"ERROR", "CRITICAL", "FATAL"}


@dataclass(slots=True)
class IncidentSummary:
    key: str
    severity: str
    summary: str
    suggestion: str
    count: int = 0
    examples: list[str] = field(default_factory=list)

    def add_example(self, message: str) -> None:
        self.count += 1
        if len(self.examples) < EXAMPLE_LIMIT:
            self.examples.append(message)


@dataclass(slots=True)
class AnalysisReport:
    totals: Counter
    incidents: list[IncidentSummary]
    source_name: str = "uploaded log"
    top_components: list[tuple[str, int]] = field(default_factory=list)
    first_timestamp: str = "N/A"
    last_timestamp: str = "N/A"

    @property
    def lines_processed(self) -> int:
        return self.totals["lines"]

    @property
    def error_ratio(self) -> float:
        if not self.lines_processed:
            return 0.0
        return self.totals["error_lines"] / self.lines_processed
def analyze_lines(
    lines: Iterable[str],
    source_name: str = "input",
    adapter: str = "auto",
) -> AnalysisReport:
    totals: Counter = Counter()
    incidents_by_key: dict[str, IncidentSummary] = {}
    component_counter: Counter = Counter()
    first_timestamp = "N/A"
    last_timestamp = "N/A"
    rules = DETECTION_RULES
    resolved_adapter, parsed_lines = iter_parsed_lines(lines, adapter, source_name)

    for parsed in parsed_lines:
        if not parsed.message:
            continue

        totals["lines"] += 1
        totals[f"level_{parsed.level.lower()}"] += 1
        component_counter[parsed.component] += 1

        if parsed.timestamp != "N/A":
            if first_timestamp == "N/A":
                first_timestamp = parsed.timestamp
            last_timestamp = parsed.timestamp

        if parsed.level in ERROR_LEVELS:
            totals["error_lines"] += 1

        message = parsed.message
        for rule in rules:
            if not rule.pattern.search(message):
                continue

            incident = incidents_by_key.get(rule.name)
            if incident is None:
                incident = incidents_by_key[rule.name] = IncidentSummary(
                    key=rule.name,
                    severity=rule.severity,
                    summary=rule.summary,
                    suggestion=rule.suggestion,
                )
            incident.add_example(message)

    if totals["lines"]:
        error_ratio = totals["error_lines"] / totals["lines"]
        if (
            totals["error_lines"] >= ERROR_FREQUENCY_THRESHOLD
            or error_ratio >= ERROR_RATIO_THRESHOLD
        ):
            incidents_by_key["high_error_frequency"] = IncidentSummary(
                key="high_error_frequency",
                severity="high",
                summary="High concentration of error-level log lines.",
                suggestion=(
                    "Review the first failing component, correlate with deployment or "
                    "infrastructure changes, and check whether one root failure is "
                    "cascading into secondary errors."
                ),
                count=totals["error_lines"],
                examples=["Aggregate detector based on error volume and ratio."],
            )

    incidents = sorted(
        incidents_by_key.values(),
        key=lambda item: (SEVERITY_ORDER.get(item.severity, 99), -item.count, item.key),
    )
    return AnalysisReport(
        totals=totals,
        incidents=incidents,
        source_name=f"{source_name} [{resolved_adapter}]",
        top_components=component_counter.most_common(5),
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
    )


def analyze_stream(
    stream: TextIO,
    source_name: str = "input",
    adapter: str = "auto",
) -> AnalysisReport:
    return analyze_lines(stream, source_name=source_name, adapter=adapter)


def analyze_text(
    text: str,
    source_name: str = "input",
    adapter: str = "auto",
) -> AnalysisReport:
    return analyze_lines(text.splitlines(), source_name=source_name, adapter=adapter)


def analyze_log(path: Path, adapter: str = "auto") -> AnalysisReport:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return analyze_stream(handle, source_name=path.name, adapter=adapter)


def format_cli_report(report: AnalysisReport) -> str:
    lines = [
        f"Incident Analysis Report: {report.source_name}",
        f"Lines processed: {report.lines_processed}",
        f"Time range: {report.first_timestamp} -> {report.last_timestamp}",
        (
            "Log levels: "
            f"ERROR={report.totals['level_error']}, "
            f"CRITICAL={report.totals['level_critical']}, "
            f"FATAL={report.totals['level_fatal']}, "
            f"WARN={report.totals['level_warn']}, "
            f"INFO={report.totals['level_info']}, "
            f"UNKNOWN={report.totals['level_unknown']}"
        ),
        f"Error ratio: {report.error_ratio:.1%}",
        "",
    ]

    if report.top_components:
        lines.append("Top components:")
        for component, count in report.top_components:
            lines.append(f"- {component}: {count} lines")
        lines.append("")

    if not report.incidents:
        lines.append("No known incident patterns were detected.")
        return "\n".join(lines)

    lines.append("Detected issues:")
    for incident in report.incidents:
        lines.append(
            f"- [{incident.severity.upper()}] {incident.summary} (matches: {incident.count})"
        )
        lines.append(f"  Suggestion: {incident.suggestion}")
        lines.append("  Examples:")
        for example in incident.examples:
            lines.append(f"  - {example}")
        lines.append("")

    return "\n".join(lines).rstrip()


def report_to_dict(report: AnalysisReport) -> dict:
    return {
        "source_name": report.source_name,
        "lines_processed": report.lines_processed,
        "first_timestamp": report.first_timestamp,
        "last_timestamp": report.last_timestamp,
        "error_ratio": round(report.error_ratio, 4),
        "log_levels": {
            "error": report.totals["level_error"],
            "critical": report.totals["level_critical"],
            "fatal": report.totals["level_fatal"],
            "warn": report.totals["level_warn"],
            "info": report.totals["level_info"],
            "unknown": report.totals["level_unknown"],
        },
        "top_components": [
            {"name": component, "count": count}
            for component, count in report.top_components
        ],
        "incidents": [
            {
                "key": incident.key,
                "severity": incident.severity,
                "summary": incident.summary,
                "suggestion": incident.suggestion,
                "count": incident.count,
                "examples": incident.examples,
            }
            for incident in report.incidents
        ],
    }


def format_markdown_report(report: AnalysisReport) -> str:
    lines = [
        f"# Incident Analysis Report",
        "",
        f"- Source: `{report.source_name}`",
        f"- Lines processed: `{report.lines_processed}`",
        f"- Time range: `{report.first_timestamp}` to `{report.last_timestamp}`",
        f"- Error ratio: `{report.error_ratio:.1%}`",
        "",
        "## Log Levels",
        "",
        f"- ERROR: `{report.totals['level_error']}`",
        f"- CRITICAL: `{report.totals['level_critical']}`",
        f"- FATAL: `{report.totals['level_fatal']}`",
        f"- WARN: `{report.totals['level_warn']}`",
        f"- INFO: `{report.totals['level_info']}`",
        f"- UNKNOWN: `{report.totals['level_unknown']}`",
        "",
    ]

    if report.top_components:
        lines.extend(["## Top Components", ""])
        for component, count in report.top_components:
            lines.append(f"- `{component}`: {count} lines")
        lines.append("")

    if not report.incidents:
        lines.extend(["## Detected Issues", "", "No known incident patterns were detected."])
        return "\n".join(lines)

    lines.extend(["## Detected Issues", ""])
    for incident in report.incidents:
        lines.append(
            f"### {incident.severity.upper()}: {incident.summary} ({incident.count} matches)"
        )
        lines.append("")
        lines.append(f"Suggestion: {incident.suggestion}")
        lines.append("")
        lines.append("Examples:")
        for example in incident.examples:
            lines.append(f"- `{example}`")
        lines.append("")

    return "\n".join(lines).rstrip()


def render_html_page(report: AnalysisReport | None = None, error_message: str = "") -> str:
    def severity_class(value: str) -> str:
        return {
            "critical": "sev-critical",
            "high": "sev-high",
            "medium": "sev-medium",
            "low": "sev-low",
        }.get(value, "sev-low")

    incidents_html = ""
    summary_html = ""
    if report is not None:
        summary_html = f"""
        <section class="summary-grid">
          <article class="card">
            <h2>Source</h2>
            <p class="metric metric-small">{html.escape(report.source_name)}</p>
          </article>
          <article class="card">
            <h2>Lines Processed</h2>
            <p class="metric">{report.lines_processed}</p>
          </article>
          <article class="card">
            <h2>Error Ratio</h2>
            <p class="metric">{report.error_ratio:.1%}</p>
          </article>
          <article class="card">
            <h2>Error Lines</h2>
            <p class="metric">{report.totals["error_lines"]}</p>
          </article>
          <article class="card">
            <h2>Detected Issues</h2>
            <p class="metric">{len(report.incidents)}</p>
          </article>
        </section>
        <section class="card range-card">
          <h2>Observed Time Range</h2>
          <p>{html.escape(report.first_timestamp)} to {html.escape(report.last_timestamp)}</p>
        </section>
        <section class="card levels">
          <h2>Log Levels</h2>
          <div class="level-row">
            <span>ERROR {report.totals["level_error"]}</span>
            <span>CRITICAL {report.totals["level_critical"]}</span>
            <span>FATAL {report.totals["level_fatal"]}</span>
            <span>WARN {report.totals["level_warn"]}</span>
            <span>INFO {report.totals["level_info"]}</span>
            <span>UNKNOWN {report.totals["level_unknown"]}</span>
          </div>
        </section>
        """

        if report.top_components:
            component_items = "".join(
                f"<li><strong>{html.escape(component)}</strong><span>{count} lines</span></li>"
                for component, count in report.top_components
            )
            summary_html += f"""
            <section class="card components-card">
              <h2>Top Components</h2>
              <ul class="component-list">{component_items}</ul>
            </section>
            """

        if report.incidents:
            cards = []
            for incident in report.incidents:
                examples = "".join(
                    f"<li>{html.escape(example)}</li>" for example in incident.examples
                )
                cards.append(
                    f"""
                    <article class="card incident-card">
                      <div class="incident-head">
                        <span class="severity {severity_class(incident.severity)}">{incident.severity.upper()}</span>
                        <span class="count">{incident.count} matches</span>
                      </div>
                      <h3>{html.escape(incident.summary)}</h3>
                      <p>{html.escape(incident.suggestion)}</p>
                      <ul>{examples}</ul>
                    </article>
                    """
                )
            incidents_html = (
                '<section class="incidents"><h2>Detected Issues</h2>'
                + "".join(cards)
                + "</section>"
            )
        else:
            incidents_html = """
            <section class="card incidents-empty">
              <h2>Detected Issues</h2>
              <p>No known incident patterns were detected in this upload.</p>
            </section>
            """

    error_block = (
        f'<div class="error-banner">{html.escape(error_message)}</div>'
        if error_message
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI-Powered DevOps Incident Analyzer</title>
  <style>
    :root {{
      --bg: #f3efe6;
      --panel: #fffdfa;
      --ink: #1e2430;
      --muted: #5a6472;
      --accent: #0f766e;
      --accent-soft: #d8f1ee;
      --border: #ddd3c1;
      --critical: #a61b1b;
      --high: #c15b12;
      --medium: #a07900;
      --low: #2b6a4a;
      --shadow: 0 14px 35px rgba(34, 37, 44, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(15, 118, 110, 0.18), transparent 28%),
        linear-gradient(180deg, #fcf8f0, var(--bg));
    }}
    .page {{
      width: min(1100px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}
    .hero {{
      display: grid;
      gap: 12px;
      margin-bottom: 24px;
    }}
    h1, h2, h3 {{ margin: 0; }}
    h1 {{
      font-size: clamp(2rem, 4vw, 3.5rem);
      letter-spacing: -0.04em;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      max-width: 720px;
      line-height: 1.6;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 20px;
      box-shadow: var(--shadow);
    }}
    .upload-card {{
      padding: 24px;
      margin-bottom: 24px;
    }}
    .upload-form {{
      display: grid;
      gap: 16px;
    }}
    .upload-label {{
      display: grid;
      gap: 8px;
      color: var(--muted);
      font-weight: 600;
    }}
    input[type="file"] {{
      width: 100%;
      padding: 14px;
      border-radius: 14px;
      border: 1px dashed var(--border);
      background: #fff;
      color: var(--ink);
    }}
    button {{
      width: fit-content;
      padding: 12px 20px;
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }}
    button:hover {{ filter: brightness(1.05); }}
    .error-banner {{
      margin-bottom: 16px;
      padding: 14px 16px;
      border-radius: 14px;
      color: #7f1d1d;
      background: #fee2e2;
      border: 1px solid #fecaca;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }}
    .summary-grid .card,
    .levels,
    .incident-card,
    .incidents-empty {{
      padding: 20px;
    }}
    .metric {{
      margin: 10px 0 0;
      font-size: 2rem;
      font-weight: 700;
    }}
    .metric-small {{
      font-size: 1.1rem;
      line-height: 1.5;
      word-break: break-word;
    }}
    .range-card,
    .levels {{
      margin-bottom: 24px;
    }}
    .range-card p {{
      margin: 12px 0 0;
      color: var(--muted);
    }}
    .components-card {{
      margin-bottom: 24px;
      padding: 20px;
    }}
    .component-list {{
      list-style: none;
      margin: 14px 0 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .component-list li {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      border-radius: 14px;
      background: #f6f8f8;
      color: var(--muted);
    }}
    .level-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
      color: var(--muted);
    }}
    .level-row span {{
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
    }}
    .incidents {{
      display: grid;
      gap: 16px;
    }}
    .incident-card {{
      display: grid;
      gap: 14px;
    }}
    .incident-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    .severity {{
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 800;
      letter-spacing: 0.06em;
    }}
    .sev-critical {{ background: #fee2e2; color: var(--critical); }}
    .sev-high {{ background: #ffedd5; color: var(--high); }}
    .sev-medium {{ background: #fef3c7; color: var(--medium); }}
    .sev-low {{ background: #dcfce7; color: var(--low); }}
    .count {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .incident-card p,
    .incident-card li {{
      color: var(--muted);
      line-height: 1.6;
    }}
    .incident-card ul {{
      margin: 0;
      padding-left: 20px;
    }}
    .footer-note {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    @media (max-width: 640px) {{
      .page {{
        width: min(100% - 20px, 1100px);
        padding-top: 20px;
      }}
      .upload-card,
      .summary-grid .card,
      .levels,
      .incident-card,
      .incidents-empty {{
        padding: 16px;
      }}
      .incident-head {{
        align-items: flex-start;
        flex-direction: column;
      }}
      button {{
        width: 100%;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>DevOps Incident Analyzer</h1>
      <p>Upload an application or infrastructure log file to detect common operational failures, spot noisy error bursts, and get fast rule-based root-cause suggestions.</p>
    </section>
    {error_block}
    <section class="card upload-card">
      <form class="upload-form" method="post" enctype="multipart/form-data">
        <label class="upload-label" for="logfile">
          Choose a log file
          <input id="logfile" name="logfile" type="file" accept=".txt,.log,.out,.json,.jsonl">
        </label>
        <button type="submit">Analyze Log File</button>
      </form>
      <p class="footer-note">CLI still works too: <code>python log_analyzer.py sample_logs.txt</code></p>
    </section>
    {summary_html}
    {incidents_html}
  </main>
</body>
</html>"""


class AnalyzerHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "IncidentAnalyzer/1.0"

    def do_GET(self) -> None:
        self._send_html(render_html_page())

    def do_POST(self) -> None:
        try:
            upload = _parse_uploaded_file(
                self.headers.get("Content-Type", ""),
                self.rfile.read(int(self.headers.get("Content-Length", "0"))),
            )
            if upload is None:
                self._send_html(
                    render_html_page(error_message="Choose a log file before submitting."),
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            file_name, file_lines = upload
            report = analyze_stream(file_lines, source_name=file_name, adapter="auto")
            self._send_html(render_html_page(report=report))
        except Exception as exc:
            self._send_html(
                render_html_page(error_message=f"Failed to analyze file: {exc}"),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _decoded_line_stream(binary_data: bytes) -> Iterable[str]:
    for raw_line in binary_data.splitlines():
        yield raw_line.decode("utf-8", errors="replace")


def _parse_uploaded_file(content_type: str, payload: bytes) -> tuple[str, Iterable[str]] | None:
    if "multipart/form-data" not in content_type or not payload:
        return None

    header_block = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode(
        "utf-8"
    )
    message = BytesParser(policy=policy.default).parsebytes(header_block + payload)

    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        if part.get_param("name", header="content-disposition") != "logfile":
            continue

        filename = part.get_filename() or "uploaded.log"
        file_bytes = part.get_payload(decode=True) or b""
        return filename, _decoded_line_stream(file_bytes)

    return None


def run_web_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), AnalyzerHTTPRequestHandler)
    print(f"Serving incident analyzer at http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze application or infrastructure logs for common incident patterns."
    )
    parser.add_argument("logfile", nargs="?", help="Path to the log file to analyze.")
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="Output format for CLI mode.",
    )
    parser.add_argument(
        "--adapter",
        choices=SUPPORTED_ADAPTERS,
        default="auto",
        help="Select a parser adapter for generic text, JSON logs, or vendor-specific logs.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start a simple web interface for uploading and analyzing logs.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for web mode.")
    parser.add_argument("--port", type=int, default=8000, help="Port for web mode.")
    args = parser.parse_args()

    if args.web:
        run_web_server(args.host, args.port)
        return

    if not args.logfile:
        parser.error("Provide a log file path or run with --web.")

    path = Path(args.logfile)
    if not path.exists() or not path.is_file():
        raise SystemExit(f"Log file not found: {path}")

    report = analyze_log(path, adapter=args.adapter)
    if args.format == "json":
        print(json.dumps(report_to_dict(report), indent=2))
        return
    if args.format == "markdown":
        print(format_markdown_report(report))
        return

    print(format_cli_report(report))


if __name__ == "__main__":
    main()
