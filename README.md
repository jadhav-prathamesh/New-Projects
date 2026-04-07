# DevOps Incident Analyzer

This project is a lightweight, rule-based incident analysis tool for operational logs. It helps teams detect common production issues quickly, summarize what went wrong, and suggest likely next steps without relying on external LLM APIs.

The analyzer currently supports two entry points:

- CLI analysis for direct terminal usage
- A simple web interface for uploading log files and reviewing results in the browser

## Architecture Overview

The project is intentionally small and modular so the analysis logic can be reused across interfaces.

### Core flow

1. Log ingestion
   The analyzer accepts log data from a local file in CLI mode or from an uploaded file in web mode.

2. Line parsing
   Each log line is parsed for a timestamp, severity level, and raw message content.

3. Rule evaluation
   Regex-based detection rules scan each message for known incident signatures such as:
   - disk full conditions
   - timeout patterns
   - out-of-memory failures
   - connection errors
   - authentication and authorization failures

4. Anomaly detection
   The analyzer tracks overall log volume and error-level frequency to flag noisy failure bursts even when a single root cause triggers many downstream errors.

5. Report generation
   Results are converted into a human-readable report containing:
   - issue severity
   - match counts
   - example log lines
   - root-cause suggestions

### File structure

- [log_analyzer.py](/d:/VS/Projects/log_analyzer.py): shared parsing, analysis, CLI formatting, and built-in web server
- [rules.py](/d:/VS/Projects/rules.py): detection rules, thresholds, and severity ordering
- [sample_logs.txt](/d:/VS/Projects/sample_logs.txt): sample input for quick local testing

## Real-World Use Case

Imagine an e-commerce platform during a high-traffic sale window. Customers begin reporting failed checkouts and slow page loads. A DevOps engineer exports service logs from the API gateway, payment service, and background workers, then runs them through this analyzer.

Instead of manually scanning thousands of lines, the tool can quickly highlight that:

- timeout errors are spiking between internal services
- one worker is failing because the disk is full
- an out-of-memory event occurred during a reconciliation job
- authentication failures are affecting a deployment bot or service account

This gives the responder an immediate starting point for triage and helps narrow attention to the most likely root causes before the outage grows worse.

## Before and After

### Before these improvements

- The project logic existed, but the structure and intended flow were not documented.
- New contributors had to inspect the source code to understand how the CLI and web interface related to the shared analyzer.
- The real operational value of the tool was implied, not clearly demonstrated.

### After these improvements

- The architecture is documented clearly, making onboarding faster for collaborators.
- The relationship between ingestion, parsing, rule evaluation, anomaly detection, and reporting is easier to understand.
- A realistic DevOps incident scenario shows why the project matters in practice.
- The project is easier to maintain, present, and extend with future features such as additional rules or optional LLM-assisted suggestions.

## How To Run

### CLI

```powershell
python log_analyzer.py sample_logs.txt
```

### Web interface

```powershell
python log_analyzer.py --web
```

Then open:

```text
http://127.0.0.1:8000
```

## Next Possible Enhancements

- add more log format adapters for vendor-specific systems
- support JSON log parsing more explicitly
- export reports as JSON or markdown
- add optional LLM-based explanation mode on top of the rule-based engine
