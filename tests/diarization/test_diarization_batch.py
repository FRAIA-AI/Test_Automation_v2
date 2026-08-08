"""Local smoke test for multi-speaker diarization consultations.

This test deliberately does NOT evaluate diarization accuracy yet.

Purpose:
1. Run each generated consultation through the working People's Clinic flow.
2. Retrieve realtimeDiarizedTranscription.
3. Verify that the diarized field is populated.
4. Save each result separately for manual inspection.

Expected local dataset structure:

generated_consultations/
    case_01/
        consultation.webm
        oracle.json
    case_02/
        consultation.webm
        oracle.json
    ...
    case_05/
        consultation.webm
        oracle.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.pages.consultation_page import (
    ConsultationPage,
)

from tests.helpers.auth import create_authenticated_session
from tests.helpers.clinic_api import (
    upload_consultation_audio,
    wait_for_processed_transcription,
)
from tests.helpers.config import (
    get_settings,
    require_admin_credentials,
)
from tests.pages.dashboard_page import (
    DashboardPage,
    SyntheticPatient,
)


# ============================================================
# CONFIG
# ============================================================

DEFAULT_CASES_DIR = Path("test_data/diarization")

CASES_DIR = Path(
    os.environ.get(
        "DIARIZATION_CASES_DIR",
        str(DEFAULT_CASES_DIR),
    )
)

RESULTS_DIR = Path(
    "results/diarization"
)

def discover_case_ids(cases_dir: Path) -> list[str]:
    """Return fixture cases in a stable order.

    ``DIARIZATION_CASES_DIR`` can point at a larger private corpus locally,
    while Actions uses the versioned fixtures in ``test_data/diarization``.
    """

    case_ids = sorted(
        (
            path.name
            for path in cases_dir.glob("case_*")
            if path.is_dir()
        ),
        key=lambda case_id: int(case_id.removeprefix("case_")),
    )

    case_limit = os.environ.get("DIARIZATION_CASE_LIMIT")

    if not case_limit:
        return case_ids

    try:
        limit = int(case_limit)
    except ValueError as exc:
        raise ValueError(
            "DIARIZATION_CASE_LIMIT must be a positive integer."
        ) from exc

    if limit < 1:
        raise ValueError(
            "DIARIZATION_CASE_LIMIT must be a positive integer."
        )

    return case_ids[:limit]


CASE_IDS = discover_case_ids(CASES_DIR)


def save_generated_note(
    *,
    case_id: str,
    generated_note: str,
) -> None:

    case_results_dir = (
        RESULTS_DIR
        / case_id
    )

    case_results_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    note_file = (
        case_results_dir
        / "generated-note.txt"
    )

    note_file.write_text(
        generated_note
        or "[EMPTY]",
        encoding="utf-8",
    )

# ============================================================
# LOAD CASE
# ============================================================

def load_case(case_id: str) -> dict:
    case_dir = CASES_DIR / case_id

    audio_file = (
        case_dir
        / "consultation.webm"
    )

    oracle_file = (
        case_dir
        / "oracle.json"
    )

    if not case_dir.exists():
        pytest.fail(
            f"Case directory does not exist: "
            f"{case_dir}"
        )

    if not audio_file.exists():
        pytest.fail(
            f"Audio file does not exist: "
            f"{audio_file}"
        )

    if not oracle_file.exists():
        pytest.fail(
            f"Oracle file does not exist: "
            f"{oracle_file}"
        )

    with oracle_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        oracle = json.load(file)

    return {
        "case_id": case_id,
        "case_dir": case_dir,
        "audio_file": audio_file,
        "oracle_file": oracle_file,
        "oracle": oracle,
    }


# ============================================================
# SAVE RESULT
# ============================================================

def save_transcription_result(
    *,
    case_id: str,
    consultation_id: str,
    oracle: dict,
    diarized_transcription: str,
    realtime_transcription: str,
    processed_chunk_count: int,
) -> None:

    case_results_dir = (
        RESULTS_DIR
        / case_id
    )

    case_results_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # DIARIZED
    # --------------------------------------------------------

    diarized_file = (
        case_results_dir
        / "diarized-transcription.txt"
    )

    diarized_file.write_text(
        diarized_transcription
        or "[EMPTY]",
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # NORMAL REALTIME TRANSCRIPTION
    # --------------------------------------------------------

    realtime_file = (
        case_results_dir
        / "realtime-transcription.txt"
    )

    realtime_file.write_text(
        realtime_transcription
        or "[EMPTY]",
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # ORIGINAL KNOWN DIALOGUE
    # --------------------------------------------------------

    dialogue_lines = []

    for turn in oracle.get(
        "dialogue",
        [],
    ):
        speaker = turn.get(
            "speaker",
            "unknown",
        )

        text = turn.get(
            "text",
            "",
        )

        dialogue_lines.append(
            f"{speaker}: {text}"
        )

    original_dialogue_file = (
        case_results_dir
        / "original-dialogue.txt"
    )

    original_dialogue_file.write_text(
        "\n\n".join(
            dialogue_lines
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # DEBUG / METADATA
    # --------------------------------------------------------

    metadata = {
        "case_id":
            case_id,

        "consultation_id":
            consultation_id,

        "scenario":
            oracle.get(
                "scenario"
            ),

        "expected_speaker_count":
            oracle.get(
                "speaker_count"
            ),

        "expected_speakers":
            list(
                oracle.get(
                    "speakers",
                    {},
                ).keys()
            ),

        "duration_seconds":
            oracle.get(
                "duration_seconds"
            ),

        "processed_chunk_count":
            processed_chunk_count,

        "diarized_transcription_present":
            bool(
                diarized_transcription
            ),

        "realtime_transcription_present":
            bool(
                realtime_transcription
            ),

        "diarized_character_count":
            len(
                diarized_transcription
            ),

        "realtime_character_count":
            len(
                realtime_transcription
            ),
    }

    metadata_file = (
        case_results_dir
        / "metadata.json"
    )

    metadata_file.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ============================================================
# TEST
# ============================================================

@pytest.mark.parametrize(
    "case_id",
    CASE_IDS,
)
def test_collect_diarized_transcription(
    case_id,
    app_session_factory,
):
    """
    Smoke test only.

    PASS means:
    - consultation could be created
    - generated WebM could be uploaded
    - backend processed the audio
    - realtimeDiarizedTranscription was returned

    It does NOT mean diarization is accurate yet.
    """

    settings = get_settings()

    require_admin_credentials(
        settings
    )

    case = load_case(
        case_id
    )

    oracle = case[
        "oracle"
    ]

    audio_file = case[
        "audio_file"
    ]

    # --------------------------------------------------------
    # DISPLAY CASE INFO
    # --------------------------------------------------------

    print()
    print("=" * 80)

    print(
        f"DIARIZATION CASE: "
        f"{case_id}"
    )

    print("=" * 80)

    print(
        f"Scenario: "
        f"{oracle.get('scenario')}"
    )

    print(
        f"Audio: "
        f"{audio_file}"
    )

    print(
        f"Duration: "
        f"{oracle.get('duration_seconds', 'unknown')} sec"
    )

    print(
        f"Expected speakers: "
        f"{oracle.get('speaker_count', 'unknown')}"
    )

    print(
        "Speaker roles: "
        + ", ".join(
            oracle.get(
                "speakers",
                {},
            ).keys()
        )
    )

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    session, _attempts = (
        create_authenticated_session(
            app_session_factory,
            sign_in_url=(
                settings.sign_in_url
            ),
            username=(
                settings.admin_username
            ),
            password=(
                settings.admin_password
            ),
            media_permissions=True,
        )
    )

    dashboard = DashboardPage(
        session.page
    )

    dashboard.select_english_if_available()

    dashboard.complete_mic_check_if_required()

    # --------------------------------------------------------
    # CREATE PATIENT + CONSULTATION
    # --------------------------------------------------------

    patient = SyntheticPatient.create()

    consultation_id = (
        dashboard.start_direct_consultation(
            patient
        )
    )

    print(
        f"Consultation ID: "
        f"{consultation_id}"
    )

    # --------------------------------------------------------
    # SEND GENERATED AUDIO
    # --------------------------------------------------------

    upload_consultation_audio(
        session.context,
        base_url=(
            settings.base_app_url
        ),
        consultation_id=(
            consultation_id
        ),
        audio_path=(
            audio_file
        ),
        auth_cookie_name=(
            settings.auth_cookie_name
        ),
    )

    print(
        "Audio accepted."
    )

    # --------------------------------------------------------
    # WAIT FOR BACKEND TRANSCRIPTION
    # --------------------------------------------------------
    #
    # No expected_any values here.
    #
    # We are NOT evaluating content yet.
    # We simply want the backend result.
    # --------------------------------------------------------

    transcription_result = (
        wait_for_processed_transcription(
            session.context,
            base_url=(
                settings.base_app_url
            ),
            consultation_id=(
                consultation_id
            ),
            auth_cookie_name=(
                settings.auth_cookie_name
            ),
            expected_any=[],
            timeout_ms=180_000,
        )
    )

    diarized = (
        transcription_result
        .diarized_transcription
        .strip()
    )

    realtime = (
        transcription_result
        .realtime_transcription
        .strip()
    )

    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------

    print()
    print("-" * 80)

    print(
        "realtimeDiarizedTranscription"
    )

    print("-" * 80)

    print(
        diarized
        or "[EMPTY]"
    )

    print()
    print("-" * 80)

    print(
        "realtimeTranscription"
    )

    print("-" * 80)

    print(
        realtime
        or "[EMPTY]"
    )

    print()

    print(
        "Processed chunks: "
        f"{transcription_result.processed_chunk_count}"
    )

    # --------------------------------------------------------
    # SAVE RESULT
    # --------------------------------------------------------

    save_transcription_result(
        case_id=(
            case_id
        ),
        consultation_id=(
            str(
                consultation_id
            )
        ),
        oracle=(
            oracle
        ),
        diarized_transcription=(
            diarized
        ),
        realtime_transcription=(
            realtime
        ),
        processed_chunk_count=(
            transcription_result
            .processed_chunk_count
        ),
    )

    # ============================================================
    # GENERATE CLINICAL NOTE
    # ============================================================

    print()
    print(
        "Opening Edit Note page..."
    )

    consultation = ConsultationPage(
        session.page
    )

    consultation.finish_and_open_note()

    print(
        "Waiting for generated clinical note..."
    )

    generated_note = (
        consultation.wait_for_generated_note(
            timeout_ms=180_000,
            minimum_words=10,
        )
    )

    print()
    print("-" * 80)
    print("GENERATED CLINICAL NOTE")
    print("-" * 80)

    print(
        generated_note
        or "[EMPTY]"
    )

    print("-" * 80)

    save_generated_note(
        case_id=case_id,
        generated_note=generated_note,
    )

    print(
        f"Generated note saved -> "
        f"{RESULTS_DIR / case_id / 'generated-note.txt'}"
    )

    assert generated_note, (
        f"{case_id}: generated clinical note "
        "was empty."
    )

    print(
        f"Saved results -> "
        f"{RESULTS_DIR / case_id}"
    )

    # --------------------------------------------------------
    # ONLY ASSERTION FOR THIS STAGE
    # --------------------------------------------------------

    assert diarized, (
        f"{case_id}: audio was processed, "
        "but realtimeDiarizedTranscription "
        "was empty."
    )

    print()
    print(
        f"{case_id}: DIARIZED "
        f"TRANSCRIPTION COLLECTED"
    )

    print("=" * 80)
