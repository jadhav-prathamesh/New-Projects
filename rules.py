import re
from dataclasses import dataclass
from typing import Pattern


ERROR_FREQUENCY_THRESHOLD = 5
ERROR_RATIO_THRESHOLD = 0.20
EXAMPLE_LIMIT = 3
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass(frozen=True, slots=True)
class DetectionRule:
    name: str
    severity: str
    pattern: Pattern[str]
    summary: str
    suggestion: str


DETECTION_RULES = [
    DetectionRule(
        name="disk_full",
        severity="critical",
        pattern=re.compile(
            r"(no space left on device|disk (is )?full|filesystem full|not enough disk space)",
            re.IGNORECASE,
        ),
        summary="Disk capacity issue detected.",
        suggestion="Free disk space, rotate or archive logs, and verify alerting on filesystem utilization.",
    ),
    DetectionRule(
        name="timeout",
        severity="high",
        pattern=re.compile(
            r"(timed?\s*out|timeout(?:\s+while)?|request exceeded .*deadline|deadline exceeded)",
            re.IGNORECASE,
        ),
        summary="Repeated timeout behavior detected.",
        suggestion="Check downstream latency, recent deploys, and resource saturation. Increase timeouts only after the bottleneck is understood.",
    ),
    DetectionRule(
        name="out_of_memory",
        severity="critical",
        pattern=re.compile(
            r"(out of memory|oom[-\s]?killed|cannot allocate memory|memoryerror)",
            re.IGNORECASE,
        ),
        summary="Memory pressure or OOM condition detected.",
        suggestion="Inspect memory usage, container or VM limits, and recent workload spikes. Consider leak investigation before raising limits.",
    ),
    DetectionRule(
        name="connection_refused",
        severity="high",
        pattern=re.compile(
            r"(connection refused|failed to connect|unable to connect|host unreachable)",
            re.IGNORECASE,
        ),
        summary="Connectivity issue detected.",
        suggestion="Verify service health, DNS and network reachability, and whether the target dependency is listening on the expected port.",
    ),
    DetectionRule(
        name="authentication_failure",
        severity="medium",
        pattern=re.compile(
            r"(authentication failed|access denied|permission denied|unauthorized|forbidden)",
            re.IGNORECASE,
        ),
        summary="Authentication or authorization failure detected.",
        suggestion="Check credentials, token expiry, RBAC or IAM policy changes, and secrets rotation status.",
    ),
]
