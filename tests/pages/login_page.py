"""Bilingual page object for the Peoples Clinic sign-in screen."""

from __future__ import annotations

import re
import time

from playwright.sync_api import Locator, Page, expect

from tests.helpers.models import FailureCategory, MonitorFailure


class LoginProcessingFailed(MonitorFailure):
    def __init__(self) -> None:
        super().__init__(
            message="The application returned LOGIN_PROCESSING_FAILED during sign-in.",
            category=FailureCategory.TRANSIENT,
            phase="authentication",
            code="LOGIN_PROCESSING_FAILED",
        )


class LoginDidNotComplete(MonitorFailure):
    def __init__(self) -> None:
        super().__init__(
            message="Sign-in did not reach the dashboard or return a recognised error.",
            category=FailureCategory.APPLICATION,
            phase="authentication",
            code="LOGIN_NOT_COMPLETED",
        )


class LoginPage:
    """Centralises the temporary bilingual selectors until test IDs are available."""

    dashboard_url_pattern = re.compile(r".*/dashboard(?:[/?#].*)?$")
    sign_in_button_name = re.compile(r"^(?:sign in|log ind)(?: med e-mail)?$", re.IGNORECASE)
    email_name = re.compile(r"e-?mail", re.IGNORECASE)
    password_name = re.compile(r"password|adgangskode", re.IGNORECASE)
    login_error = re.compile(r"LOGIN_PROCESSING_FAILED", re.IGNORECASE)

    def __init__(self, page: Page, sign_in_url: str) -> None:
        self.page = page
        self.sign_in_url = sign_in_url

    @property
    def email_input(self) -> Locator:
        return self.page.get_by_role("textbox", name=self.email_name)

    @property
    def password_input(self) -> Locator:
        return self.page.get_by_role("textbox", name=self.password_name)

    @property
    def sign_in_button(self) -> Locator:
        return self.page.get_by_role("button", name=self.sign_in_button_name)

    @property
    def processing_error(self) -> Locator:
        return self.page.get_by_text(self.login_error)

    def open(self) -> None:
        self.page.goto(self.sign_in_url, wait_until="domcontentloaded", timeout=60_000)
        expect(self.sign_in_button).to_be_visible(timeout=20_000)

    def sign_in(self, username: str, password: str) -> None:
        expect(self.email_input).to_be_editable(timeout=10_000)
        self.email_input.fill(username)
        self.password_input.fill(password)
        expect(self.sign_in_button).to_be_enabled(timeout=10_000)
        self.sign_in_button.click()

    def wait_for_outcome(self, timeout_ms: int = 30_000) -> None:
        """Wait for either dashboard navigation or the explicit application error."""

        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            if self.dashboard_url_pattern.match(self.page.url):
                return
            if self.processing_error.is_visible():
                raise LoginProcessingFailed()
            self.page.wait_for_timeout(250)
        raise LoginDidNotComplete()
