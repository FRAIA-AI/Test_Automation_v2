"""State-based live consultation, note approval, and feedback interactions."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from tests.helpers.oracle import assert_contains_any, assert_contains_none


class ConsultationPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def finish_and_open_note(self) -> None:
        finish = self.page.get_by_role(
            "button",
            name=re.compile(r"Finish\s*&\s*Edit Note|Afslut.*rediger", re.IGNORECASE),
        ).first
        expect(finish).to_be_enabled(timeout=15_000)
        finish.click()
        expect(
            self.page.get_by_text(re.compile(r"Edit and Save Note|Rediger.*gem.*notat", re.IGNORECASE)).first
        ).to_be_visible(timeout=60_000)

    def wait_for_valid_note(self, oracle: dict) -> str:
        loader = self.page.get_by_text(
            re.compile(r"Note is being generated|Notat.*generer", re.IGNORECASE)
        )
        if loader.count():
            expect(loader).to_be_hidden(timeout=120_000)

        editor = self.page.locator(
            ".rich-text-content, .ProseMirror, .mantine-TypographyStylesProvider-root"
        ).first
        expect(editor).to_be_visible(timeout=20_000)
        expect(editor).to_contain_text(re.compile(r"[A-Za-zÆØÅæøå]"), timeout=20_000)
        note_text = editor.inner_text().strip()

        minimum_words = int(oracle.get("minimum_note_words", 20))
        if len(note_text.split()) < minimum_words:
            raise AssertionError(
                f"Generated note has {len(note_text.split())} words; expected at least {minimum_words}. "
                f"Text: {note_text!r}"
            )
        assert_contains_none(
            note_text,
            list(oracle.get("forbidden_note_terms", [])),
            "Generated note",
        )
        assert_contains_any(
            note_text,
            list(oracle.get("expected_note_any", [])),
            "Generated note",
        )
        return note_text

    def approve_note(self) -> None:
        approve = self.page.get_by_role(
            "button", name=re.compile(r"Approve\s*&\s*Save Note|Godkend.*gem", re.IGNORECASE)
        ).first
        expect(approve).to_be_enabled(timeout=15_000)
        approve.click()

        feedback = self.page.get_by_role("dialog").filter(
            has_text=re.compile(r"How accurate was the note|Hvor præcis", re.IGNORECASE)
        )
        expect(feedback).to_be_visible(timeout=30_000)

    def submit_feedback(self, rating: int = 10) -> None:
        feedback = self.page.get_by_role("dialog").filter(
            has_text=re.compile(r"How accurate was the note|Hvor præcis", re.IGNORECASE)
        )
        expect(feedback).to_be_visible(timeout=10_000)
        rating_button = feedback.get_by_text(str(rating), exact=True).first
        expect(rating_button).to_be_visible(timeout=10_000)
        rating_button.click()
        submit = feedback.get_by_role(
            "button", name=re.compile(r"Send Feedback|Send feedback", re.IGNORECASE)
        ).first
        expect(submit).to_be_enabled(timeout=10_000)
        submit.click()
        expect(feedback).to_be_hidden(timeout=20_000)
        expect(self.page).to_have_url(re.compile(r".*/dashboard"), timeout=30_000)
