"""Deterministic FNX-to-patient-form parser monitor."""

from __future__ import annotations

import pytest

from tests.helpers.auth import (
    create_authenticated_session,
)
from tests.helpers.config import (
    get_settings,
    require_admin_credentials,
    require_files,
)
from tests.helpers.oracle import load_oracle
from tests.pages.dashboard_page import DashboardPage
from tests.pages.fnx_page import FnxPage


@pytest.mark.fnx
@pytest.mark.parser
def test_fnx_upload_populates_known_patient_fields(
    app_session_factory,
    stage_evidence,
) -> None:
    settings = get_settings()

    require_admin_credentials(
        settings
    )

    require_files(
        settings.fnx_file,
        settings.fnx_oracle_file,
    )

    oracle = load_oracle(
        settings.fnx_oracle_file
    )

    session, _attempts = create_authenticated_session(
        app_session_factory,
        sign_in_url=settings.sign_in_url,
        username=settings.admin_username,
        password=settings.admin_password,
    )

    evidence = stage_evidence(
        session.page
    )

    evidence.capture(
        "01-parser-login-completed"
    )

    dashboard = DashboardPage(
        session.page
    )

    dashboard.select_english_if_available()

    evidence.capture(
        "02-parser-language-selection-complete"
    )

    fnx = FnxPage(
        session.page
    )

    evidence.capture(
        "03-before-parser-upload"
    )

    fnx.upload_to_patient_form(
        settings.fnx_file
    )

    evidence.capture(
        "04-parser-file-uploaded"
    )

    fnx.expect_parsed_patient(
        oracle
    )

    evidence.capture(
        "05-parser-patient-fields-validated"
    )
