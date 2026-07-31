"""Reusable authenticated-session creation with one narrowly controlled retry."""

from __future__ import annotations

from typing import Callable

from tests.conftest import AppSession
from tests.pages.login_page import LoginPage, LoginProcessingFailed


def create_authenticated_session(
    session_factory: Callable[..., AppSession],
    *,
    sign_in_url: str,
    username: str,
    password: str,
    media_permissions: bool = False,
) -> tuple[AppSession, int]:
    """Return an authenticated fresh session and the number of attempts used."""

    last_error: LoginProcessingFailed | None = None
    for attempt in range(1, 3):
        session = session_factory(media_permissions=media_permissions)
        login = LoginPage(session.page, sign_in_url)
        login.open()
        login.sign_in(username, password)
        try:
            login.wait_for_outcome()
        except LoginProcessingFailed as error:
            last_error = error
            if attempt == 1:
                continue
            raise
        return session, attempt
    raise last_error or AssertionError("Login attempts unexpectedly exhausted.")
