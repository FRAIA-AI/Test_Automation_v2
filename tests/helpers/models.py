"""Small, serializable models for test outcomes and incident classification."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class FailureCategory(StrEnum):
    APPLICATION = "application"
    ASSERTION = "assertion"
    AUTOMATION = "automation"
    INFRASTRUCTURE = "infrastructure"
    TRANSIENT = "transient"


@dataclass(slots=True)
class MonitorFailure(Exception):
    """An expected, classified monitor failure suitable for reporting."""

    message: str
    category: FailureCategory
    phase: str
    code: str | None = None

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True, slots=True)
class TestResult:
    test: str
    status: str
    started_at: str
    finished_at: str
    duration_seconds: float
    phase: str
    attempts: int
    failure: dict[str, Any] | None = None

    @classmethod
    def started(cls) -> datetime:
        return datetime.now(UTC)

    @classmethod
    def from_failure(
        cls, *, test: str, phase: str, started_at: datetime, attempts: int, failure: Exception
    ) -> "TestResult":
        finished_at = datetime.now(UTC)
        failure_data: dict[str, Any] = {
            "type": type(failure).__name__,
            "message": str(failure),
        }
        if isinstance(failure, MonitorFailure):
            failure_data.update(category=failure.category, code=failure.code)
        return cls(
            test=test,
            status="failure",
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_seconds=round((finished_at - started_at).total_seconds(), 3),
            phase=phase,
            attempts=attempts,
            failure=failure_data,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
