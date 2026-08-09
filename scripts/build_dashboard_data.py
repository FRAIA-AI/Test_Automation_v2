"""Build static dashboard data and extract monitor evidence from GitHub Actions."""

from __future__ import annotations

import json
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]
API = "https://api.github.com"
OUTPUT = Path("public")
DATA_DIR = OUTPUT / "data"
EVIDENCE_DIR = OUTPUT / "evidence"

MONITORS = {
    "smoke": {
        "label": "Smoke",
        "workflow": "smoke.yml",
        "threshold_minutes": 30,
        "expected_interval_minutes": 10,
    },
    "regression": {
        "label": "Regression",
        "workflow": "regression.yml",
        "threshold_minutes": 120,
        "expected_interval_minutes": 60,
    },
    "fnx": {
        "label": "FNX",
        "workflow": "fnx.yml",
        "threshold_minutes": 180,
        "expected_interval_minutes": 120,
    },
    "diarization": {
        "label": "Diarization benchmark",
        "workflow": "diarization.yml",
        "threshold_minutes": None,
        "expected_interval_minutes": None,
        "kind": "benchmark",
        "expected_case_count": 25,
        "schedule_label": "Weekly · Sunday 03:30 UTC",
    },
}


def api_json(path: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "clinic-monitoring-dashboard",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def download(url: str, destination: Path) -> None:
    class ArtifactRedirectHandler(urllib.request.HTTPRedirectHandler):
        """Do not forward GitHub credentials to signed blob-storage URLs."""

        def redirect_request(
            self,
            request: urllib.request.Request,
            file_pointer: Any,
            code: int,
            message: str,
            headers: Any,
            new_url: str,
        ) -> urllib.request.Request | None:
            redirected = super().redirect_request(
                request, file_pointer, code, message, headers, new_url
            )
            if redirected and (
                urllib.parse.urlsplit(request.full_url).netloc
                != urllib.parse.urlsplit(new_url).netloc
            ):
                redirected.remove_header("Authorization")
                redirected.remove_header("Accept")
                redirected.remove_header("X-GitHub-Api-Version")
            return redirected

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "clinic-monitoring-dashboard",
        },
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(ArtifactRedirectHandler())
    with opener.open(request, timeout=120) as response:
        destination.write_bytes(response.read())


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def duration_seconds(run: dict[str, Any]) -> float | None:
    started = parse_time(run.get("run_started_at") or run.get("created_at"))
    finished = parse_time(run.get("updated_at"))
    if not started or not finished:
        return None
    return round(max(0.0, (finished - started).total_seconds()), 2)


def extract_main_error(text: str) -> str:
    if not text.strip():
        return "No concise error was captured. Open the GitHub run for details."
    markers = ("\nCall log:", "\nAria snapshot:", "\n====", "\nCaptured stdout")
    for marker in markers:
        if marker in text:
            text = text.split(marker, 1)[0]
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("self =", "oracle =", "_ _ _")):
            continue
        if line.startswith("E "):
            line = line[2:].strip()
        if line not in lines:
            lines.append(line)
    return "\n".join(lines[-8:])[:1800] or "No concise error was captured."


def safe_extract(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        root = destination.resolve()
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if root not in target.parents and target != root:
                continue
            archive.extract(member, destination)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def parse_diarization_evaluation(extracted: Path) -> dict[str, Any] | None:
    """Return a compact, UI-ready view of the latest benchmark artifact."""
    summaries = [path for path in extracted.rglob("evaluation-summary.json") if path.is_file()]
    if not summaries:
        return None
    summary = read_json(summaries[0])
    if not summary:
        return None

    metadata: dict[str, dict[str, Any]] = {}
    for path in extracted.rglob("metadata.json"):
        item = read_json(path)
        if item and item.get("case_id"):
            metadata[str(item["case_id"])] = item

    cases: list[dict[str, Any]] = []
    for path in extracted.rglob("case_*.json"):
        item = read_json(path)
        if not item or "expected_turn_count" not in item or not item.get("case_id"):
            continue
        case_id = str(item["case_id"])
        meta = metadata.get(case_id, {})
        item["expected_speaker_count"] = meta.get("expected_speaker_count")
        item["expected_speakers"] = meta.get("expected_speakers", [])
        item["duration_seconds"] = meta.get("duration_seconds")
        cases.append(item)
    cases.sort(key=lambda item: str(item.get("case_id", "")))

    count_fields = (
        "expected_turn_count",
        "evaluated_turn_count",
        "correctly_attributed_turns",
        "misattributed_turns",
        "missing_turns",
    )
    turns = {field: sum(int(item.get(field) or 0) for item in cases) for field in count_fields}
    return {"summary": summary, "cases": cases, "turns": turns}


def copy_evidence(monitor: str, extracted: Path) -> dict[str, Any]:
    target = EVIDENCE_DIR / monitor
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)

    screenshots: list[str] = []
    videos: list[str] = []
    traces: list[str] = []
    documents: list[str] = []
    main_error: str | None = None

    for source in extracted.rglob("*"):
        if not source.is_file():
            continue
        suffix = source.suffix.casefold()
        if suffix not in {".png", ".jpg", ".jpeg", ".webm", ".zip", ".txt", ".xml", ".json"}:
            continue
        name = source.name
        destination = target / name
        counter = 1
        while destination.exists():
            destination = target / f"{source.stem}-{counter}{source.suffix}"
            counter += 1
        shutil.copy2(source, destination)
        relative = destination.relative_to(OUTPUT).as_posix()
        if suffix in {".png", ".jpg", ".jpeg"}:
            screenshots.append(relative)
        elif suffix == ".webm":
            videos.append(relative)
        elif suffix == ".zip" and "trace" in name.casefold():
            traces.append(relative)
        elif name == "main-error.txt":
            documents.append(relative)
            main_error = source.read_text(encoding="utf-8", errors="replace")[:3000]
        elif suffix in {".txt", ".xml", ".json"}:
            documents.append(relative)

    screenshots.sort()
    videos.sort()
    traces.sort()
    documents.sort()
    return {
        "screenshots": screenshots,
        "videos": videos,
        "traces": traces,
        "documents": documents,
        "main_error": main_error,
        "evaluation": parse_diarization_evaluation(extracted) if monitor == "diarization" else None,
    }


