# DevOps Incident Analyzer

DevOps Incident Analyzer is a lightweight, rule-based log analysis tool built to help engineers triage incidents faster. It scans raw logs, detects common operational failure patterns, summarizes what matters, and suggests practical next steps without requiring any external LLM or cloud dependency.

It is designed to be simple to run, easy to extend, and useful in both local debugging sessions and lightweight incident-response workflows.

## Why This Project Exists

During an incident, engineers often spend too much time manually scanning noisy logs to understand what is happening. This project reduces that initial triage time by turning unstructured log files into a focused report with:

- detected failure categories
- severity labels
- example log lines
- likely root-cause suggestions
- aggregate signal such as error ratio and affected components

The goal is not to replace observability platforms. It is to provide a fast first-pass incident assistant that works on plain text logs.

## Features

- Rule-based detection for common incident patterns
- Streaming log processing for large files
- CLI mode for terminal-based workflows
- Built-in web interface for file upload and report viewing
- Human-readable output with severity and remediation guidance
- Adapter support for generic text, JSON logs, and Cisco ASA-style logs
- JSON and Markdown output options for scripting or documentation
- Component-level summary to highlight noisy services or processes

## Supported Detection Rules

The analyzer currently identifies:

- disk full and storage exhaustion signals
- timeout and deadline issues
- out-of-memory conditions
- connection and reachability failures
- authentication and authorization failures
- high error concentration based on error volume and ratio

## Project Structure

- [log_analyzer.py](/d:/VS/Projects/log_analyzer.py): parser, analyzer, CLI output, JSON export, and web server
- [adapters.py](/d:/VS/Projects/adapters.py): parser adapters for text, JSON, and vendor-specific formats
- [rules.py](/d:/VS/Projects/rules.py): detection rules, thresholds, and severity ordering
- [sample_logs.txt](/d:/VS/Projects/sample_logs.txt): sample log file for quick testing
- [json_logs_sample.jsonl](/d:/VS/Projects/json_logs_sample.jsonl): sample structured JSON log input
- [cisco_asa_sample.txt](/d:/VS/Projects/cisco_asa_sample.txt): sample Cisco ASA-style log input

## How It Works

The analyzer follows a small, reusable pipeline:

1. Ingest log data from a local file or browser upload.
2. Select an adapter automatically, or use an explicit adapter for text, JSON, or Cisco ASA-style logs.
3. Parse each line for timestamp, severity level, component name, and message body.
4. Match each message against rule-based detection patterns.
5. Track aggregate signals such as total errors, error ratio, time range, and top components.
6. Produce a concise report for CLI, browser, or machine-readable JSON or Markdown output.

Because the analysis is stream-based, large files can be processed without loading the entire file into memory during CLI usage.

## Real-World Use Case

Imagine a payment platform during a weekend traffic spike. Alerts start firing for failed checkouts, increased latency, and worker instability. An engineer exports logs from the API gateway, payment service, worker processes, and authentication layer, then runs them through this analyzer.

The report can quickly reveal that:

- timeout errors are clustered around payment and order service calls
- one worker is hitting a disk full condition
- memory pressure caused an OOM kill in a background reconciliation job
- authentication failures are affecting a service account used by automation

Instead of reading thousands of lines manually, the responder gets a structured summary that points to the most likely starting points for triage.

## Setup

### Requirements

- Python 3.10 or newer

No third-party dependencies are required.

### Clone and Run

```powershell
git clone https://github.com/jadhav-prathamesh/New-Projects.git
cd New-Projects
```

## Usage

### CLI analysis

Analyze the included sample log:

```powershell
python log_analyzer.py sample_logs.txt
```

Analyze any other log file:

```powershell
python log_analyzer.py path\to\your.log
```

Use an explicit adapter when the format is known:

```powershell
python log_analyzer.py cisco_asa_sample.txt --adapter cisco-asa
python log_analyzer.py json_logs_sample.jsonl --adapter json
```

### JSON output

Export the report as JSON:

```powershell
python log_analyzer.py sample_logs.txt --format json
```

This is useful for scripting, testing, or integrating the analyzer into a broader workflow.

### Markdown output

Export the report as Markdown for GitHub issues, incident notes, or internal documentation:

```powershell
python log_analyzer.py sample_logs.txt --format markdown
```

### Web interface

Start the local web UI:

```powershell
python log_analyzer.py --web
```

Then open:

```text
http://127.0.0.1:8000
```

Upload a `.txt`, `.log`, `.out`, or `.json` file and review the rendered report in the browser.

## Example CLI Output

```text
Incident Analysis Report: sample_logs.txt
Lines processed: 12
Time range: 2026-04-07 09:00:01 -> 2026-04-07 09:00:30
Log levels: ERROR=8, CRITICAL=1, FATAL=0, WARN=1, INFO=2, UNKNOWN=0
Error ratio: 75.0%

Top components:
- payments: 4 lines
- api-gateway: 3 lines
- worker: 3 lines

Detected issues:
- [CRITICAL] Disk capacity issue detected. (matches: 2)
- [HIGH] Repeated timeout behavior detected. (matches: 4)
```

## What Makes The Current Version Better

Recent improvements made the tool more practical and easier to work with:

- Analysis logic is shared cleanly across CLI and web modes
- The report now includes top components and observed time range
- Adapter selection makes vendor-specific and structured logs easier to support
- JSON and Markdown output make the tool easier to automate and share
- The web interface presents results in a clearer, more readable layout
- The README now explains purpose, setup, architecture, and usage more thoroughly

## Future Enhancements

Potential next steps for the project:

- richer parsing for nested or array-based structured JSON logs
- additional rules for SSL, DNS, CPU saturation, and restart loops
- saved HTML export for sharing browser reports
- test suite for regression coverage
- optional LLM-based explanations layered on top of the rule engine

## License

No license file is currently included in the repository. Add one before broader distribution if you want to make reuse terms explicit.
