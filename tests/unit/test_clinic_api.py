from __future__ import annotations

from types import SimpleNamespace

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from tests.helpers import clinic_api
from tests.helpers.clinic_api import AudioUploadFailed, wait_for_processed_transcription


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class _Response:
    ok = True

    def json(self) -> dict:
        return {
            "processedChunkCount": 1,
            "realtimeTranscription": "The patient has a headache",
        }


class _Request:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def get(self, *_args, **_kwargs):
        self.calls += 1
        if self.calls <= self.failures:
            raise PlaywrightTimeoutError("API request timed out")
        return _Response()


def _context(request: _Request) -> SimpleNamespace:
    return SimpleNamespace(
        request=request,
        cookies=lambda: [{"name": "auth", "value": "token"}],
    )


def test_processed_transcription_retries_transient_request_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = _Clock()
    request = _Request(failures=1)
    monkeypatch.setattr(clinic_api.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(clinic_api.time, "sleep", clock.sleep)

    transcription = wait_for_processed_transcription(
        _context(request),
        base_url="https://clinic.example",
        consultation_id="123",
        auth_cookie_name="auth",
        expected_any=["headache"],
        timeout_ms=5_000,
    )

    assert transcription == "The patient has a headache"
    assert request.calls == 2


def test_processed_transcription_reports_persistent_request_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = _Clock()
    request = _Request(failures=10)
    monkeypatch.setattr(clinic_api.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(clinic_api.time, "sleep", clock.sleep)

    with pytest.raises(AudioUploadFailed, match=r"requestTimeouts=2") as error:
        wait_for_processed_transcription(
            _context(request),
            base_url="https://clinic.example",
            consultation_id="123",
            auth_cookie_name="auth",
            expected_any=["headache"],
            timeout_ms=2_000,
        )

    assert "API request timed out" in str(error.value)
