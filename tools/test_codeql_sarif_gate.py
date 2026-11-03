import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.codeql_sarif_gate import (
    SarifError,
    analyze_sarif,
    classify_severity,
    evaluate_gate,
    load_sarif,
    main,
)


def sarif_with_rules(rules, results):
    return {
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "CodeQL", "rules": rules}},
            "results": results,
        }],
    }


class CodeqlSarifGateTests(unittest.TestCase):
    def test_cvss_boundaries_are_classified(self):
        self.assertEqual(classify_severity("9.0"), "critical")
        self.assertEqual(classify_severity(7.0), "high")
        self.assertEqual(classify_severity("4.0"), "medium")
        self.assertEqual(classify_severity(3.9), "low")

    def test_invalid_or_missing_metadata_is_unclassified(self):
        for value in (None, "not-a-score", -1, 10.1, True):
            with self.subTest(value=value):
                self.assertEqual(classify_severity(value), "unclassified")

    def test_results_match_rule_ids_and_count_all_buckets(self):
        report = sarif_with_rules(
            [
                {"id": "r-critical", "properties": {"security-severity": "9.8"}},
                {"id": "r-high", "properties": {"security-severity": "7.5"}},
                {"id": "r-medium", "properties": {"security-severity": "5.0"}},
                {"id": "r-low", "properties": {"security-severity": "2.0"}},
                {"id": "r-unknown", "properties": {}},
            ],
            [{"ruleId": rule_id} for rule_id in (
                "r-critical", "r-high", "r-medium", "r-low", "r-unknown", "missing"
            )],
        )
        self.assertEqual(analyze_sarif(report), {
            "critical": 1,
            "high": 1,
            "medium": 1,
            "low": 1,
            "unclassified": 2,
        })

    def test_rule_index_is_used_when_rule_id_is_absent(self):
        report = sarif_with_rules(
            [{"id": "indexed", "properties": {"security-severity": "8.0"}}],
            [{"ruleIndex": 0}],
        )
        self.assertEqual(analyze_sarif(report)["high"], 1)

    def test_gate_thresholds_and_unclassified_policy(self):
        clean_counts = {"critical": 0, "high": 0, "medium": 0, "low": 3, "unclassified": 0}
        self.assertTrue(evaluate_gate(clean_counts, "fail")[0])
        unknown_counts = {**clean_counts, "unclassified": 1}
        self.assertFalse(evaluate_gate(unknown_counts, "fail")[0])
        self.assertTrue(evaluate_gate(unknown_counts, "pass")[0])
        medium_counts = {**clean_counts, "medium": 1}
        self.assertFalse(evaluate_gate(medium_counts, "pass")[0])

    def test_missing_and_invalid_reports_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "missing.sarif"
            with self.assertRaises(SarifError):
                load_sarif(report_path)

            with self.assertRaises(SarifError):
                load_sarif(Path(temporary_directory))

            report_path.write_text("not JSON", encoding="utf-8")
            with self.assertRaises(SarifError):
                load_sarif(report_path)

            report_path.write_text(json.dumps({"version": "2.0.0", "runs": []}), encoding="utf-8")
            with self.assertRaises(SarifError):
                load_sarif(report_path)

            report_path.write_text(json.dumps({"version": "2.1.0", "runs": []}), encoding="utf-8")
            with self.assertRaises(SarifError):
                load_sarif(report_path)

    def test_sarif_directory_aggregates_all_reports(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_directory = Path(temporary_directory)
            report_directory.joinpath("java.sarif").write_text(json.dumps(sarif_with_rules(
                [{"id": "low", "properties": {"security-severity": "1.0"}}],
                [{"ruleId": "low"}],
            )), encoding="utf-8")
            report_directory.joinpath("extra.sarif").write_text(json.dumps(sarif_with_rules(
                [{"id": "high", "properties": {"security-severity": "7.0"}}],
                [{"ruleId": "high"}],
            )), encoding="utf-8")

            counts = load_sarif(report_directory)
            self.assertEqual(counts["low"], 1)
            self.assertEqual(counts["high"], 1)

    def test_cli_fails_and_writes_summary_for_missing_report(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            summary_path = Path(temporary_directory) / "summary.md"
            with patch.dict(os.environ, {"CODEQL_UNCLASSIFIED_POLICY": "fail"}):
                exit_code = main([
                    str(Path(temporary_directory) / "missing.sarif"),
                    str(summary_path),
                ])

            self.assertEqual(exit_code, 1)
            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("SARIF Report: **MISSING**", summary)
            self.assertIn("Quality Gate: **FAILED**", summary)

    def test_no_findings_passes(self):
        empty_run = {"tool": {"driver": {"name": "CodeQL"}}, "results": []}
        self.assertEqual(analyze_sarif({"version": "2.1.0", "runs": [empty_run]}), {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "unclassified": 0,
        })


if __name__ == "__main__":
    unittest.main()