"""Hybrid UI/API monitor for the complete direct-consultation journey."""

from __future__ import annotations

import pytest

from tests.helpers.auth import (
    create_authenticated_session,
)
from tests.helpers.clinic_api import (
    upload_consultation_audio,
    wait_for_processed_transcription,
)
from tests.helpers.config import (
    get_settings,
    require_admin_credentials,
    require_files,
)
from tests.helpers.oracle import (
    load_oracle,
)
from tests.pages.consultation_page import (
    ConsultationPage,
)
from tests.pages.dashboard_page import (
    DashboardPage,
    SyntheticPatient,
)


@pytest.mark.regression
def test_direct_consultation_generates_and_saves_valid_note(
    app_session_factory,
    stage_evidence,
) -> None:
    settings = get_settings()

    require_admin_credentials(
        settings
    )

    require_files(
        settings.audio_file,
        settings.audio_oracle_file,
    )

    oracle = load_oracle(
        settings.audio_oracle_file
    )

    session, _attempts = create_authenticated_session(
        app_session_factory,
        sign_in_url=settings.sign_in_url,
        username=settings.admin_username,
        password=settings.admin_password,
        media_permissions=True,
    )

    evidence = stage_evidence(
        session.page
    )

    dashboard = DashboardPage(
        session.page
    )

    evidence.capture(
        "01-signed-in"
    )

    dashboard.select_english_if_available()

    evidence.capture(
        "02-language-selection-complete"
    )

    dashboard.complete_mic_check_if_required()

    evidence.capture(
        "03-mic-check-complete"
    )

    patient = SyntheticPatient.create()

    consultation_id = (
        dashboard.start_direct_consultation(
            patient
        )
    )

    evidence.capture(
        "04-consultation-started"
    )

    upload_consultation_audio(
        session.context,
        base_url=settings.base_app_url,
        consultation_id=consultation_id,
        audio_path=settings.audio_file,
        auth_cookie_name=(
            settings.auth_cookie_name
        ),
    )

    evidence.capture(
        "05-audio-upload-accepted"
    )

    wait_for_processed_transcription(
        session.context,
        base_url=settings.base_app_url,
        consultation_id=consultation_id,
        auth_cookie_name=(
            settings.auth_cookie_name
        ),
        expected_any=list(
            oracle.get(
                "transcription_expected_any",
                [],
            )
        ),
    )

    evidence.capture(
        "06-transcription-processed"
    )

    consultation = ConsultationPage(
        session.page
    )

    consultation.finish_and_open_note()

    evidence.capture(
        "07-note-page-opened"
    )

    consultation.wait_for_valid_note(
        oracle
    )

    evidence.capture(
        "08-valid-note-generated"
    )

    consultation.approve_note()

    evidence.capture(
        "09-note-approved"
    )

    consultation.submit_feedback(
        rating=10
    )

    evidence.capture(
        "10-feedback-submitted"
    )

    dashboard.expect_recent_consultation(
        patient
    )

    evidence.capture(
        "11-dashboard-verified"
    )
