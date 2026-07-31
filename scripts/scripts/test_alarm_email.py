"""Create safe synthetic evidence for testing the alarm email."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def create_junit_failure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites tests="1" failures="1" errors="0" time="3.4">
  <testsuite name="alarm_email_test" tests="1" failures="1">
    <testcase
      classname="tests.alarm.test_alarm_delivery"
      name="test_synthetic_alarm_email"
      time="3.4"
    >
      <failure
        type="SyntheticAlarmTest"
        message="Synthetic alarm test: screenshot, video and concise error delivery verification."
      >
SyntheticAlarmTest: Synthetic alarm test: screenshot, video and concise error delivery verification.

Call log:
  - This verbose text should not appear in the email.
  - This confirms that the JUnit summarizer removes the full call log.

Aria snapshot:
  - This accessibility snapshot should not appear in the email.
      </failure>
    </testcase>
  </testsuite>
</testsuites>
"""

    path.write_text(xml, encoding="utf-8")


def create_browser_evidence(
    base_url: str,
    evidence_root: Path,
) -> None:
    screenshot_dir = evidence_root / "stage-screenshots"
    failure_dir = evidence_root / "failure-screenshots"
    video_dir = evidence_root / "videos"

    for directory in (
        screenshot_dir,
        failure_dir,
        video_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            viewport={
                "width": 1280,
                "height": 720,
            },
            record_video_dir=str(video_dir),
            record_video_size={
                "width": 1280,
                "height": 720,
            },
        )

        page = context.new_page()

        page.goto(
            f"{base_url.rstrip('/')}/signin",
            wait_until="domcontentloaded",
            timeout=60_000,
        )

        page.screenshot(
            path=str(
                screenshot_dir
                / "01-alarm-test-signin-page.png"
            ),
            full_page=True,
        )

        page.evaluate(
            """
            () => {
                const banner = document.createElement("div");
                banner.id = "synthetic-monitor-alarm-test";
                banner.textContent =
                    "SYNTHETIC ALARM TEST — no production failure occurred";

                Object.assign(banner.style, {
                    position: "fixed",
                    top: "20px",
                    left: "20px",
                    right: "20px",
                    padding: "18px",
                    zIndex: "999999",
                    background: "#fff3cd",
                    color: "#664d03",
                    border: "2px solid #ffca2c",
                    borderRadius: "8px",
                    fontFamily: "Arial, sans-serif",
                    fontSize: "20px",
                    fontWeight: "bold",
                    textAlign: "center"
                });

                document.body.appendChild(banner);
            }
            """
        )

        page.screenshot(
            path=str(
                screenshot_dir
                / "02-alarm-test-banner-visible.png"
            ),
            full_page=True,
        )

        page.wait_for_timeout(5_000)

        page.screenshot(
            path=str(
                failure_dir
                / "synthetic-alarm-test-failure.png"
            ),
            full_page=True,
        )

        context.close()
        browser.close()


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--monitor",
        default="Peoples Clinic Alarm Delivery Test",
    )

    parser.add_argument(
        "--base-url",
        default=os.getenv(
            "BASE_APP_URL",
            "https://clinic.peoplesdoctor.ai",
        ),
    )

    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path("test-results"),
    )

    parser.add_argument(
        "--junit-file",
        type=Path,
        default=Path(
            "results/alarm-test-junit.xml"
        ),
    )

    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path(
            "results/alarm-test-state.json"
        ),
    )

    args = parser.parse_args()

    create_browser_evidence(
        args.base_url,
        args.evidence_root,
    )

    create_junit_failure(
        args.junit_file
    )

    command = [
        sys.executable,
        "scripts/send_alert.py",
        "--monitor",
        args.monitor,
        "--status",
        "failure",
        "--state-file",
        str(args.state_file),
        "--junit-file",
        str(args.junit_file),
        "--evidence-root",
        str(args.evidence_root),
        "--cooldown-minutes",
        "0",
    ]

    completed = subprocess.run(
        command,
        check=False,
    )

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
