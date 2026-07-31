"""Send concise SMTP alerts with screenshots and video attachments."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import smtplib
import ssl
import xml.etree.ElementTree as ET

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Literal


Status = Literal["success", "failure"]
Event = Literal[
    "failure",
    "reminder",
    "recovery",
    "test",
]


@dataclass
class AlertState:
    status: Status = "success"
    updated_at: str | None = None
    last_failure_notification_at: str | None = None


@dataclass(frozen=True)
class AlertDecision:
    event: Event | None
    reason: str


@dataclass(frozen=True)
class FailureSummary:
    test_name: str
    exception_type: str
    phase: str
    message: str


@dataclass
class AttachmentResult:
    attached: list[str]
    omitted: list[str]
    total_bytes: int


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def is_in_alert_window(
    now: datetime,
    start_hour: int,
    end_hour: int,
) -> bool:
    hour = now.astimezone(timezone.utc).hour

    if start_hour == end_hour:
        return True

    if start_hour < end_hour:
        return start_hour <= hour < end_hour

    return hour >= start_hour or hour < end_hour


def decide_alert(
    previous: AlertState,
    status: Status,
    now: datetime,
    *,
    cooldown_minutes: int,
    start_hour_utc: int,
    end_hour_utc: int,
) -> AlertDecision:
    in_window = is_in_alert_window(
        now,
        start_hour_utc,
        end_hour_utc,
    )

    if status == "failure":
        if not in_window:
            return AlertDecision(
                None,
                "failure outside configured notification window",
            )

        last_notification = parse_utc(
            previous.last_failure_notification_at
        )

        if last_notification is None:
            return AlertDecision(
                "failure",
                "first notified failure in this incident",
            )

        if now - last_notification >= timedelta(
            minutes=cooldown_minutes
        ):
            return AlertDecision(
                "reminder",
                "failure reminder cooldown elapsed",
            )

        return AlertDecision(
            None,
            "failure reminder cooldown has not elapsed",
        )

    if (
        previous.status == "failure"
        and previous.last_failure_notification_at
    ):
        return AlertDecision(
            "recovery",
            "monitor recovered after a notified failure",
        )

    return AlertDecision(
        None,
        "monitor is healthy and no notified incident is open",
    )


def load_state(path: Path) -> AlertState:
    if not path.is_file():
        return AlertState()

    try:
        raw = json.loads(
            path.read_text(encoding="utf-8")
        )

        status = raw.get("status", "success")

        if status not in {"success", "failure"}:
            raise ValueError(
                f"invalid status {status!r}"
            )

        return AlertState(
            status=status,
            updated_at=raw.get("updated_at"),
            last_failure_notification_at=raw.get(
                "last_failure_notification_at"
            ),
        )

    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        print(
            f"WARNING: Ignoring invalid alert state "
            f"at {path}: {exc}"
        )
        return AlertState()


def save_state(
    path: Path,
    state: AlertState,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            asdict(state),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            "Missing required GitHub secret/"
            f"environment variable: {name}"
        )

    return value


def infer_phase(
    test_name: str,
    message: str,
) -> str:
    text = f"{test_name} {message}".casefold()

    phase_rules = [
        (
            "authentication",
            ("login", "sign_in", "signin"),
        ),
        (
            "microphone check",
            ("mic", "microphone"),
        ),
        (
            "consultation start",
            (
                "start consultation",
                "live consultation",
            ),
        ),
        (
            "audio upload",
            (
                "audio",
                "transcription api",
            ),
        ),
        (
            "transcription processing",
            ("processed transcription",),
        ),
        (
            "note generation and validation",
            (
                "generated note",
                "loader",
                "note did not",
                "note generation",
            ),
        ),
        (
            "note approval",
            ("approve", "save note"),
        ),
        (
            "feedback",
            ("feedback", "rating"),
        ),
        (
            "dashboard verification",
            (
                "dashboard",
                "recent consultation",
            ),
        ),
    ]

    for phase, terms in phase_rules:
        if any(term in text for term in terms):
            return phase

    return "unknown"


def clean_failure_text(text: str) -> str:
    """
    Extract only the main exception.

    Remove Playwright call logs, accessibility snapshots, pytest source
    excerpts, and repeated stack-trace content.
    """

    text = text.strip()

    for marker in (
        "\nCall log:",
        "\nAria snapshot:",
        "\nCaptured stdout",
        "\nCaptured stderr",
        "\n===========================",
    ):
        if marker in text:
            text = text.split(marker, 1)[0].strip()

    cleaned: list[str] = []

    for line in text.splitlines():
        line = re.sub(
            r"^\s*E\s+",
            "",
            line,
        ).strip()

        if not line:
            continue

        if line.startswith(
            (
                "self = ",
                "oracle = ",
                "page = ",
            )
        ):
            continue

        if line not in cleaned:
            cleaned.append(line)

    result = "\n".join(cleaned[:8])

    return (
        result[:2000]
        or "No concise failure message was available."
    )


def read_junit_summary(
    path: Path | None,
) -> FailureSummary:
    if path is None or not path.is_file():
        return FailureSummary(
            test_name="Unknown test",
            exception_type="WorkflowFailure",
            phase="infrastructure or test setup",
            message=(
                "No JUnit failure report was generated. "
                "Open the GitHub Actions run for details."
            ),
        )

    try:
        root = ET.parse(path).getroot()

    except (OSError, ET.ParseError) as exc:
        return FailureSummary(
            test_name="Unknown test",
            exception_type="JUnitParseError",
            phase="reporting",
            message=f"Could not read JUnit report: {exc}",
        )

    testcase = root.find(".//testcase[failure]")
    failure_tag = "failure"

    if testcase is None:
        testcase = root.find(".//testcase[error]")
        failure_tag = "error"

    if testcase is None:
        return FailureSummary(
            test_name="Unknown test",
            exception_type="WorkflowFailure",
            phase="infrastructure or test setup",
            message=(
                "The workflow failed, but the JUnit report "
                "contains no failed test case."
            ),
        )

    node = testcase.find(failure_tag)

    test_name = ".".join(
        value
        for value in (
            testcase.attrib.get("classname", ""),
            testcase.attrib.get("name", ""),
        )
        if value
    ) or "Unknown test"

    exception_type = "AssertionError"
    raw_message = ""

    if node is not None:
        exception_type = node.attrib.get(
            "type",
            "AssertionError",
        )

        raw_message = (
            node.attrib.get("message")
            or node.text
            or ""
        )

    message = clean_failure_text(raw_message)

    return FailureSummary(
        test_name=test_name,
        exception_type=exception_type,
        phase=infer_phase(
            test_name,
            message,
        ),
        message=message,
    )


def collect_evidence_files(
    evidence_root: Path | None,
) -> list[Path]:
    if evidence_root is None:
        return []

    if not evidence_root.exists():
        return []

    stage_screenshots = sorted(
        (
            evidence_root
            / "stage-screenshots"
        ).glob("*.png")
    )

    failure_screenshots = sorted(
        (
            evidence_root
            / "failure-screenshots"
        ).glob("*.png")
    )

    videos = sorted(
        (
            evidence_root
            / "videos"
        ).glob("*.webm"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    # Attach all stage screenshots, failure screenshots,
    # and the newest video from the failed run.
    return [
        *stage_screenshots,
        *failure_screenshots,
        *videos[:1],
    ]


def add_bytes_attachment(
    message: EmailMessage,
    *,
    content: bytes,
    filename: str,
    content_type: str,
) -> None:
    maintype, subtype = content_type.split("/", 1)

    message.add_attachment(
        content,
        maintype=maintype,
        subtype=subtype,
        filename=filename,
    )


def attach_evidence(
    message: EmailMessage,
    paths: list[Path],
    *,
    max_total_bytes: int,
    initial_bytes: int = 0,
) -> AttachmentResult:
    attached: list[str] = []
    omitted: list[str] = []
    total_bytes = initial_bytes

    for path in paths:
        if not path.is_file():
            continue

        file_size = path.stat().st_size

        if total_bytes + file_size > max_total_bytes:
            omitted.append(
                f"{path.name} "
                f"({file_size / 1024 / 1024:.1f} MB)"
            )
            continue

        content_type, _encoding = mimetypes.guess_type(
            path.name
        )

        if not content_type:
            content_type = "application/octet-stream"

        add_bytes_attachment(
            message,
            content=path.read_bytes(),
            filename=path.name,
            content_type=content_type,
        )

        attached.append(path.name)
        total_bytes += file_size

    return AttachmentResult(
        attached=attached,
        omitted=omitted,
        total_bytes=total_bytes,
    )


def build_message(
    monitor: str,
    event: Event,
    now: datetime,
    failure: FailureSummary | None,
    evidence_root: Path | None,
) -> EmailMessage:
    labels = {
        "failure": (
            "❌ FAILED",
            "A new monitor failure was confirmed.",
        ),
        "reminder": (
            "⚠️ STILL FAILING",
            "The monitor remains unhealthy.",
        ),
        "recovery": (
            "✅ RECOVERED",
            "The monitor is healthy again.",
        ),
        "test": (
            "✅ EMAIL TEST",
            "The monitoring email alarm "
            "is configured correctly.",
        ),
    }

    label, summary = labels[event]

    server_url = os.getenv(
        "GITHUB_SERVER_URL",
        "https://github.com",
    ).rstrip("/")

    repository = os.getenv(
        "GITHUB_REPOSITORY",
        "unknown repository",
    )

    run_id = os.getenv("GITHUB_RUN_ID", "")

    run_url = (
        f"{server_url}/{repository}/actions/runs/{run_id}"
        if run_id
        else "Unavailable"
    )

    lines = [
        summary,
        "",
        f"Monitor: {monitor}",
        f"Event: {event}",
        f"Time (UTC): {utc_text(now)}",
        f"Repository: {repository}",
        f"Branch: {os.getenv('GITHUB_REF_NAME', 'unknown')}",
        f"Commit: {os.getenv('GITHUB_SHA', 'unknown')}",
    ]

    if (
        failure is not None
        and event in {"failure", "reminder"}
    ):
        lines.extend(
            [
                "",
                f"Test: {failure.test_name}",
                f"Phase: {failure.phase}",
                f"Failure type: {failure.exception_type}",
                "",
                "Main issue:",
                failure.message,
            ]
        )

    elif event == "recovery":
        lines.extend(
            [
                "",
                "The latest monitor run completed successfully.",
            ]
        )

    elif event == "test":
        lines.extend(
            [
                "",
                "This was a manual email configuration test.",
            ]
        )

    lines.extend(
        [
            "",
            "GitHub run and complete artifacts:",
            run_url,
        ]
    )

    message = EmailMessage()

    message["Subject"] = f"{label}: {monitor}"
    message["From"] = required_env(
        "MAIL_SENDER_ADDRESS"
    )
    message["To"] = required_env(
        "MAIL_RECIPIENT_ADDRESS"
    )

    message.set_content("\n".join(lines))

    if (
        failure is not None
        and event in {"failure", "reminder"}
    ):
        main_error_text = "\n".join(
            [
                f"Monitor: {monitor}",
                f"Test: {failure.test_name}",
                f"Phase: {failure.phase}",
                f"Failure type: {failure.exception_type}",
                "",
                "Main issue:",
                failure.message,
                "",
                f"GitHub run: {run_url}",
            ]
        )

        error_bytes = main_error_text.encode("utf-8")

        add_bytes_attachment(
            message,
            content=error_bytes,
            filename="main-error.txt",
            content_type="text/plain",
        )

        max_attachment_mb = int(
            os.getenv(
                "MAX_EMAIL_ATTACHMENT_MB",
                "20",
            )
        )

        evidence_files = collect_evidence_files(
            evidence_root
        )

        attachment_result = attach_evidence(
            message,
            evidence_files,
            max_total_bytes=(
                max_attachment_mb
                * 1024
                * 1024
            ),
            initial_bytes=len(error_bytes),
        )

        attachment_information = [
            "",
            "Email attachments:",
        ]

        if attachment_result.attached:
            attachment_information.extend(
                f"- Attached: {name}"
                for name in attachment_result.attached
            )
        else:
            attachment_information.append(
                "- No screenshot or video files were available."
            )

        if attachment_result.omitted:
            attachment_information.extend(
                [
                    "",
                    "Omitted because the email attachment "
                    "limit would be exceeded:",
                    *[
                        f"- {name}"
                        for name in attachment_result.omitted
                    ],
                    "",
                    "The omitted evidence remains available "
                    "through the GitHub run link.",
                ]
            )

        # Update the plain-text body after the attachments were selected.
        message.set_content(
            "\n".join(lines + attachment_information)
        )

    return message


def send_message(message: EmailMessage) -> None:
    host = required_env("MAIL_SERVER_ADDRESS")
    port_text = required_env("MAIL_SERVER_PORT")
    username = required_env("MAIL_USERNAME")
    password = required_env("MAIL_PASSWORD")

    try:
        port = int(port_text)

    except ValueError as exc:
        raise RuntimeError(
            "MAIL_SERVER_PORT must be a number"
        ) from exc

    context = ssl.create_default_context()

    if port == 465:
        with smtplib.SMTP_SSL(
            host,
            port,
            timeout=60,
            context=context,
        ) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)

    else:
        with smtplib.SMTP(
            host,
            port,
            timeout=60,
        ) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--monitor",
        required=True,
    )

    parser.add_argument(
        "--status",
        choices=("success", "failure"),
    )

    parser.add_argument(
        "--state-file",
        type=Path,
    )

    parser.add_argument(
        "--junit-file",
        type=Path,
    )

    parser.add_argument(
        "--evidence-root",
        type=Path,
    )

    parser.add_argument(
        "--cooldown-minutes",
        type=int,
        default=60,
    )

    parser.add_argument(
        "--test-email",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = datetime.now(timezone.utc)

    if args.test_email:
        message = build_message(
            args.monitor,
            "test",
            now,
            None,
            args.evidence_root,
        )

        send_message(message)

        print(
            f"Sent test email for {args.monitor}."
        )
        return 0

    if args.status is None or args.state_file is None:
        raise SystemExit(
            "--status and --state-file are required "
            "unless --test-email is used"
        )

    previous = load_state(args.state_file)

    start_hour = int(
        os.getenv("ALERT_START_HOUR_UTC", "4")
    )

    end_hour = int(
        os.getenv("ALERT_END_HOUR_UTC", "17")
    )

    decision = decide_alert(
        previous,
        args.status,
        now,
        cooldown_minutes=args.cooldown_minutes,
        start_hour_utc=start_hour,
        end_hour_utc=end_hour,
    )

    next_state = AlertState(
        status=args.status,
        updated_at=utc_text(now),
        last_failure_notification_at=(
            previous.last_failure_notification_at
        ),
    )

    save_state(
        args.state_file,
        next_state,
    )

    if decision.event:
        failure = (
            read_junit_summary(args.junit_file)
            if decision.event in {"failure", "reminder"}
            else None
        )

        message = build_message(
            args.monitor,
            decision.event,
            now,
            failure,
            args.evidence_root,
        )

        send_message(message)

        print(
            f"Sent {decision.event} "
            f"email for {args.monitor}."
        )

        if decision.event in {"failure", "reminder"}:
            next_state.last_failure_notification_at = utc_text(
                now
            )
        else:
            next_state.last_failure_notification_at = None

    else:
        print(
            f"No email sent for {args.monitor}: "
            f"{decision.reason}."
        )

        if args.status == "success":
            next_state.last_failure_notification_at = None

    save_state(
        args.state_file,
        next_state,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
