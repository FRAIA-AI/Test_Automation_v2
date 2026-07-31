"""FNX summary and multi-turn conversational-memory monitor."""

from __future__ import annotations

import pytest

from tests.helpers.auth import create_authenticated_session
from tests.helpers.config import get_settings, require_admin_credentials, require_files
from tests.helpers.oracle import load_oracle
from tests.pages.dashboard_page import DashboardPage
from tests.pages.fnx_page import FnxPage


@pytest.mark.fnx
@pytest.mark.ai
def test_fnx_ai_summary_and_contextual_follow_up(app_session_factory) -> None:
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
    fnx.open_analytics()
    fnx.upload_to_analytics(settings.fnx_file, str(oracle["patient"]["name"]))
    fnx.generate_summary(oracle)

    for turn in oracle["chat_turns"]:
        fnx.send_prompt(
            str(turn["prompt"]),
            list(turn["expected_any"]),
            list(turn.get("forbidden", [])),
        )
