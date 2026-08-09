"""Fail a scheduled diarization benchmark when aggregate quality drops."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


DIARIZATION_MINIMUM = 92.0
CLINICAL_NOTE_MINIMUM = 90.0


@dataclass(frozen=True)
class QualityCheck:
    label: str
    value: float
    minimum: float

    @property
    def passed(self) -> bool:
        return self.value >= self.minimum


def evaluate(summary: dict[str, object]) -> list[QualityCheck]:
    diarization = summary.get("diarization") or {}
    clinical = summary.get("clinical_note") or {}
    if not isinstance(diarization, dict) or not isinstance(clinical, dict):
        raise ValueError("evaluation summary is missing required score groups")
    return [
        QualityCheck(
            "Diarization overall",
            float(diarization.get("average_overall_score", 0)),
            DIARIZATION_MINIMUM,
        ),
        QualityCheck(
            "Content retention",
            float(diarization.get("average_content_retention", 0)),
            DIARIZATION_MINIMUM,
        ),
        QualityCheck(
            "Overall attribution",
            float(diarization.get("average_overall_attribution", 0)),
            DIARIZATION_MINIMUM,
        ),
        QualityCheck(
            "Transcription integrity",
            float(diarization.get("average_transcription_integrity", 0)),
            DIARIZATION_MINIMUM,
        ),
        QualityCheck(
            "Clinical fact retention",
            float(clinical.get("average_fact_retention", 0)),
            CLINICAL_NOTE_MINIMUM,
        ),
        QualityCheck(
            "Clinical note fidelity",
            float(clinical.get("average_fidelity", 0)),
            CLINICAL_NOTE_MINIMUM,
        ),
        QualityCheck(
            "Clinical hallucination integrity",
            float(clinical.get("average_hallucination_integrity", 0)),
            CLINICAL_NOTE_MINIMUM,
        ),
    ]


def write_junit(path: Path, checks: list[QualityCheck]) -> None:
    failures = [check for check in checks if not check.passed]
    suite = ET.Element(
        "testsuite",
        name="diarization_quality_gate",
        tests=str(len(checks)),
        failures=str(len(failures)),
        errors="0",
    )
    for check in checks:
        case = ET.SubElement(
            suite,
            "testcase",
            classname="monitoring.diarization.quality",
            name=check.label.lower().replace(" ", "_"),
        )
        if not check.passed:
            failure = ET.SubElement(
                case,
                "failure",
                type="QualityThresholdFailure",
                message=f"{check.label} is {check.value:.2f}%, below {check.minimum:.2f}%",
            )
            failure.text = (
                f"Scheduled diarization quality alarm: {check.label} fell to "
                f"{check.value:.2f}% (required minimum {check.minimum:.2f}%)."
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    checks = evaluate(summary)
    write_junit(args.junit, checks)
    for check in checks:
        state = "PASS" if check.passed else "FAIL"
        print(f"{state}: {check.label}: {check.value:.2f}% (minimum {check.minimum:.2f}%)")
    return 1 if any(not check.passed for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
