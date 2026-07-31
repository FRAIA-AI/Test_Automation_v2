"""Browser fixtures with diagnostics retained when a test fails."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest
from playwright.sync_api import Browser, BrowserContext, Page


@dataclass(slots=True)
class AppSession:
    context: BrowserContext
    page: Page


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict) -> dict:
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
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture
def app_session_factory(
    browser: Browser, request: pytest.FixtureRequest, pytestconfig: pytest.Config
) -> Callable[..., AppSession]:
    """Create isolated browser contexts; a retry receives a truly fresh session."""

    sessions: list[AppSession] = []
    output_dir = Path(str(pytestconfig.getoption("output")))
    video_dir = output_dir / "videos"
    trace_dir = output_dir / "traces"
    screenshot_dir = output_dir / "screenshots"
    for directory in (video_dir, trace_dir, screenshot_dir):
        directory.mkdir(parents=True, exist_ok=True)

    def create(*, media_permissions: bool = False) -> AppSession:
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            permissions=["camera", "microphone"] if media_permissions else [],
            record_video_dir=str(video_dir),
            record_video_size={"width": 1920, "height": 1080},
        )
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        session = AppSession(context=context, page=context.new_page())
        sessions.append(session)
        return session

    yield create

    failed = bool(getattr(request.node, "rep_call", None) and request.node.rep_call.failed)
    for index, session in enumerate(sessions, start=1):
        videos = [page.video for page in session.context.pages if page.video]
        try:
            if failed and not session.page.is_closed():
                session.page.screenshot(
                    path=str(screenshot_dir / f"{request.node.name}-attempt-{index}.png"),
                    full_page=True,
                )
            trace_path = trace_dir / f"{request.node.name}-attempt-{index}.zip"
            session.context.tracing.stop(path=str(trace_path) if failed else None)
        finally:
            session.context.close()
        if not failed:
            for video in videos:
                try:
                    Path(video.path()).unlink(missing_ok=True)
                except Exception:
                    # Evidence cleanup must never change a successful test into a failure.
                    pass
