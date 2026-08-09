from datetime import datetime, timezone

from scripts.send_alert import FailureSummary, build_message


def test_diarization_email_includes_dashboard_and_reports(
    tmp_path,
    monkeypatch,
) -> None:
    evaluation = tmp_path / "evaluation"
    evaluation.mkdir()
    (evaluation / "evaluation-summary.json").write_text(
        '{"cases_evaluated": 3}',
        encoding="utf-8",
    )
    (evaluation / "evaluation-report.txt").write_text(
        "Complete evaluation report",
        encoding="utf-8",
    )

    monkeypatch.setenv("MAIL_SENDER_ADDRESS", "alerts@example.com")
    monkeypatch.setenv("MAIL_RECIPIENT_ADDRESS", "team@example.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "FRAIA-AI/Test_Automation_v2")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv(
        "MONITOR_DASHBOARD_URL",
        "https://fraia-ai.github.io/Test_Automation_v2/diarization.html",
    )

    message = build_message(
        "Peoples Clinic Diarization Benchmark",
        "failure",
        datetime(2026, 8, 9, 10, 0, tzinfo=timezone.utc),
        FailureSummary(
            test_name="diarization_overall",
            exception_type="QualityThresholdFailure",
            phase="quality gate",
            message="Diarization overall is below 92%",
        ),
        tmp_path,
    )

    body = message.get_body(preferencelist=("plain",)).get_content()
    filenames = {
        attachment.get_filename()
        for attachment in message.iter_attachments()
    }
    assert "https://fraia-ai.github.io/Test_Automation_v2/diarization.html" in body
    assert "https://github.com/FRAIA-AI/Test_Automation_v2/actions/runs/123" in body
    assert "main-error.txt" in filenames
    assert "evaluation-summary.json" in filenames
    assert "evaluation-report.txt" in filenames
