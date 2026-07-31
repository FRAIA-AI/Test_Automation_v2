"""FNX parser and analytics interactions with direct file-input uploads."""

from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import Locator, Page, expect

from tests.helpers.oracle import assert_contains_any, assert_contains_none


class FnxPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def upload_to_patient_form(self, file_path: Path) -> None:
        upload_zone = self.page.get_by_text(
            re.compile(r"Drag\s*&\s*drop|Upload journalfil", re.IGNORECASE)
        ).first
        expect(upload_zone).to_be_visible(timeout=15_000)
        upload_zone.click()

        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=10_000)
        file_input = dialog.locator('input[type="file"]')
        expect(file_input).to_have_count(1)
        file_input.set_input_files(str(file_path))

        confirm = dialog.get_by_role(
            "button",
            name=re.compile(r"^Upload Files$|^Upload filer$|^Upload$|^Send$", re.IGNORECASE),
        ).last
        expect(confirm).to_be_enabled(timeout=15_000)
        confirm.click()
        expect(dialog).to_be_hidden(timeout=20_000)

    def expect_parsed_patient(self, oracle: dict) -> None:
        cpr = self.page.get_by_placeholder(re.compile(r"CPR", re.IGNORECASE)).first
        name = self.page.get_by_placeholder(
            re.compile(r"Patient Name|Patientnavn|Patientens navn", re.IGNORECASE)
        ).first
        expect(cpr).to_have_value(
            re.compile(re.escape(str(oracle["patient"]["cpr_prefix"]))), timeout=15_000
        )
        expected_name = str(oracle["patient"]["name"])
        expect(name).to_have_value(
            re.compile(re.escape(expected_name), re.IGNORECASE), timeout=15_000
        )

    def open_analytics(self) -> None:
        analytics = self.page.get_by_text(
            re.compile(r"FNX Analytics|Journal Resume|Journalresumé", re.IGNORECASE)
        ).first
        expect(analytics).to_be_visible(timeout=15_000)
        analytics.click()
        expect(
            self.page.get_by_text(
                re.compile(r"Upload file|Upload fil|Vælg fil|Gennemse", re.IGNORECASE)
            ).first
        ).to_be_visible(timeout=30_000)

    def upload_to_analytics(self, file_path: Path, patient_name: str) -> None:
        file_inputs = self.page.locator('input[type="file"]')
        if file_inputs.count():
            file_inputs.last.set_input_files(str(file_path))
        else:
            upload = self.page.get_by_text(
                re.compile(r"Upload file|Upload fil|Vælg fil|Gennemse", re.IGNORECASE)
            ).first
            with self.page.expect_file_chooser(timeout=10_000) as chooser_info:
                upload.click()
            chooser_info.value.set_files(str(file_path))
        expect(self.page.get_by_text(patient_name, exact=False).first).to_be_visible(timeout=30_000)
        uploading = self.page.get_by_text(
            re.compile(r"^UPLOADING$|^UPLOADER$", re.IGNORECASE)
        )
        if uploading.count():
            expect(uploading).to_be_hidden(timeout=90_000)
        expect(
            self.page.get_by_text(
                re.compile(r"^UPLOADED$|^UPLOADET$", re.IGNORECASE)
            ).last
        ).to_be_visible(timeout=90_000)

    def generate_summary(self, oracle: dict) -> str:
        summary = self.page.get_by_role(
            "button",
            name=re.compile(
                r"Journal Summary|Patient Summary|Journal Resume|Journalresumé",
                re.IGNORECASE,
            ),
        ).last
        expect(summary).to_be_visible(timeout=20_000)
        expect(summary).to_be_enabled(timeout=120_000)
        summary.click()
        return self._wait_for_expected_content(
            list(oracle["summary"]["expected_any"]),
            list(oracle["summary"].get("forbidden", [])),
            label="FNX summary",
            timeout_ms=90_000,
        )

    def send_prompt(self, prompt: str, expected_any: list[str], forbidden: list[str]) -> str:
        chat_input = self.page.get_by_placeholder(
            re.compile(r"Describe what you need|Beskriv hvad du", re.IGNORECASE)
        ).first
        expect(chat_input).to_be_editable(timeout=45_000)
        before = self.page.locator("body").inner_text()
        chat_input.fill(prompt)
        chat_input.press("Enter")
        expect(self.page.get_by_text(prompt, exact=True).last).to_be_visible(timeout=10_000)
        result = self._wait_for_new_expected_content(
            before,
            expected_any,
            forbidden,
            label=f"AI response to {prompt!r}",
            timeout_ms=60_000,
        )
        expect(chat_input).to_be_editable(timeout=45_000)
        return result

    def _wait_for_expected_content(
        self,
        expected_any: list[str],
        forbidden: list[str],
        *,
        label: str,
        timeout_ms: int,
    ) -> str:
        deadline = time.monotonic() + timeout_ms / 1000
        current = ""
        while time.monotonic() < deadline:
            current = self.page.locator("body").inner_text()
            if any(term.casefold() in current.casefold() for term in expected_any):
                assert_contains_any(current, expected_any, label)
                assert_contains_none(current, forbidden, label)
                return current
            self.page.wait_for_timeout(500)
        raise AssertionError(
            f"{label} did not contain any expected term {expected_any!r} within {timeout_ms} ms."
        )

    def _wait_for_new_expected_content(
        self,
        before: str,
        expected_any: list[str],
        forbidden: list[str],
        *,
        label: str,
        timeout_ms: int,
    ) -> str:
        before_folded = before.casefold()
        baseline = {term: before_folded.count(term.casefold()) for term in expected_any}
        deadline = time.monotonic() + timeout_ms / 1000
        current = before
        while time.monotonic() < deadline:
            current = self.page.locator("body").inner_text()
            folded = current.casefold()
            if any(
                folded.count(term.casefold()) > baseline[term]
                for term in expected_any
            ):
                assert_contains_any(current, expected_any, label)
                assert_contains_none(current, forbidden, label)
                return current
            self.page.wait_for_timeout(500)
        raise AssertionError(
            f"{label} did not add any expected term {expected_any!r} within {timeout_ms} ms."
        )
