"""Authenticated API operations used by the hybrid consultation monitor."""

from __future__ import annotations

import base64
import time
from pathlib import Path

from playwright.sync_api import BrowserContext

from tests.helpers.models import FailureCategory, MonitorFailure
from tests.helpers.oracle import assert_contains_any


class AudioUploadFailed(MonitorFailure):
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            category=FailureCategory.APPLICATION,
            phase="audio_upload",
            code="AUDIO_UPLOAD_FAILED",
        )


def _select_auth_token(cookies: list[dict], exact_name: str) -> str:
    if exact_name:
        matches = [cookie for cookie in cookies if cookie["name"] == exact_name]
    else:
        # Peoples Clinic exposes access, refresh, and ID tokens. Only the access
        # token is appropriate for the API Authorization header.
        access_tokens = [
            cookie for cookie in cookies if cookie["name"].casefold() == "pc-accesstoken"
        ]
        matches = access_tokens or [
            cookie
            for cookie in cookies
            if any(key in cookie["name"].casefold() for key in ("token", "auth", "pc-cookie"))
        ]
    if len(matches) != 1:
        names = [cookie["name"] for cookie in matches]
        raise AudioUploadFailed(
            "Expected exactly one authentication cookie. "
            f"Set AUTH_COOKIE_NAME explicitly; candidate names were {names!r}."
        )
    return matches[0]["value"]


def upload_consultation_audio(
    context: BrowserContext,
    *,
    base_url: str,
    consultation_id: str,
    audio_path: Path,
    auth_cookie_name: str,
) -> None:
    cookies = context.cookies()
    token = _select_auth_token(cookies, auth_cookie_name)
    cookie_header = "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in cookies)
    encoded_audio = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    response = context.request.post(
        f"{base_url}/api/live/transcription",
        headers={
            "Authorization": f"Bearer {token}",
            "Cookie": cookie_header,
            "Content-Type": "application/json",
            "Referer": f"{base_url}/consultation/live/{consultation_id}",
        },
        data={
            "consultation_id": consultation_id,
            "transcription": encoded_audio,
            "mimeType": "audio/webm;codecs=opus",
        },
        timeout=60_000,
    )
    if not response.ok:
        raise AudioUploadFailed(
            f"Audio API returned HTTP {response.status}: {response.text()[:1000]}"
        )


def wait_for_processed_transcription(
    context: BrowserContext,
    *,
    base_url: str,
    consultation_id: str,
    auth_cookie_name: str,
    expected_any: list[str],
    timeout_ms: int = 90_000,
) -> str:
    """Poll the consultation state until the backend processed a real audio chunk."""

    token = _select_auth_token(context.cookies(), auth_cookie_name)
    deadline = time.monotonic() + timeout_ms / 1000
    last_state: dict = {}
    while time.monotonic() < deadline:
        response = context.request.get(
            f"{base_url}/api/live?consultation_id={consultation_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30_000,
        )
        if not response.ok:
            raise AudioUploadFailed(
                f"Consultation-state API returned HTTP {response.status}: "
                f"{response.text()[:1000]}"
            )
        state = response.json()
        if isinstance(state, dict):
            last_state = state
            processed = int(state.get("processedChunkCount") or 0)
            transcription = (
                state.get("realtimeDiarizedTranscription")
                or state.get("realtimeTranscription")
                or ""
            )
            if processed > 0 and str(transcription).strip():
                text = str(transcription).strip()
                assert_contains_any(text, expected_any, "Processed transcription")
                return text
        time.sleep(1)

    raise AudioUploadFailed(
        "Audio was accepted but no processed transcription appeared within "
        f"{timeout_ms} ms. Last state: processedChunkCount="
        f"{last_state.get('processedChunkCount')!r}, "
        f"realtimeTranscription={last_state.get('realtimeTranscription')!r}, "
        "realtimeDiarizedTranscription="
        f"{last_state.get('realtimeDiarizedTranscription')!r}."
    )
