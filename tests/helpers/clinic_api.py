"""Authenticated API operations used by the hybrid consultation monitor."""

from __future__ import annotations

import base64
import subprocess
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


def _audio_mime_type(audio_path: Path) -> str:
    """Return the API MIME type for supported consultation audio."""

    mime_types = {
        ".webm": "audio/webm;codecs=opus",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
    }

    try:
        return mime_types[audio_path.suffix.lower()]
    except KeyError as exc:
        raise AudioUploadFailed(
            "Unsupported consultation audio format: "
            f"{audio_path.suffix or '[no extension]'}"
        ) from exc


def _prepare_audio_payload(
    audio_path: Path,
) -> tuple[bytes, str]:
    """Keep JSON uploads below the gateway limit without changing fixtures."""

    audio_bytes = audio_path.read_bytes()
    encoded_size = 4 * ((len(audio_bytes) + 2) // 3)

    if encoded_size <= 8_000_000:
        return audio_bytes, _audio_mime_type(audio_path)

    try:
        conversion = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(audio_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "libopus",
                "-b:a",
                "48k",
                "-f",
                "webm",
                "pipe:1",
            ],
            check=False,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise AudioUploadFailed(
            "Large audio requires FFmpeg for upload compression, "
            "but ffmpeg was not found on PATH."
        ) from exc

    if conversion.returncode != 0 or not conversion.stdout:
        error = conversion.stderr.decode(
            "utf-8",
            errors="replace",
        ).strip()
        raise AudioUploadFailed(
            "FFmpeg could not prepare the consultation audio: "
            f"{error[:1000]}"
        )

    compressed_size = 4 * (
        (len(conversion.stdout) + 2) // 3
    )
    if compressed_size > 8_000_000:
        raise AudioUploadFailed(
            "Compressed audio still exceeds the safe JSON upload size: "
            f"{compressed_size} base64 bytes."
        )

    return conversion.stdout, "audio/webm;codecs=opus"


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
    audio_bytes, mime_type = _prepare_audio_payload(audio_path)
    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
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
            "mimeType": mime_type,
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
