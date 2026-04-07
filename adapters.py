import json
import re
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Iterable


TIMESTAMP_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:,\d{3})?)"
)
LEVEL_RE = re.compile(
    r"\b(INFO|WARN|WARNING|ERROR|CRITICAL|DEBUG|FATAL)\b",
    re.IGNORECASE,
)
COMPONENT_RE = re.compile(
    r"^\s*(?:\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:,\d{3})?\s+)?"
    r"(?:INFO|WARN|WARNING|ERROR|CRITICAL|DEBUG|FATAL)\s+"
    r"(?P<component>[\w./:-]+)",
    re.IGNORECASE,
)
ASA_RE = re.compile(
    r"^(?P<prefix>(?:[A-Z][a-z]{2}\s+\d{1,2}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+)?)"
    r"(?:(?P<host>[\w.-]+)\s+)?%ASA-(?P<severity>\d)-(?P<code>\d+):\s*(?P<message>.+)$"
)
MONTH_TIMESTAMP_RE = re.compile(
    r"(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{4}\s+\d{2}:\d{2}:\d{2})"
)

JSON_TIMESTAMP_KEYS = ("timestamp", "time", "@timestamp", "ts")
JSON_LEVEL_KEYS = ("level", "severity", "log_level", "lvl")
JSON_COMPONENT_KEYS = ("component", "service", "logger", "app", "source")
JSON_MESSAGE_KEYS = ("message", "msg", "event", "error")
SUPPORTED_ADAPTERS = ("auto", "text", "json", "cisco-asa")


@dataclass(slots=True)
class ParsedLine:
    timestamp: str
    level: str
    component: str
    message: str


def normalize_level(value: str | None) -> str:
    if not value:
        return "UNKNOWN"

    normalized = value.strip().upper()
    alias_map = {
        "WARNING": "WARN",
        "ERR": "ERROR",
        "SEVERE": "CRITICAL",
        "NOTICE": "INFO",
    }
    return alias_map.get(normalized, normalized)


def parse_text_line(line: str) -> ParsedLine:
    timestamp_match = TIMESTAMP_RE.search(line)
    level_match = LEVEL_RE.search(line)
    component_match = COMPONENT_RE.search(line)

    return ParsedLine(
        timestamp=timestamp_match.group("timestamp") if timestamp_match else "N/A",
        level=normalize_level(level_match.group(1) if level_match else None),
        component=component_match.group("component") if component_match else "unknown",
        message=line.rstrip("\r\n"),
    )


def _extract_json_value(payload: dict, keys: tuple[str, ...], default: str) -> str:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return str(payload[key])
    return default


def parse_json_line(line: str) -> ParsedLine:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return parse_text_line(line)

    if not isinstance(payload, dict):
        return parse_text_line(line)

    timestamp = _extract_json_value(payload, JSON_TIMESTAMP_KEYS, "N/A")
    level = normalize_level(_extract_json_value(payload, JSON_LEVEL_KEYS, "UNKNOWN"))
    component = _extract_json_value(payload, JSON_COMPONENT_KEYS, "unknown")
    message = _extract_json_value(payload, JSON_MESSAGE_KEYS, line.rstrip("\r\n"))

    return ParsedLine(
        timestamp=timestamp,
        level=level,
        component=component,
        message=message,
    )


def parse_cisco_asa_line(line: str) -> ParsedLine:
    match = ASA_RE.match(line.rstrip("\r\n"))
    if not match:
        return parse_text_line(line)

    severity_digit = int(match.group("severity"))
    timestamp_match = MONTH_TIMESTAMP_RE.search(match.group("prefix") or "")
    severity_map = {
        0: "CRITICAL",
        1: "CRITICAL",
        2: "CRITICAL",
        3: "ERROR",
        4: "WARN",
        5: "INFO",
        6: "INFO",
        7: "DEBUG",
    }

    return ParsedLine(
        timestamp=timestamp_match.group("timestamp") if timestamp_match else "N/A",
        level=severity_map.get(severity_digit, "UNKNOWN"),
        component=match.group("host") or "asa",
        message=match.group("message"),
    )


def resolve_adapter(adapter: str, first_line: str, source_name: str) -> str:
    requested = adapter.lower()
    if requested != "auto":
        return requested

    suffix = Path(source_name).suffix.lower()
    stripped = first_line.lstrip()
    if suffix == ".json" or stripped.startswith("{"):
        return "json"
    if "%ASA-" in first_line or "asa" in source_name.lower():
        return "cisco-asa"
    return "text"


def parse_with_adapter(line: str, adapter: str) -> ParsedLine:
    if adapter == "json":
        return parse_json_line(line)
    if adapter == "cisco-asa":
        return parse_cisco_asa_line(line)
    return parse_text_line(line)


def iter_parsed_lines(
    lines: Iterable[str],
    adapter: str,
    source_name: str,
) -> tuple[str, Iterable[ParsedLine]]:
    iterator = iter(lines)
    first_line = next(iterator, "")
    resolved = resolve_adapter(adapter, first_line, source_name)
    combined = chain([first_line], iterator) if first_line else iterator
    return resolved, (parse_with_adapter(line, resolved) for line in combined)
