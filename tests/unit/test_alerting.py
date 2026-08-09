from datetime import datetime, timedelta, timezone

from scripts.send_alert import AlertState, decide_alert, is_in_alert_window


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


def test_zero_cooldown_sends_every_failed_run() -> None:
    previous = AlertState(
        status="failure",
        last_failure_notification_at=NOW.isoformat(),
    )
    decision = decide_alert(
        previous,
        "failure",
        NOW,
        cooldown_minutes=0,
        start_hour_utc=0,
        end_hour_utc=0,
    )
    assert decision.event == "reminder"


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


def test_central_europe_window_uses_summer_time() -> None:
    summer_open = datetime(2026, 8, 9, 4, 0, tzinfo=timezone.utc)
    summer_close = datetime(2026, 8, 9, 16, 0, tzinfo=timezone.utc)
    assert is_in_alert_window(summer_open, 6, 18, "Europe/Berlin")
    assert not is_in_alert_window(summer_close, 6, 18, "Europe/Berlin")


def test_central_europe_window_uses_winter_time() -> None:
    winter_open = datetime(2026, 1, 9, 5, 0, tzinfo=timezone.utc)
    assert is_in_alert_window(winter_open, 6, 18, "Europe/Berlin")
