"""High-frequency production availability monitor for sign-in and sign-out."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from tests.helpers.config import get_settings, require_smoke_credentials
from tests.helpers.auth import create_authenticated_session
from tests.helpers.models import FailureCategory, MonitorFailure


class LogoutDidNotComplete(MonitorFailure):
    def __init__(self) -> None:
        super().__init__(
            message="Logout did not return the user to the sign-in page.",
            category=FailureCategory.APPLICATION,
            phase="logout",
            code="LOGOUT_NOT_COMPLETED",
        )


@pytest.mark.smoke
def test_user_can_login_and_logout(app_session_factory) -> None:
    """Retry exactly once only when the app explicitly reports login processing failure."""

    settings = get_settings()
    require_smoke_credentials(settings)
    session, _attempts = create_authenticated_session(
        app_session_factory,
        sign_in_url=settings.sign_in_url,
        username=settings.test_username,
        password=settings.test_password,
    )

    dashboard_anchor = session.page.get_by_text(
        re.compile(r"Recent Consultations|Seneste Konsultationer", re.IGNORECASE)
    ).first
    expect(dashboard_anchor).to_be_visible(timeout=20_000)

    logout_button = session.page.get_by_role(
        "button", name=re.compile(r"^Logout$|^Log ud$", re.IGNORECASE)
    )
    expect(logout_button).to_be_visible(timeout=10_000)
    logout_button.click()

    try:
        expect(session.page).to_have_url(re.compile(r".*/signin(?:[/?#].*)?$"), timeout=20_000)
    except AssertionError as error:
        raise LogoutDidNotComplete() from error
