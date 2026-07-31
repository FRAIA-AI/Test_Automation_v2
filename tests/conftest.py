"""Browser fixtures and deterministic monitoring evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest
from playwright.sync_api import Browser, BrowserContext, Page


@dataclass(slots=True)
class AppSession:
    context: BrowserContext
    page: Page


class StageEvidence:
    """Capture named screenshots for important business stages."""

    def __init__(
        self,
        page: Page,
        output_dir: Path,
        test_name: str,
    ) -> None:
        self.page = page
        self.test_name = _safe_name(test_name)

        self.screenshot_dir = output_dir / "stage-screenshots"
        self.screenshot_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.counter = 0

    def capture(self, stage: str) -> Path:
        self.counter += 1

        safe_stage = _safe_name(stage)

        path = self.screenshot_dir / (
            f"{self.test_name}-"
            f"{self.counter:02d}-"
            f"{safe_stage}.png"
        )

        if not self.page.is_closed():
            self.page.screenshot(
                path=str(path),
                full_page=True,
            )

        return path


def _safe_name(value: str) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "-",
        value,
    ).strip("-")

    return cleaned or "unnamed"


@pytest.fixture(scope="session")
def browser_type_launch_args(
    browser_type_launch_args: dict,
) -> dict:
    """Give deep tests deterministic fake camera/microphone devices."""

    return {
        **browser_type_launch_args,
        "args": [
            *browser_type_launch_args.get("args", []),
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
        ],
    }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[object],
):
    outcome = yield
    report = outcome.get_result()

    setattr(
        item,
        f"rep_{report.when}",
        report,
    )


@pytest.fixture
def app_session_factory(
    browser: Browser,
    request: pytest.FixtureRequest,
    pytestconfig: pytest.Config,
) -> Callable[..., AppSession]:
    """
    Create isolated browser contexts.

    Screenshots, traces, and videos are finalized during fixture teardown.
    """

    sessions: list[AppSession] = []

    output_dir = Path(
        str(pytestconfig.getoption("output"))
    )

    video_dir = output_dir / "videos"
    trace_dir = output_dir / "traces"
    failure_screenshot_dir = (
        output_dir / "failure-screenshots"
    )

    for directory in (
        video_dir,
        trace_dir,
        failure_screenshot_dir,
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def create(
        *,
        media_permissions: bool = False,
    ) -> AppSession:
        context = browser.new_context(
            viewport={
                "width": 1920,
                "height": 1080,
            },
            permissions=(
                ["camera", "microphone"]
                if media_permissions
                else []
            ),
            record_video_dir=str(video_dir),
            record_video_size={
                "width": 1920,
                "height": 1080,
            },
        )

        context.tracing.start(
            screenshots=True,
            snapshots=True,
            sources=True,
        )

        page = context.new_page()

        session = AppSession(
            context=context,
            page=page,
        )

        sessions.append(session)

        return session

    yield create

    failed = bool(
        getattr(
            request.node,
            "rep_call",
            None,
        )
        and request.node.rep_call.failed
    )

    for index, session in enumerate(
        sessions,
        start=1,
    ):
        test_name = _safe_name(
            request.node.name
        )

        video_handles = [
            page.video
            for page in session.context.pages
            if page.video is not None
        ]

        try:
            if (
                failed
                and not session.page.is_closed()
            ):
                session.page.screenshot(
                    path=str(
                        failure_screenshot_dir
                        / (
                            f"{test_name}-"
                            f"attempt-{index}.png"
                        )
                    ),
                    full_page=True,
                )

            trace_path = (
                trace_dir
                / (
                    f"{test_name}-"
                    f"attempt-{index}.zip"
                )
            )

            session.context.tracing.stop(
                path=(
                    str(trace_path)
                    if failed
                    else None
                )
            )

        finally:
            # Video files are finalized only after context closure.
            session.context.close()

        if not failed:
            for video in video_handles:
                try:
                    Path(
                        video.path()
                    ).unlink(
                        missing_ok=True
                    )
                except Exception:
                    # Cleanup must never turn a passed test into a failure.
                    pass


@pytest.fixture
def stage_evidence(
    request: pytest.FixtureRequest,
    pytestconfig: pytest.Config,
):
    """Create stage evidence after a browser page exists."""

    output_dir = Path(
        str(pytestconfig.getoption("output"))
    )

    def create(
        page: Page,
    ) -> StageEvidence:
        return StageEvidence(
            page=page,
            output_dir=output_dir,
            test_name=request.node.name,
        )

    return create
