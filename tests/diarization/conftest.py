"""Pytest reporting hooks for the diarization batch tests."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest


RESULTS_DIR = Path("results/diarization")

# Stores results for this pytest run.
DIARIZATION_RESULTS: dict[str, dict] = {}


def _get_case_id(item) -> str:
    """Extract case_id from the parametrized pytest test."""

    if hasattr(item, "callspec"):
        case_id = item.callspec.params.get("case_id")

        if case_id:
            return str(case_id)

    # Fallback for unexpected/non-parametrized tests.
    return item.name


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Capture PASS/FAIL result for each diarization case.

    We primarily use the 'call' phase, but setup failures are
    also captured so they still appear in the final summary.
    """

    outcome = yield
    report = outcome.get_result()

    # Only collect tests from this diarization directory.
    node_path = str(item.fspath).replace("\\", "/")

    if "/tests/diarization/" not in node_path:
        return

    case_id = _get_case_id(item)

    # --------------------------------------------------------
    # SETUP FAILURE
    # --------------------------------------------------------

    if report.when == "setup" and report.failed:

        DIARIZATION_RESULTS[case_id] = {
            "case_id": case_id,
            "status": "FAILED",
            "phase": "setup",
            "duration_seconds": round(
                report.duration,
                2,
            ),
            "error": str(
                report.longrepr
            ),
        }

        return

    # --------------------------------------------------------
    # NORMAL TEST RESULT
    # --------------------------------------------------------

    if report.when != "call":
        return

    if report.passed:
        status = "PASSED"
        error = None

    elif report.failed:
        status = "FAILED"
        error = str(
            report.longrepr
        )

    elif report.skipped:
        status = "SKIPPED"
        error = str(
            report.longrepr
        )

    else:
        status = "UNKNOWN"
        error = None

    DIARIZATION_RESULTS[case_id] = {
        "case_id": case_id,
        "status": status,
        "phase": "call",
        "duration_seconds": round(
            report.duration,
            2,
        ),
        "error": error,
    }


def pytest_terminal_summary(
    terminalreporter,
    exitstatus,
    config,
):
    """
    Print one final batch summary after all diarization
    tests have completed.
    """

    if not DIARIZATION_RESULTS:
        return

    # Sort case_01 -> case_25.
    def case_number(result):
        case_id = result["case_id"]

        try:
            return int(
                case_id.split("_")[1]
            )
        except (ValueError, IndexError):
            return 9999

    results = sorted(
        DIARIZATION_RESULTS.values(),
        key=case_number,
    )

    passed = [
        result
        for result in results
        if result["status"] == "PASSED"
    ]

    failed = [
        result
        for result in results
        if result["status"] == "FAILED"
    ]

    skipped = [
        result
        for result in results
        if result["status"] == "SKIPPED"
    ]

    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    terminalreporter.write_line("")
    terminalreporter.write_line(
        "=" * 80
    )

    terminalreporter.write_line(
        "DIARIZATION BATCH FINAL RESULTS"
    )

    terminalreporter.write_line(
        "=" * 80
    )

    terminalreporter.write_line("")

    for result in results:

        case_id = result[
            "case_id"
        ]

        status = result[
            "status"
        ]

        duration = result[
            "duration_seconds"
        ]

        if status == "PASSED":
            symbol = "PASS"

        elif status == "FAILED":
            symbol = "FAIL"

        elif status == "SKIPPED":
            symbol = "SKIP"

        else:
            symbol = "????"

        terminalreporter.write_line(
            f"{case_id:<10} "
            f"{symbol:<6} "
            f"({duration:.2f}s)"
        )

    # ========================================================
    # TOTALS
    # ========================================================

    terminalreporter.write_line("")
    terminalreporter.write_line(
        "-" * 80
    )

    terminalreporter.write_line(
        f"Total cases:    {len(results)}"
    )

    terminalreporter.write_line(
        f"Passed:         {len(passed)}"
    )

    terminalreporter.write_line(
        f"Failed:         {len(failed)}"
    )

    terminalreporter.write_line(
        f"Skipped:        {len(skipped)}"
    )

    if results:

        pass_rate = (
            len(passed)
            / len(results)
            * 100
        )

    else:
        pass_rate = 0.0

    terminalreporter.write_line(
        f"Pass rate:      {pass_rate:.1f}%"
    )

    # ========================================================
    # FAILED CASES
    # ========================================================

    if failed:

        terminalreporter.write_line("")
        terminalreporter.write_line(
            "FAILED CASES"
        )

        terminalreporter.write_line(
            "-" * 80
        )

        for result in failed:

            terminalreporter.write_line(
                f"  {result['case_id']}"
            )

    else:

        terminalreporter.write_line("")
        terminalreporter.write_line(
            "ALL DIARIZATION CASES PASSED"
        )

    terminalreporter.write_line(
        "=" * 80
    )

    # ========================================================
    # SAVE MACHINE-READABLE SUMMARY
    # ========================================================

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary = {
        "generated_at":
            datetime.now()
            .astimezone()
            .isoformat(),

        "total_cases":
            len(results),

        "passed":
            len(passed),

        "failed":
            len(failed),

        "skipped":
            len(skipped),

        "pass_rate_percent":
            round(
                pass_rate,
                2,
            ),

        "results":
            results,
    }

    summary_file = (
        RESULTS_DIR
        / "batch-summary.json"
    )

    summary_file.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    terminalreporter.write_line("")
    terminalreporter.write_line(
        f"Batch summary saved -> "
        f"{summary_file}"
    )
