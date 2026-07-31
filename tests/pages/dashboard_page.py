"""Dashboard interactions shared by consultation and FNX monitors."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.sync_api import Page, expect


@dataclass(frozen=True, slots=True)
class SyntheticPatient:
    first_name: str
    family_name: str
    cpr: str

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.family_name}"

    @classmethod
    def create(cls) -> "SyntheticPatient":
        now = datetime.now(ZoneInfo("Europe/Budapest"))
        return cls(
            first_name=f"Auto{now:%H%M}",
            family_name=f"Test{now:%Y%m%d}",
            cpr=f"{now:%H%M%S}-{now:%d%m}",
        )


class DashboardPage:
    live_url_pattern = re.compile(r".*/consultation/live/(\d+)(?:[/?#].*)?$")

    def __init__(self, page: Page) -> None:
        self.page = page

    def select_english_if_available(self) -> None:
        english = self.page.get_by_role("button", name=re.compile(r"^English$", re.IGNORECASE))
        if english.count() and english.first.is_visible():
            english.first.click()
            expect(english.first).to_be_visible(timeout=10_000)

    def complete_mic_check_if_required(self) -> None:
        mic_check = self.page.get_by_text(re.compile(r"^MIC CHECK$", re.IGNORECASE))
        if not mic_check.count() or not mic_check.first.is_visible():
            return

        self.page.route(
            "**/api/mic-check/transcribe",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"transcription":"This is a microphone test."}',
            ),
        )
        self.page.route(
            "**/api/mic-check/verify",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"isMatch":true,"confidence":0.99,"feedback":"Synthetic monitor."}',
            ),
        )
        try:
            mic_check.first.click()
            dialog = self.page.get_by_role("dialog")
            expect(dialog).to_be_visible(timeout=15_000)
            test_button = dialog.get_by_role(
                "button", name=re.compile(r"Test Microphone|Test mikrofon", re.IGNORECASE)
            )
            expect(test_button).to_be_enabled(timeout=10_000)
            test_button.click()

            complete_button = dialog.get_by_role(
                "button",
                name=re.compile(
                    r"^(?:Continue|Join|Done|Fortsæt|Deltag|Færdig)$",
                    re.IGNORECASE,
                ),
            )
            expect(complete_button.last).to_be_visible(timeout=60_000)
            complete_button.last.click()
            expect(dialog).to_be_hidden(timeout=15_000)
        finally:
            self.page.unroute("**/api/mic-check/transcribe")
            self.page.unroute("**/api/mic-check/verify")

    def start_direct_consultation(self, patient: SyntheticPatient) -> str:
        cpr_input = self.page.get_by_placeholder(
            re.compile(r"CPR-Number|CPR-nummer|CPR", re.IGNORECASE)
        ).first
        name_input = self.page.get_by_placeholder(
            re.compile(r"Patient Name|Patientnavn|Patientens navn", re.IGNORECASE)
        ).first
        expect(cpr_input).to_be_editable(timeout=15_000)
        cpr_input.click()
        cpr_input.fill("")
        cpr_input.press_sequentially(patient.cpr, delay=35)
        name_input.click()
        name_input.fill("")
        name_input.press_sequentially(patient.full_name, delay=35)
        name_input.press("Tab")
        expect(cpr_input).to_have_value(
            re.compile(rf"^{re.escape(patient.cpr[:6])}"), timeout=5_000
        )
        expect(name_input).to_have_value(
            re.compile(
                rf"^{re.escape(patient.first_name)}\s*{re.escape(patient.family_name)}$"
            ),
            timeout=5_000,
        )

        start_button = self.page.get_by_role(
            "button",
            name=re.compile(r"Start (?:Consultation|Konsultation)", re.IGNORECASE),
        ).last
        expect(start_button).to_be_enabled(timeout=15_000)
        start_button.click()
        expect(self.page).to_have_url(self.live_url_pattern, timeout=45_000)
        match = self.live_url_pattern.match(self.page.url)
        if not match:
            raise AssertionError(f"Live consultation ID is missing from URL: {self.page.url}")
        return match.group(1)

    def expect_recent_consultation(self, patient: SyntheticPatient) -> None:
        expect(self.page).to_have_url(re.compile(r".*/dashboard"), timeout=30_000)
        expect(self.page.get_by_text(patient.cpr[:6]).first).to_be_visible(timeout=20_000)
