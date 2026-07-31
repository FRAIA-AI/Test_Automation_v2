"""Deterministic FNX-to-patient-form parser monitor."""

from __future__ import annotations

import pytest

from tests.helpers.auth import create_authenticated_session
from tests.helpers.config import get_settings, require_admin_credentials, require_files
from tests.helpers.oracle import load_oracle
from tests.pages.dashboard_page import DashboardPage
from tests.pages.fnx_page import FnxPage


@pytest.mark.fnx
@pytest.mark.parser
def test_fnx_upload_populates_known_patient_fields(app_session_factory) -> None:
    settings = get_settings()
    require_admin_credentials(settings)
    require_files(settings.fnx_file, settings.fnx_oracle_file)
    oracle = load_oracle(settings.fnx_oracle_file)

    session, _attempts = create_authenticated_session(
        app_session_factory,
        sign_in_url=settings.sign_in_url,
        username=settings.admin_username,
        password=settings.admin_password,
    )
    DashboardPage(session.page).select_english_if_available()
    fnx = FnxPage(session.page)
    fnx.upload_to_patient_form(settings.fnx_file)
    fnx.expect_parsed_patient(oracle)
