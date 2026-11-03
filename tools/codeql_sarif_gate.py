#!/usr/bin/env python3
"""Evaluate CodeQL SARIF findings against the repository security policy."""

import json
import math
import os
import sys
from pathlib import Path
from typing import Any


BUCKETS = ("critical", "high", "medium", "low", "unclassified")


class SarifError(ValueError):
    """Raised when the SARIF report is missing or structurally invalid."""


def classify_severity(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return "unclassified"
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "unclassified"
    if not math.isfinite(score) or score < 0 or score > 10:
        return "unclassified"
    if score >= 9:
        return "critical"
    if score >= 7:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def _rule_severity(rule: dict[str, Any]) -> str:
    properties = rule.get("properties")
    if not isinstance(properties, dict):
        return "unclassified"
    return classify_severity(properties.get("security-severity"))


def analyze_sarif(document: Any) -> dict[str, int]:
    if not isinstance(document, dict) or document.get("version") != "2.1.0":
        raise SarifError("SARIF root must declare version 2.1.0")
    runs = document.get("runs")
    if not isinstance(runs, list):
        raise SarifError("SARIF runs must be an array")
    if not runs:
        raise SarifError("SARIF runs must contain at least one run")

    counts = {bucket: 0 for bucket in BUCKETS}
    for run_number, run in enumerate(runs, start=1):
        if not isinstance(run, dict):
            raise SarifError(f"SARIF run {run_number} must be an object")
        tool = run.get("tool")
        driver = tool.get("driver") if isinstance(tool, dict) else None
        if not isinstance(driver, dict):
            raise SarifError(f"SARIF run {run_number} is missing tool.driver")

        rules = driver.get("rules", [])
        results = run.get("results", [])
        if not isinstance(rules, list) or not isinstance(results, list):
            raise SarifError(f"SARIF run {run_number} rules and results must be arrays")

        rules_by_id: dict[str, str] = {}
        for rule_number, rule in enumerate(rules):
            if not isinstance(rule, dict) or not isinstance(rule.get("id"), str):
                raise SarifError(
                    f"SARIF run {run_number} rule {rule_number} is missing a string id"
                )
            rules_by_id[rule["id"]] = _rule_severity(rule)

        for result_number, result in enumerate(results):
            if not isinstance(result, dict):
                raise SarifError(
                    f"SARIF run {run_number} result {result_number} must be an object"
                )
            rule_id = result.get("ruleId")
            if isinstance(rule_id, str) and rule_id in rules_by_id:
                bucket = rules_by_id[rule_id]
            elif not isinstance(rule_id, str):
                rule_index = result.get("ruleIndex")
                if (isinstance(rule_index, int) and not isinstance(rule_index, bool)
                        and 0 <= rule_index < len(rules)):
                    bucket = rules_by_id[rules[rule_index]["id"]]
                else:
                    bucket = "unclassified"
            else:
                bucket = "unclassified"
            counts[bucket] += 1
    return counts


def load_sarif(path: str | Path) -> dict[str, int]:
    report_path = Path(path)
    if report_path.is_dir():
        report_paths = sorted(report_path.rglob("*.sarif"))
    elif report_path.is_file():
        report_paths = [report_path]
    else:
        report_paths = []
    if not report_paths:
        raise SarifError(f"SARIF report is missing: {report_path}")

    combined_counts = {bucket: 0 for bucket in BUCKETS}
    for current_path in report_paths:
        try:
            with current_path.open(encoding="utf-8") as report_file:
                document = json.load(report_file)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise SarifError(
                f"SARIF report {current_path} cannot be read as valid JSON: {error}"
            ) from error
        current_counts = analyze_sarif(document)
        for bucket in BUCKETS:
            combined_counts[bucket] += current_counts[bucket]
    return combined_counts


def evaluate_gate(counts: dict[str, int], unclassified_policy: str) -> tuple[bool, str]:
    if unclassified_policy not in ("fail", "pass"):
        raise ValueError("unclassified policy must be 'fail' or 'pass'")

    blocked = [name for name in ("critical", "high", "medium") if counts[name] > 0]
    if blocked:
        return False, f"{', '.join(name.title() for name in blocked)} security findings detected."
    if counts["unclassified"] and unclassified_policy == "fail":
        return False, "Unclassified findings detected and policy is set to fail."
    if counts["unclassified"]:
        return True, "No Critical, High, or Medium findings; unclassified findings are allowed by policy."
    return True, "No Critical, High, or Medium security findings detected."


def _write_summary(path: str | Path, counts: dict[str, int] | None,
                   gate_passed: bool, reason: str, report_status: str,
                   policy: str) -> None:
    summary_path = Path(path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# CODEQL SECURITY QUALITY GATE",
        "",
        f"SARIF Report: **{report_status}**",
    ]
    if counts is None:
        lines.extend(["", "Findings: not available"])
    else:
        total = sum(counts.values())
        lines.extend([
            "",
            f"Total Findings: **{total}**",
            f"Critical: **{counts['critical']}**",
            f"High: **{counts['high']}**",
            f"Medium: **{counts['medium']}**",
            f"Low: **{counts['low']}**",
            f"Unclassified: **{counts['unclassified']}**",
        ])
    lines.extend([
        "",
        f"Unclassified Policy: **{policy}**",
        f"Quality Gate: **{'PASSED' if gate_passed else 'FAILED'}**",
        f"Reason: {reason}",
        "",
    ])
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 2:
        print("Usage: codeql_sarif_gate.py SARIF_PATH SUMMARY_PATH", file=sys.stderr)
        return 2

    sarif_path, summary_path = arguments
    policy = os.environ.get("CODEQL_UNCLASSIFIED_POLICY", "fail").strip().lower()
    if policy not in ("fail", "pass"):
        reason = "Invalid unclassified policy; expected 'fail' or 'pass'."
        _write_summary(summary_path, None, False, reason, "NOT READ", policy)
        print(reason, file=sys.stderr)
        return 1

    try:
        counts = load_sarif(sarif_path)
    except SarifError as error:
        reason = str(error)
        report_status = "MISSING" if reason.startswith("SARIF report is missing:") else "INVALID"
        _write_summary(summary_path, None, False, reason, report_status, policy)
        print(reason, file=sys.stderr)
        return 1

    gate_passed, reason = evaluate_gate(counts, policy)
    _write_summary(summary_path, counts, gate_passed, reason, "VALID", policy)
    total = sum(counts.values())
    print(f"Total findings: {total}")
    for bucket in BUCKETS:
        print(f"{bucket.title()}: {counts[bucket]}")
    print(f"Quality gate: {'PASSED' if gate_passed else 'FAILED'}")
    print(f"Reason: {reason}")
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())