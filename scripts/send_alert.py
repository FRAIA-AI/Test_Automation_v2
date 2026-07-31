"""Send stateful SMTP failure and recovery alerts for a monitor."""

from __future__ import annotations

import argparse
import json
import os
import smtplib
import ssl
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Literal


Status = Literal["success", "failure"]
Event = Literal["failure", "reminder", "recovery", "test"]


@dataclass
class AlertState:
    status: Status = "success"
    updated_at: str | None = None
    last_failure_notification_at: str | None = None


@dataclass(frozen=True)
class AlertDecision:
    event: Event | None
    reason: str


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def is_in_alert_window(now: datetime, start_hour: int, end_hour: int) -> bool:
    """Return whether now is inside a UTC hour window; the end is exclusive."""
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
    in_window = is_in_alert_window(now, start_hour_utc, end_hour_utc)

    if status == "failure":
        if not in_window:
            return AlertDecision(None, "failure outside configured notification window")

        last_notification = parse_utc(previous.last_failure_notification_at)
        if last_notification is None:
            return AlertDecision("failure", "first notified failure in this incident")
        if now - last_notification >= timedelta(minutes=cooldown_minutes):
            return AlertDecision("reminder", "failure reminder cooldown elapsed")
        return AlertDecision(None, "failure reminder cooldown has not elapsed")

    if previous.status == "failure" and previous.last_failure_notification_at:
        return AlertDecision("recovery", "monitor recovered after a notified failure")
    return AlertDecision(None, "monitor is healthy and no notified incident is open")


def load_state(path: Path) -> AlertState:
    if not path.is_file():
        return AlertState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        status = raw.get("status", "success")
        if status not in {"success", "failure"}:
            raise ValueError(f"invalid status {status!r}")
        return AlertState(
            status=status,
            updated_at=raw.get("updated_at"),
            last_failure_notification_at=raw.get("last_failure_notification_at"),
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"WARNING: Ignoring invalid alert state at {path}: {exc}")
        return AlertState()


def save_state(path: Path, state: AlertState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2) + "\n", encoding="utf-8")


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required GitHub secret/environment variable: {name}")
    return value


def read_details(path: Path | None, limit: int = 12_000) -> str:
    if path is None or not path.is_file():
        return "No test output file was available. Open the GitHub Actions run for details."
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return "The test output file was empty. Open the GitHub Actions run for details."
    if len(text) > limit:
        return "[Earlier output omitted]\n" + text[-limit:]
    return text


def build_message(monitor: str, event: Event, now: datetime, details: str) -> EmailMessage:
    labels = {
        "failure": ("❌ FAILED", "A new monitor failure was confirmed."),
        "reminder": ("⚠️ STILL FAILING", "The monitor remains unhealthy."),
        "recovery": ("✅ RECOVERED", "The monitor is healthy again."),
        "test": ("✅ EMAIL TEST", "The monitoring email alarm is configured correctly."),
    }
    label, summary = labels[event]
    server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repository = os.getenv("GITHUB_REPOSITORY", "unknown repository")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}" if run_id else "Unavailable"

    message = EmailMessage()
    message["Subject"] = f"{label}: {monitor}"
    message["From"] = required_env("MAIL_SENDER_ADDRESS")
    message["To"] = required_env("MAIL_RECIPIENT_ADDRESS")
    message.set_content(
        "\n".join(
            [
                summary,
                "",
                f"Monitor: {monitor}",
                f"Event: {event}",
                f"Time (UTC): {utc_text(now)}",
                f"Repository: {repository}",
                f"Branch: {os.getenv('GITHUB_REF_NAME', 'unknown')}",
                f"Commit: {os.getenv('GITHUB_SHA', 'unknown')}",
                f"GitHub run and artifacts: {run_url}",
                "",
                "Test output:",
                details,
            ]
        )
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
        raise RuntimeError("MAIL_SERVER_PORT must be a number") from exc

    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30, context=context) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--monitor", required=True)
    parser.add_argument("--status", choices=("success", "failure"))
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--details-file", type=Path)
    parser.add_argument("--cooldown-minutes", type=int, default=60)
    parser.add_argument("--test-email", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = datetime.now(timezone.utc)
    if args.test_email:
        message = build_message(
            args.monitor,
            "test",
            now,
            "This was a manual configuration test. No product failure occurred.",
        )
        send_message(message)
        print(f"Sent test email for {args.monitor}.")
        return 0
    if args.status is None or args.state_file is None:
        raise SystemExit("--status and --state-file are required unless --test-email is used")

    previous = load_state(args.state_file)
    start_hour = int(os.getenv("ALERT_START_HOUR_UTC", "4"))
    end_hour = int(os.getenv("ALERT_END_HOUR_UTC", "17"))
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
        last_failure_notification_at=previous.last_failure_notification_at,
    )
    # Persist the observed status before SMTP. If delivery fails, the next run
    # can restore the incident and retry because no notification time was set.
    save_state(args.state_file, next_state)

    if decision.event:
        details = (
            read_details(args.details_file)
            if decision.event != "recovery"
            else "The latest scheduled or manually triggered monitor run passed."
        )
        message = build_message(args.monitor, decision.event, now, details)
        send_message(message)
        print(f"Sent {decision.event} email for {args.monitor}.")
        if decision.event in {"failure", "reminder"}:
            next_state.last_failure_notification_at = utc_text(now)
        else:
            next_state.last_failure_notification_at = None
    else:
        print(f"No email sent for {args.monitor}: {decision.reason}.")
        if args.status == "success":
            next_state.last_failure_notification_at = None

    save_state(args.state_file, next_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
