"""Clinical-note collection helpers used only by the diarization benchmark."""

from __future__ import annotations

import re
import time

from playwright.sync_api import Locator, Page, expect


def _note_editor(page: Page) -> Locator:
    """Locate the rich-text note editor without matching surrounding content."""

    candidates = [
        page.locator(".ProseMirror[contenteditable='true']"),
        page.locator("[contenteditable='true'].ProseMirror"),
        page.locator(".rich-text-content [contenteditable='true']"),
        page.locator("[role='textbox'][contenteditable='true']"),
    ]

    for locator in candidates:
        if locator.count() > 0:
            return locator.first

    return page.locator(".ProseMirror, .rich-text-content").first


def _generation_loader(page: Page) -> Locator:
    """Match the text-bearing note-generation loader in either UI language."""

    return page.locator("span, p").filter(
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


def wait_for_generated_note(
    page: Page,
    *,
    timeout_ms: int = 120_000,
    minimum_words: int = 10,
) -> str:
    """Wait until a generated clinical note is present and the loader is gone."""

    editor = _note_editor(page)
    expect(editor).to_be_visible(timeout=60_000)

    deadline = time.monotonic() + timeout_ms / 1000
    last_text = ""
    last_loader_visible = False

    while time.monotonic() < deadline:
        try:
            last_text = editor.inner_text(timeout=5_000).strip()
        except Exception:
            last_text = ""

        loader = _generation_loader(page)
        last_loader_visible = (
            loader.count() > 0
            and loader.first.is_visible()
        )

        if len(last_text.split()) >= minimum_words and not last_loader_visible:
            return last_text

        page.wait_for_timeout(1_000)

    raise AssertionError(
        "Generated note did not become available within "
        f"{timeout_ms // 1000} seconds. "
        f"Required at least {minimum_words} words; "
        f"received {len(last_text.split())}. "
        f"Generation loader visible: {last_loader_visible}. "
        f"Current note text: {last_text[:1000]!r}"
    )
