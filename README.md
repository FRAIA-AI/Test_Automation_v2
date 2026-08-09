# People's Clinic Monitoring v2

<p align="center">
  <a href="https://clinic.peoplesdoctor.ai/">
    <img src="https://clinic.peoplesdoctor.ai/assets/images/peoples-doctor-logo-onboarding.png" alt="People's Clinic" width="150">
  </a>
</p>

<p align="center">
  Production synthetic monitoring for People's Clinic using <strong>Python 3.12</strong>, <strong>pytest</strong>, <strong>Playwright</strong>, GitHub Actions, SMTP incident alerts, retained evidence, and a GitHub Pages operations dashboard.
</p>

<p align="center">
  <a href="https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/smoke.yml"><img src="https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/smoke.yml/badge.svg?branch=main" alt="Smoke Monitor"></a>
  <a href="https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/regression.yml"><img src="https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/regression.yml/badge.svg?branch=main" alt="Consultation Regression"></a>
  <a href="https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/fnx.yml"><img src="https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/fnx.yml/badge.svg?branch=main" alt="FNX Parser and AI"></a>
  <a href="https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/dashboard.yml"><img src="https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/dashboard.yml/badge.svg?branch=main" alt="Monitoring Dashboard"></a>
</p>

<p align="center">
  <a href="https://clinic.peoplesdoctor.ai/"><strong>Open People's Clinic</strong></a>
  ·
  <a href="https://fraia-ai.github.io/Test_Automation_v2/"><strong>Open Live Monitoring Dashboard</strong></a>
  ·
  <a href="https://github.com/FRAIA-AI/Test_Automation_v2/actions"><strong>View GitHub Actions</strong></a>
</p>

> **Production caution**
>
> Deep monitors create synthetic activity in the production application. Use only approved automation accounts, synthetic patient identifiers, and approved fixture files. Never use real patient data.

---

## Live monitoring dashboard

The public dashboard combines current health, stale-monitor detection, execution history, failure context, screenshots, videos, traces, timing, 2D trends, and a 3D reliability view.

<p align="center">
  <a href="https://fraia-ai.github.io/Test_Automation_v2/">
    <img src="https://image.thum.io/get/width/1600/crop/900/noanimate/https://fraia-ai.github.io/Test_Automation_v2/" alt="People's Clinic monitoring dashboard live preview" width="100%">
  </a>
</p>

> The image above is a live external preview of the deployed dashboard. Click it to open the interactive version.

### Platform preview

<p align="center">
  <a href="https://clinic.peoplesdoctor.ai/">
    <img src="https://image.thum.io/get/width/1400/crop/760/noanimate/https://clinic.peoplesdoctor.ai/" alt="People's Clinic platform sign-in page" width="85%">
  </a>
</p>

The README intentionally shows only the public platform entry page. Authenticated consultation pages, transcripts, CPR values, generated notes, and medical content are excluded from repository documentation.

---

## Current monitor results

The badges at the top of this README always reflect the latest workflow result on `main`.

