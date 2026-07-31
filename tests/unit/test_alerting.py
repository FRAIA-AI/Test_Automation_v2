from datetime import datetime, timedelta, timezone

from scripts.send_alert import AlertState, decide_alert


NOW = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)


def decide(previous: AlertState, status: str, now: datetime = NOW):
    return decide_alert(
        previous,
        status,  # type: ignore[arg-type]
        now,
        cooldown_minutes=60,
        start_hour_utc=4,
        end_hour_utc=17,
    )


def test_first_failure_sends_email() -> None:
    assert decide(AlertState(), "failure").event == "failure"


def test_repeated_failure_inside_cooldown_is_suppressed() -> None:
    previous = AlertState(
        status="failure",
        last_failure_notification_at=(NOW - timedelta(minutes=30)).isoformat(),
    )
    assert decide(previous, "failure").event is None


def test_repeated_failure_after_cooldown_sends_reminder() -> None:
    previous = AlertState(
        status="failure",
        last_failure_notification_at=(NOW - timedelta(minutes=61)).isoformat(),
    )
    assert decide(previous, "failure").event == "reminder"


def test_failure_outside_notification_window_is_suppressed() -> None:
    outside_window = NOW.replace(hour=2)
    assert decide(AlertState(), "failure", outside_window).event is None


def test_unnotified_failure_sends_when_window_opens() -> None:
    previous = AlertState(status="failure", last_failure_notification_at=None)
    assert decide(previous, "failure").event == "failure"


def test_notified_failure_then_success_sends_recovery() -> None:
    previous = AlertState(status="failure", last_failure_notification_at=NOW.isoformat())
    assert decide(previous, "success").event == "recovery"


def test_unnotified_failure_then_success_does_not_send_recovery() -> None:
    previous = AlertState(status="failure", last_failure_notification_at=None)
    assert decide(previous, "success").event is None


def test_stable_success_does_not_send_email() -> None:
    assert decide(AlertState(status="success"), "success").event is None
