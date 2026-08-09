from scripts.check_diarization_quality import evaluate


def summary(diarization_score: float, clinical_score: float) -> dict[str, object]:
    return {
        "diarization": {
            "average_overall_score": diarization_score,
            "average_content_retention": diarization_score,
            "average_overall_attribution": diarization_score,
            "average_transcription_integrity": diarization_score,
        },
        "clinical_note": {
            "average_fact_retention": clinical_score,
            "average_fidelity": clinical_score,
            "average_hallucination_integrity": clinical_score,
        },
    }


def test_values_equal_to_thresholds_pass() -> None:
    assert all(check.passed for check in evaluate(summary(92, 90)))


def test_diarization_value_below_92_fails() -> None:
    checks = evaluate(summary(91.99, 90))
    assert any(not check.passed for check in checks[:4])


def test_clinical_value_below_90_fails() -> None:
    checks = evaluate(summary(92, 89.99))
    assert any(not check.passed for check in checks[4:])