def latest_artifact_for_run(run_id: int) -> dict[str, Any] | None:
    data = api_json(f"/repos/{REPOSITORY}/actions/runs/{run_id}/artifacts?per_page=100")
    artifacts = [item for item in data.get("artifacts", []) if not item.get("expired")]
    if not artifacts:
        return None
    artifacts.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return artifacts[0]


def load_evidence(monitor: str, run: dict[str, Any]) -> dict[str, Any]:
    artifact = latest_artifact_for_run(int(run["id"]))
    empty = {"screenshots": [], "videos": [], "traces": [], "documents": [], "main_error": None, "evaluation": None}
    if artifact is None:
        return empty

    work = Path(".dashboard-work") / monitor
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    zip_path = work / "artifact.zip"
    extracted = work / "extracted"
    try:
        download(artifact["archive_download_url"], zip_path)
        safe_extract(zip_path, extracted)
        return copy_evidence(monitor, extracted)
    except (OSError, urllib.error.URLError, zipfile.BadZipFile) as error:
        print(f"WARNING: evidence extraction failed for {monitor}: {error}")
        return empty


def monitor_data(key: str, config: dict[str, Any]) -> dict[str, Any]:
    workflow = config["workflow"]
    response = api_json(
        f"/repos/{REPOSITORY}/actions/workflows/{workflow}/runs?branch=main&per_page=50"
    )
    runs = response.get("workflow_runs", [])
    history: list[dict[str, Any]] = []

    for run in runs:
        history.append(
            {
                "id": run["id"],
                "number": run.get("run_number"),
                "event": run.get("event"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "created_at": run.get("created_at"),
                "started_at": run.get("run_started_at"),
                "updated_at": run.get("updated_at"),
                "duration_seconds": duration_seconds(run),
                "url": run.get("html_url"),
                "sha": run.get("head_sha"),
                "actor": (run.get("actor") or {}).get("login"),
            }
        )

    latest_completed = next((run for run in runs if run.get("status") == "completed"), None)
    latest_any = runs[0] if runs else None
    evidence = load_evidence(key, latest_completed) if latest_completed else {
        "screenshots": [], "videos": [], "traces": [], "documents": [],
        "main_error": None, "evaluation": None,
    }

    main_error = evidence.get("main_error")
    if not main_error and latest_completed and latest_completed.get("conclusion") != "success":
        main_error = (
            f"Workflow concluded with {latest_completed.get('conclusion')}. "
            "Open the run for the complete failure details."
        )

    return {
        "key": key,
        "label": config["label"],
        "workflow": workflow,
        "threshold_minutes": config["threshold_minutes"],
        "expected_interval_minutes": config["expected_interval_minutes"],
        "kind": config.get("kind", "monitor"),
        "expected_case_count": config.get("expected_case_count"),
        "schedule_label": config.get("schedule_label"),
        "latest": history[0] if history else None,
        "latest_completed": next((item for item in history if item["status"] == "completed"), None),
        "main_error": main_error,
        "evidence": evidence,
        "history": history,
        "workflow_url": (
            f"https://github.com/{REPOSITORY}/actions/workflows/{workflow}"
        ),
        "currently_running": bool(latest_any and latest_any.get("status") != "completed"),
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    monitors: dict[str, Any] = {}
    for key, config in MONITORS.items():
        try:
            monitors[key] = monitor_data(key, config)
        except urllib.error.HTTPError as error:
            print(f"ERROR: could not build {key}: HTTP {error.code}")
            monitors[key] = {
                "key": key,
                "label": config["label"],
                "workflow": config["workflow"],
                "threshold_minutes": config["threshold_minutes"],
                "expected_interval_minutes": config["expected_interval_minutes"],
                "kind": config.get("kind", "monitor"),
                "expected_case_count": config.get("expected_case_count"),
                "schedule_label": config.get("schedule_label"),
                "latest": None,
                "latest_completed": None,
                "main_error": f"Dashboard data build failed with HTTP {error.code}.",
                "evidence": {"screenshots": [], "videos": [], "traces": [], "documents": [], "evaluation": None},
                "history": [],
                "workflow_url": f"https://github.com/{REPOSITORY}/actions/workflows/{config['workflow']}",
                "currently_running": False,
            }

    payload = {
        "repository": REPOSITORY,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "refresh_seconds": 300,
        "monitors": monitors,
    }
    (DATA_DIR / "dashboard.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: len(value.get("history", [])) for key, value in monitors.items()}))


if __name__ == "__main__":
    main()
