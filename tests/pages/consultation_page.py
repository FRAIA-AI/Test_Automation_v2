"""State-based consultation, note approval, and feedback interactions."""

from __future__ import annotations

import re
import time

from playwright.sync_api import Locator, Page, expect

from tests.helpers.oracle import (
    assert_contains_any,
    assert_contains_none,
)


class ConsultationPage:
    def __init__(
        self,
        page: Page,
    ) -> None:
        self.page = page

    def finish_and_open_note(
        self,
    ) -> None:
        finish = self.page.get_by_role(
            "button",
            name=re.compile(
                r"Finish\s*&\s*Edit Note|"
                r"Afslut.*rediger",
                re.IGNORECASE,
            ),
        ).first

        expect(
            finish
        ).to_be_enabled(
            timeout=15_000
        )

        finish.click()

        heading = self.page.get_by_text(
            re.compile(
                r"Edit and Save Note|"
                r"Rediger.*gem.*note|"
                r"Rediger.*gem.*notat",
                re.IGNORECASE,
            )
        ).first

        expect(
            heading
        ).to_be_visible(
            timeout=60_000
        )

    def _note_editor(
        self,
    ) -> Locator:
        """
        Prefer the actual rich-text editor.

        Avoid broad Mantine typography containers because they can include
        the patient résumé and unrelated page content.
        """

        candidates = [
            self.page.locator(
                ".ProseMirror[contenteditable='true']"
            ),
            self.page.locator(
                "[contenteditable='true'].ProseMirror"
            ),
            self.page.locator(
                ".rich-text-content "
                "[contenteditable='true']"
            ),
            self.page.locator(
                "[role='textbox']"
                "[contenteditable='true']"
            ),
        ]

        for locator in candidates:
            if locator.count() > 0:
                return locator.first

        return self.page.locator(
            ".ProseMirror, "
            ".rich-text-content"
        ).first

    def _generation_loader(
        self,
    ) -> Locator:
        """
        Match only the actual text-bearing loader element.

        The exact-text anchors prevent Playwright from switching from the
        loader span to a visible parent div.
        """

        return self.page.locator(
            "span, p"
        ).filter(
            has_text=re.compile(
                r"^\s*(?:"
                r"Note is being generated"
                r"(?:,?\s*please wait)?\.?|"
                r"Notatet genereres"
                r"(?:,\s*vent venligst)?\.?|"
                r"Notat(?:et)? .*generer(?:es)?.*"
                r")\s*$",
                re.IGNORECASE,
            )
        )

    def wait_for_valid_note(
        self,
        oracle: dict,
        timeout_ms: int = 120_000,
    ) -> str:
        editor = self._note_editor()

        expect(
            editor
        ).to_be_visible(
            timeout=60_000
        )

        minimum_words = int(
            oracle.get(
                "minimum_note_words",
                20,
            )
        )

        forbidden = list(
            oracle.get(
                "forbidden_note_terms",
                [],
            )
        )

        expected_any = list(
            oracle.get(
                "expected_note_any",
                [],
            )
        )

        deadline = (
            time.monotonic()
            + timeout_ms / 1000
        )

        last_text = ""
        last_loader_visible = False

        while time.monotonic() < deadline:
            try:
                last_text = editor.inner_text(
                    timeout=5_000
                ).strip()
            except Exception:
                last_text = ""

            loader = self._generation_loader()

            last_loader_visible = (
                loader.count() > 0
                and loader.first.is_visible()
            )

            if (
                len(last_text.split())
                >= minimum_words
            ):
                assert_contains_none(
                    last_text,
                    forbidden,
                    "Generated note",
                )

                assert_contains_any(
                    last_text,
                    expected_any,
                    "Generated note",
                )

                return last_text

            self.page.wait_for_timeout(
                1_000
            )

        raise AssertionError(
            "Generated note did not become valid within "
            f"{timeout_ms // 1000} seconds. "
            f"Required at least {minimum_words} words; "
            f"received {len(last_text.split())}. "
            f"Generation loader visible: "
            f"{last_loader_visible}. "
            f"Current note text: "
            f"{last_text[:1000]!r}"
        )

    def approve_note(
        self,
    ) -> None:
        approve = self.page.get_by_role(
            "button",
            name=re.compile(
                r"Approve\s*&\s*Save Note|"
                r"Godkend.*gem",
                re.IGNORECASE,
            ),
        ).first

        expect(
            approve
        ).to_be_enabled(
            timeout=15_000
        )

        approve.click()

        feedback = self._feedback_dialog()

        expect(
            feedback
        ).to_be_visible(
            timeout=30_000
        )

    def _feedback_dialog(
        self,
    ) -> Locator:
        return self.page.get_by_role(
            "dialog"
        ).filter(
            has_text=re.compile(
                r"How accurate was the note|"
                r"Hvor præcis",
                re.IGNORECASE,
            )
        )

    def submit_feedback(
        self,
        rating: int = 10,
    ) -> None:
        feedback = self._feedback_dialog()

        expect(
            feedback
        ).to_be_visible(
            timeout=10_000
        )

        rating_button = feedback.get_by_text(
            str(rating),
            exact=True,
        ).first

        expect(
            rating_button
        ).to_be_visible(
            timeout=10_000
        )

        rating_button.click()

        submit = feedback.get_by_role(
            "button",
            name=re.compile(
                r"Send Feedback|"
                r"Send feedback|"
                r"Send feedbacken",
                re.IGNORECASE,
            ),
        ).first

        expect(
            submit
        ).to_be_enabled(
            timeout=10_000
        )

        submit.click()

        expect(
            feedback
        ).to_be_hidden(
            timeout=20_000
        )

        expect(
            self.page
        ).to_have_url(
            re.compile(
                r".*/dashboard"
            ),
            timeout=30_000,
        )
