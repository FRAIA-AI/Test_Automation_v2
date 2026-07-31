"""FNX summary and multi-turn conversational-memory monitor."""

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
@pytest.mark.ai
def test_fnx_ai_summary_and_contextual_follow_up(
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
        "01-ai-login-completed"
    )

    dashboard = DashboardPage(
        session.page
    )

    dashboard.select_english_if_available()

    evidence.capture(
        "02-ai-language-selection-complete"
    )

    fnx = FnxPage(
        session.page
    )

    fnx.open_analytics()

    evidence.capture(
        "03-fnx-analytics-opened"
    )

    fnx.upload_to_analytics(
        settings.fnx_file,
        str(
            oracle["patient"]["name"]
        ),
    )

    evidence.capture(
        "04-fnx-analytics-upload-complete"
    )

    fnx.generate_summary(
        oracle
    )

    evidence.capture(
        "05-fnx-summary-validated"
    )

    chat_turns = list(
        oracle["chat_turns"]
    )

    for index, turn in enumerate(
        chat_turns,
        start=1,
    ):
        prompt = str(
            turn["prompt"]
        )

        expected_any = list(
            turn["expected_any"]
        )

        forbidden = list(
            turn.get(
                "forbidden",
                [],
            )
        )

        evidence.capture(
            f"06-chat-turn-{index}-before-prompt"
        )

        fnx.send_prompt(
            prompt,
            expected_any,
            forbidden,
        )

        evidence.capture(
            f"07-chat-turn-{index}-response-validated"
        )