| Monitor | Scope | Schedule | Workflow |
|---|---|---:|---|
| Smoke | Sign in, confirm dashboard, sign out | Every 10 minutes | [`Smoke Monitor (v2)`](https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/smoke.yml) |
| Regression | Synthetic consultation, WebM API upload, transcription, clinical note, approval, feedback, dashboard verification | Hourly | [`Consultation Regression (v2)`](https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/regression.yml) |
| FNX | FNX parsing, patient summary, factual validation, and contextual AI chat | Every 2 hours at minute 15 UTC | [`FNX Parser and AI (v2)`](https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/fnx.yml) |
| Dashboard | Rebuild data, collect latest evidence, deploy GitHub Pages | After monitor completion and four times per hour | [`Monitoring Dashboard (v2)`](https://github.com/FRAIA-AI/Test_Automation_v2/actions/workflows/dashboard.yml) |

GitHub scheduled workflows use UTC and may start several minutes late during periods of high platform load.

---

## Diarization & clinical-note benchmark

The active v2 benchmark runs **three Danish consultation audio fixtures** in separate synthetic consultation sessions: one doctor/patient case, one case with a patient relative, and one case with a nurse. The original 25-case corpus remains available in `test_data/diarization` for regression comparison.

People's Clinic intentionally has only two output speaker buckets:

| Original speaker | Expected platform bucket |
|---|---|
| Doctor | **Læge / Doctor** |
| Patient, parent, child, relative, or other non-doctor | **Patient** |

The product still exposes only two buckets. The evaluator therefore checks doctor speech against **Læge / Doctor** and routes every other source role to **Patient**; it does not require identity-level separation between additional speakers.

Each audio fixture has a matching JSON oracle. The benchmark collects the platform's diarized transcription and generated clinical note, then uses structured AI evaluation against that oracle. Deterministic code calculates the final scores and quality gates.

| Layer | What is measured |
|---|---|
| Diarized transcription | Content retention, doctor attribution, patient-side attribution, overall attribution, transcription integrity, and turn counts |
| Generated clinical note | Clinical fact retention, note fidelity, clinical hallucination integrity, missing facts, and unsupported facts |

Run a fast one-case v2 pipeline check:

```bash
DIARIZATION_CASES_DIR=test_data/diarization_v2 DIARIZATION_CASE_LIMIT=1 pytest tests/diarization/test_diarization_batch.py -v
```

Run all three v2 cases:

```bash
DIARIZATION_CASES_DIR=test_data/diarization_v2 DIARIZATION_CASE_LIMIT=3 pytest tests/diarization/test_diarization_batch.py -v
```

The workflow then evaluates all collected transcripts and generated notes with the same structured AI scoring, deterministic formulas, quality gates, evidence upload, dashboard ingestion, and alerting used by the earlier suite. See the [live dashboard guide](https://fraia-ai.github.io/Test_Automation_v2/guide.html) for score definitions, formulas, thresholds, reports, and troubleshooting guidance.

The diarization benchmark requires at least 92% for each transcription/diarization aggregate and 90% for each generated clinical-note aggregate. Any lower score fails the quality gate and sends an email for that run; the benchmark does not suppress repeated failed-run emails.

Diarization failure emails are delivered only from 06:00 (inclusive) until 18:00 (exclusive) Central European local time, with daylight-saving changes handled through `Europe/Berlin`. Each email links to the live diarization dashboard and GitHub run, and attaches the complete evaluation summary and text report when available, followed by screenshots and the latest video within the attachment limit.

---

## Test suite

```text
tests/smoke/test_login_logout.py
  Sign in -> dashboard verification -> sign out

tests/regression/test_consultation.py
  Sign in -> optional mic check -> synthetic patient -> live consultation
  -> WebM API upload -> processed transcription -> generated note
  -> approve -> feedback -> dashboard verification

tests/fnx/test_fnx_parser.py
  FNX upload -> deterministic CPR and patient-name validation

tests/fnx/test_fnx_ai.py
  FNX analytics upload -> factual summary -> question -> contextual follow-up
```

The parser and AI journeys are intentionally separate. Parser behavior is deterministic; LLM output is validated with flexible factual anchors and forbidden-response checks.

Authentication retries exactly once only when the application reports `LOGIN_PROCESSING_FAILED`. The retry uses a completely fresh browser context. Other failures are not retried automatically.

---

## Architecture

```text
Smoke workflow ────────┐
Regression workflow ───┼── pytest + Playwright
FNX workflow ──────────┘          │
                                  ├── stage screenshots
                                  ├── failure screenshot
                                  ├── WebM video on failure
                                  ├── Playwright trace on failure
                                  ├── JUnit XML
                                  └── concise SMTP alert
                                           │
                                           ▼
                              GitHub Actions artifacts
                                           │
                                           ▼
                         One dashboard build/deploy workflow
                                           │
                                           ▼
                                  GitHub Pages dashboard
```

Only the dashboard workflow deploys GitHub Pages. Smoke, Regression, and FNX never push to `gh-pages`, preventing competing deployments and race conditions.

---

## Repository layout

```text
.github/workflows/
  smoke.yml
  regression.yml
  fnx.yml
  dashboard.yml
  test-alarm-email.yml

dashboard/
  index.html
  favicon.png
  bg-music.mp3

scripts/
  send_alert.py
  test_alarm_email.py
  build_dashboard_data.py
  prepare_dashboard_assets.py
  postprocess_dashboard.py

test_data/
  consultation-audio.webm
  consultation-audio.oracle.json
  2024-12-14_CGM_P300_1_Ref.FNX
  fnx.oracle.json

tests/
  conftest.py
  helpers/
  pages/
  smoke/
  regression/
  fnx/
```

---

## Local setup

### WSL or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install --with-deps chromium
cp .env.example .env
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
```

Pinned dependencies:

```text
pytest==8.3.5
pytest-playwright==0.7.0
python-dotenv==1.0.1
```

---

## Environment configuration

Configure `.env` for local runs:

```dotenv
BASE_APP_URL=https://clinic.peoplesdoctor.ai

TEST_USERNAME=smoke-monitor@example.invalid
TEST_PASSWORD=replace-me

ADMIN_USERNAME=deep-monitor@example.invalid
ADMIN_PASSWORD=replace-me

AUTH_COOKIE_NAME=pc-accessToken
```

Never commit `.env`, credentials, SMTP keys, production cookies, or sensitive evidence.

### Required GitHub Actions secrets

```text
TEST_USERNAME
TEST_PASSWORD
ADMIN_USERNAME
ADMIN_PASSWORD
AUTH_COOKIE_NAME
MAIL_SERVER_ADDRESS
MAIL_SERVER_PORT
MAIL_USERNAME
MAIL_PASSWORD
MAIL_SENDER_ADDRESS
MAIL_RECIPIENT_ADDRESS
```

Example Brevo SMTP configuration:

```text
MAIL_SERVER_ADDRESS = smtp-relay.brevo.com
MAIL_SERVER_PORT = 587
MAIL_USERNAME = Brevo SMTP login
MAIL_PASSWORD = active Brevo SMTP key
MAIL_SENDER_ADDRESS = sender verified in Brevo
MAIL_RECIPIENT_ADDRESS = alert recipient
```

Enter values without surrounding quotation marks.

---

## Required fixtures

```text
test_data/consultation-audio.webm
test_data/consultation-audio.oracle.json
test_data/2024-12-14_CGM_P300_1_Ref.FNX
test_data/fnx.oracle.json
```

The consultation oracle must contain stable words actually spoken in the WebM fixture. This prevents an accepted-but-unprocessed upload from being treated as successful.

The FNX oracle contains stable patient fields, summary anchors, chat expectations, and forbidden fallback phrases.

---

## Running tests locally

Collect without executing production journeys:

```bash
pytest --collect-only -q
```

Run individual monitors:

```bash
pytest tests/smoke/test_login_logout.py -v
pytest tests/regression/test_consultation.py -v
pytest tests/fnx/test_fnx_parser.py -v
pytest tests/fnx/test_fnx_ai.py -v
```

Run all tests:

```bash
pytest -v
```

Useful markers:

```bash
pytest -m smoke -v
pytest -m regression -v
pytest -m fnx -v
pytest -m "fnx and not ai" -v
pytest -m ai -v
```

Run with JUnit output:

```bash
mkdir -p results
pytest tests/regression/test_consultation.py \
  -v \
  --junitxml=results/regression-junit.xml
```

---

## Evidence capture

Expected evidence directories:

```text
test-results/stage-screenshots/
test-results/failure-screenshots/
test-results/videos/
test-results/traces/
```

The shared fixture records a browser-page video and Playwright trace while the test runs. Failure evidence is retained; unnecessary successful-run videos are removed automatically.

Videos capture only the Chromium page. They do not capture the desktop, terminal, unrelated applications, or microphone audio from the host computer.

Open a trace locally:

```bash
playwright show-trace test-results/traces/<trace-name>.zip
```

GitHub Actions uploads evidence, captured console output, and JUnit XML as an artifact retained for 14 days.

---

## Alert behavior

Each monitor maintains independent incident state in GitHub Actions cache.

```text
First failure during the alert window    -> failure email
Failure after the reminder cooldown      -> reminder email
Repeated failure before cooldown         -> no duplicate email
First success after a notified failure   -> recovery email
Healthy run with no open incident        -> no routine email
```

Default failure-notification window:

```text
04:00 UTC inclusive -> 17:00 UTC exclusive
```

Failure and reminder emails can contain:

- monitor and test name;
- inferred failure phase;
- exception type;
- concise main error;
- `main-error.txt`;
- stage and failure screenshots;
- the newest WebM recording that fits the attachment allowance;
- a direct GitHub Actions run link.

The default combined email attachment allowance is `20 MB`. Files omitted from email remain available in the GitHub Actions artifact.

### Safe alarm-delivery test

Use the manual workflow when available:

```text
Actions -> Test Alarm Email Delivery -> Run workflow
```

It creates clearly labelled synthetic screenshots, a short WebM video, a fake JUnit failure, sends the real multipart email, and uploads the same evidence as an artifact. It does not invalidate credentials or create a real production incident.

---

## Dashboard features

- current Smoke, Regression, and FNX status cards;
- overall health and stale-monitor detection;
- last completion time, duration, trigger, and run number;
- concise failure context;
- direct workflow and run links;
- selectable history windows;
- run-count, success-rate, and duration chart modes;
- 3D reliability visualization;
- workflow history table;
- screenshot gallery and WebM player;
- evidence modal;
- JSON export;
- dark and light themes;
- responsive layout;
- animated background;
- optional ambient music;
- five-minute client-side refresh.

The dashboard logo links directly to the People's Clinic platform.

### GitHub Pages setup

Under **Settings -> Pages**, choose:

```text
Source: GitHub Actions
```

Do not choose **Deploy from a branch**. This project deliberately uses one Pages deployment workflow and no shared `gh-pages` publishing branch.

After deployment, hard-refresh when validating UI updates:

```text
Windows/Linux: Ctrl + Shift + R
macOS: Command + Shift + R
```

---

## Troubleshooting

### A scheduled workflow does not start

Confirm that:

1. the YAML is committed to the default branch;
2. the workflow is enabled under **Actions**;
3. the `schedule` block is active;
4. the cron expression is valid and uses UTC;
5. organization policy allows GitHub Actions;
6. the expected run is labelled `schedule` rather than `workflow_dispatch`.

### No failure email arrives

Check the relevant `Process ... email alerts` step and verify all SMTP secrets, the verified sender, notification window, reminder cooldown, recipient spam filtering, and provider attachment limits.

### A healthy run sends no email

That is expected. Healthy runs do not send routine success messages. A success email is used only to close a previously notified incident.

### Dashboard remains on “Loading”

Confirm the dashboard workflow generated:

```text
public/index.html
public/data/dashboard.json
```

Then confirm the deploy job succeeded and verify that `data/dashboard.json` returns HTTP 200 in browser developer tools.

### Dashboard assets do not appear

The workflow expects:

```text
dashboard/favicon.png
dashboard/bg-music.mp3
```

The preparation script copies them into the GitHub Pages artifact.

### No screenshots or video in an email

Confirm evidence existed before the alert step. The video is finalized only after the Playwright browser context closes. Large files may be omitted from email while remaining in the artifact.

---

## Security and data-handling rules

- Never use real patient identities, CPR numbers, consultation audio, or medical records.
- Never print credentials, cookies, bearer tokens, or SMTP keys.
- Keep `.env` out of version control.
- Review screenshots, videos, traces, and artifacts before external sharing.
- Use least-privilege GitHub permissions.
- Keep monitor alert state and concurrency independent.
- Treat production fixture changes as controlled changes requiring review.

---

## Maintenance checklist

When the application changes:

1. run the affected monitor manually;
2. inspect stage screenshots and trace;
3. update page objects rather than duplicating selectors;
4. update oracle terms only with verified fixture content;
5. test alarm delivery after changing evidence or SMTP code;
6. run the dashboard workflow and verify the deployed JSON and UI;
7. update this README when behavior changes materially.

## License and ownership

This repository is an internal production-monitoring project for the People's Clinic/FRAIA team. Add the organization's approved license and contribution policy before distributing it outside the authorized environment.
