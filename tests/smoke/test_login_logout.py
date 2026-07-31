"""High-frequency production availability monitor for sign-in and sign-out."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from tests.helpers.auth import create_authenticated_session
from tests.helpers.config import (
    get_settings,
    require_smoke_credentials,
)
from tests.helpers.models import (
    FailureCategory,
    MonitorFailure,
)


class LogoutDidNotComplete(MonitorFailure):
    def __init__(self) -> None:
        super().__init__(
            message=(
                "Logout did not return the user "
                "to the sign-in page."
            ),
            category=FailureCategory.APPLICATION,
            phase="logout",
            code="LOGOUT_NOT_COMPLETED",
        )


@pytest.mark.smoke
def test_user_can_login_and_logout(
    app_session_factory,
    stage_evidence,
) -> None:
    """
    Verify production authentication and logout.

    Authentication retries exactly once only when the application explicitly
    reports LOGIN_PROCESSING_FAILED.
    """

    settings = get_settings()

    require_smoke_credentials(
        settings
    )

    session, _attempts = create_authenticated_session(
        app_session_factory,
        sign_in_url=settings.sign_in_url,
        username=settings.test_username,
        password=settings.test_password,
    )

    evidence = stage_evidence(
        session.page
    )

    evidence.capture(
        "01-login-completed"
    )

    dashboard_anchor = session.page.get_by_text(
        re.compile(
            r"Recent Consultations|"
            r"Seneste Konsultationer",
            re.IGNORECASE,
        )
    ).first

    expect(
        dashboard_anchor
    ).to_be_visible(
        timeout=20_000
    )

    evidence.capture(
        "02-dashboard-confirmed"
    )

    logout_button = session.page.get_by_role(
        "button",
        name=re.compile(
            r"^Logout$|^Log ud$",
            re.IGNORECASE,
        ),
    ).first

    expect(
        logout_button
    ).to_be_visible(
        timeout=10_000
    )

    evidence.capture(
        "03-before-logout"
    )

    logout_button.click()

    try:
        expect(
            session.page
        ).to_have_url(
            re.compile(
                r".*/signin(?:[/?#].*)?$"
            ),
            timeout=20_000,
        )

    except AssertionError as error:
        evidence.capture(
            "FAILED-logout-did-not-complete"
        )

        raise LogoutDidNotComplete() from error

    sign_in_button = session.page.get_by_role(
        "button",
        name=re.compile(
            r"^(?:Sign in|Log ind)"
            r"(?: med e-mail)?$",
            re.IGNORECASE,
        ),
    ).first

    expect(
        sign_in_button
    ).to_be_visible(
        timeout=10_000
    )

    evidence.capture(
        "04-logout-completed"
    )
