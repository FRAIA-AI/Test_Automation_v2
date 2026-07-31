"""Load and validate deterministic expectations stored beside test fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.helpers.config import ConfigurationError


def load_oracle(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigurationError(f"Cannot load oracle file {path}: {error}") from error
    if not isinstance(data, dict):
        raise ConfigurationError(f"Oracle file must contain a JSON object: {path}")
    return data


def assert_contains_any(text: str, terms: list[str], label: str) -> None:
    normalized = text.casefold()
    if not terms:
        raise ConfigurationError(f"Oracle has no expectations for {label}.")
    if not any(term.casefold() in normalized for term in terms):
        raise AssertionError(f"{label} did not contain any expected term {terms!r}. Text: {text!r}")


def assert_contains_all(text: str, terms: list[str], label: str) -> None:
    normalized = text.casefold()
    missing = [term for term in terms if term.casefold() not in normalized]
    if missing:
        raise AssertionError(f"{label} is missing expected terms {missing!r}. Text: {text!r}")


def assert_contains_none(text: str, terms: list[str], label: str) -> None:
    normalized = text.casefold()
    found = [term for term in terms if term.casefold() in normalized]
    if found:
        raise AssertionError(f"{label} contains failure terms {found!r}. Text: {text!r}")
