"""API polling helpers used only by the diarization benchmark."""

from __future__ import annotations

import time
from dataclasses import dataclass

from playwright.sync_api import BrowserContext

from tests.helpers.clinic_api import AudioUploadFailed, _select_auth_token


@dataclass(slots=True)
class TranscriptionResult:
    """Both transcription fields produced for an uploaded consultation."""

    diarized_transcription: str
    realtime_transcription: str
    processed_chunk_count: int


def wait_for_diarization_result(
    context: BrowserContext,
    *,
    base_url: str,
    consultation_id: str,
    auth_cookie_name: str,
    timeout_ms: int = 90_000,
) -> TranscriptionResult:
    """Wait for processing without applying content expectations.

    Content and attribution are evaluated separately after evidence collection.
    """

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
                "Consultation-state API returned "
                f"HTTP {response.status}: {response.text()[:1000]}"
            )

        state = response.json()

        if isinstance(state, dict):
            last_state = state
            processed = int(state.get("processedChunkCount") or 0)
            diarized = str(
                state.get("realtimeDiarizedTranscription") or ""
            ).strip()
            realtime = str(
                state.get("realtimeTranscription") or ""
            ).strip()

            if processed > 0 and (diarized or realtime):
                return TranscriptionResult(
                    diarized_transcription=diarized,
                    realtime_transcription=realtime,
                    processed_chunk_count=processed,
                )

        time.sleep(1)

    raise AudioUploadFailed(
        "Audio was accepted but no processed transcription appeared within "
        f"{timeout_ms} ms. Last state: processedChunkCount="
        f"{last_state.get('processedChunkCount')!r}, "
        "realtimeTranscription="
        f"{last_state.get('realtimeTranscription')!r}, "
        "realtimeDiarizedTranscription="
        f"{last_state.get('realtimeDiarizedTranscription')!r}."
    )
