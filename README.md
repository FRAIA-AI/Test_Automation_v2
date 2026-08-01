# People's Clinic Monitoring v2

Production synthetic monitoring for the People's Clinic platform using **Python 3.12**, **pytest**, **Playwright**, GitHub Actions, SMTP incident alerts, retained test evidence, and a single GitHub Pages operations dashboard.

> **Production caution**
>
> The deep monitors create synthetic activity in the production application. Use only approved automation accounts, synthetic patient identifiers, and approved fixture files. Never use real patient data.

## Live services

- **Platform:** <https://clinic.peoplesdoctor.ai/>
- **Monitoring dashboard:** <https://fraia-ai.github.io/Test_Automation_v2/>
- **Repository:** `FRAIA-AI/Test_Automation_v2`

## What is monitored

| Monitor | Scope | Schedule | Workflow |
|---|---|---:|---|
| Smoke | Sign in, confirm dashboard, sign out | Every 10 minutes | `Smoke Monitor (v2)` |
| Regression | Sign in, microphone prerequisite, synthetic consultation, API audio upload, processed transcription, generated note, approval, feedback, dashboard verification | Hourly | `Consultation Regression (v2)` |
| FNX | FNX parser validation plus analytics summary and multi-turn AI chat | Every 2 hours at minute 15 UTC | `FNX Parser and AI (v2)` |
| Dashboard | Rebuild data, collect latest evidence, and deploy GitHub Pages | After monitor completion and four times per hour | `Monitoring Dashboard (v2)` |

GitHub scheduled workflows use UTC and may occasionally start several minutes late.

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

The FNX parser and AI journeys are intentionally separate. Parser behavior is deterministic; LLM output is validated through flexible factual anchors and forbidden-response checks.

Authentication retries exactly once only when the application explicitly reports `LOGIN_PROCESSING_FAILED`. The retry uses a fresh browser context. Other failures are not automatically retried.

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

Only the dedicated dashboard workflow deploys GitHub Pages. The three monitor workflows never push to `gh-pages`, preventing concurrent deployment conflicts.

## Repository layout

```text
.github/workflows/
  smoke.yml
  regression.yml
  fnx.yml
  dashboard.yml
  test-alarm-email.yml          # when present: manual evidence-delivery test

dashboard/
  index.html
  favicon.png
  bg-music.mp3

scripts/
  send_alert.py
  test_alarm_email.py           # synthetic alarm evidence generator
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

requirements.txt
pytest.ini
.env.example
README.md
```

Some optional files may be absent on branches that have not yet received the related workflow.

## Local setup

### WSL/Linux

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

The pinned Python dependencies are:

```text
pytest==8.3.5
pytest-playwright==0.7.0
python-dotenv==1.0.1
```

## Environment configuration

Configure `.env` for local runs:

```dotenv
BASE_APP_URL=https://clinic.peoplesdoctor.ai

TEST_USERNAME=smoke-monitor@example.invalid
TEST_PASSWORD=replace-me

ADMIN_USERNAME=deep-monitor@example.invalid
ADMIN_PASSWORD=replace-me

# People's Clinic bearer-token cookie used by the API-assisted regression flow.
AUTH_COOKIE_NAME=pc-accessToken
```

Never commit `.env`, credentials, SMTP keys, production cookies, or downloaded evidence containing sensitive information.

## Required fixture files

```text
test_data/consultation-audio.webm
test_data/consultation-audio.oracle.json
test_data/2024-12-14_CGM_P300_1_Ref.FNX
test_data/fnx.oracle.json
```

The consultation oracle must contain stable words actually spoken in the WebM fixture. This prevents an accepted-but-unprocessed upload from being treated as a successful consultation.

The FNX oracle should contain stable patient fields, summary anchors, chat-turn expectations, and forbidden fallback phrases.

## Running tests locally

Collect tests without executing production journeys:

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

Run with a JUnit report:

```bash
mkdir -p results
pytest tests/regression/test_consultation.py \
  -v \
  --junitxml=results/regression-junit.xml
```

## Evidence capture

The shared browser fixture records a complete browser-page video and Playwright trace while the test runs. It then retains failure evidence and removes unnecessary successful-run video files.

Expected directories:

```text
test-results/stage-screenshots/
test-results/failure-screenshots/
test-results/videos/
test-results/traces/
```

Stage screenshots are named by business step so a failure can be understood without reading the full console output.

Videos capture only the Chromium page. They do not capture the desktop, terminal, unrelated applications, or microphone audio from the host computer.

Open a trace locally:

```bash
playwright show-trace test-results/traces/<trace-name>.zip
```

GitHub Actions uploads the evidence, console output, and JUnit XML as a retained artifact for 14 days.

## GitHub repository secrets

Configure under **Settings -> Secrets and variables -> Actions**.

### Test credentials

```text
TEST_USERNAME
TEST_PASSWORD
ADMIN_USERNAME
ADMIN_PASSWORD
AUTH_COOKIE_NAME
```

`AUTH_COOKIE_NAME` is expected by Regression and FNX workflows. Use `pc-accessToken` unless the application cookie name has changed.

### SMTP alerts

```text
MAIL_SERVER_ADDRESS
MAIL_SERVER_PORT
MAIL_USERNAME
MAIL_PASSWORD
MAIL_SENDER_ADDRESS
MAIL_RECIPIENT_ADDRESS
```

Example Brevo configuration:

```text
MAIL_SERVER_ADDRESS = smtp-relay.brevo.com
MAIL_SERVER_PORT = 587
MAIL_USERNAME = Brevo SMTP login
MAIL_PASSWORD = active Brevo SMTP key
MAIL_SENDER_ADDRESS = sender verified in Brevo
MAIL_RECIPIENT_ADDRESS = alert recipient
```

Enter values without surrounding quotation marks.

## Alert behavior

Each monitor maintains independent incident state in the GitHub Actions cache.

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

A recovery message can be sent after the incident so the alert lifecycle is closed clearly.

Failure and reminder emails contain:

- monitor and test name;
- inferred failure phase;
- exception type;
- concise main error rather than the complete pytest log;
- `main-error.txt`;
- available stage and failure screenshots;
- the newest WebM recording that fits the configured attachment limit;
- a direct GitHub Actions run link for full logs, traces, and artifacts.

The default combined attachment allowance in the workflows is `20 MB`. Files that exceed the allowance remain in the GitHub Actions artifact.

## Testing alarm delivery safely

Use the dedicated manual workflow when available:

```text
Actions -> Test Alarm Email Delivery -> Run workflow
```

The synthetic alarm test:

1. opens the sign-in page;
2. creates clearly labelled synthetic screenshots;
3. records a short WebM video;
4. generates a fake JUnit failure;
5. sends the real multipart alert email;
6. uploads the same evidence as a GitHub artifact.

It does not invalidate credentials, create a real production incident, or submit synthetic patient data.

A successful workflow log should include messages similar to:

```text
Attached evidence files: main-error.txt, ...png, ...webm
Sent failure email for Peoples Clinic Alarm Delivery Test.
```

SMTP acceptance confirms that the server accepted the message. Final inbox placement still depends on the recipient provider, spam filtering, and attachment-size policies.

## GitHub Actions workflows

### Smoke

```text
File: .github/workflows/smoke.yml
Name: Smoke Monitor (v2)
Cron: */10 * * * *
Timeout: 10 minutes
Concurrency: cancels an older unfinished Smoke run
```

### Regression

```text
File: .github/workflows/regression.yml
Name: Consultation Regression (v2)
Cron: 0 * * * *
Timeout: 15 minutes
Concurrency: does not cancel an active regression journey
```

### FNX

```text
File: .github/workflows/fnx.yml
Name: FNX Parser and AI (v2)
Cron: 15 */2 * * *
Timeout: 20 minutes
Concurrency: does not cancel an active FNX journey
```

### Dashboard

```text
File: .github/workflows/dashboard.yml
Name: Monitoring Dashboard (v2)
Cron: 7,22,37,52 * * * *
Additional trigger: completion of Smoke, Regression, or FNX
```

The dashboard workflow:

1. checks out `main`;
2. prepares HTML and static assets;
3. queries GitHub Actions history;
4. downloads and extracts the latest monitor artifacts;
5. creates `public/data/dashboard.json`;
6. applies final dashboard UI upgrades;
7. uploads one GitHub Pages artifact;
8. deploys through `actions/deploy-pages`.

## Monitoring dashboard

The dashboard includes:

- current Smoke, Regression, and FNX status cards;
- stale-monitor detection;
- last completion time, duration, trigger, and run number;
- concise failure context;
- direct workflow and run links;
- selectable history windows;
- run-count, success-rate, and duration chart modes;
- 3D reliability visualization;
- workflow history table;
- screenshot gallery and video player;
- evidence modal;
- JSON export;
- dark and light themes;
- responsive layout;
- animated background;
- optional ambient music;
- automatic data refresh.

The dashboard logo links back to the People's Clinic platform.

### GitHub Pages setup

Under **Settings -> Pages**, choose:

```text
Source: GitHub Actions
```

Do not select **Deploy from a branch**. The project deliberately uses a single Pages deployment workflow and does not maintain a shared `gh-pages` publishing branch.

After a dashboard deployment, hard-refresh the browser when validating a UI change:

```text
Windows/Linux: Ctrl + Shift + R
macOS: Command + Shift + R
```

## Selector and validation policy

- Selectors are scoped and support English and Danish labels where required.
- FNX uploads prefer direct `input[type="file"]` interaction instead of localized “Browse Files” buttons.
- Regression success is based on meaningful editor content and oracle validation, not only on a loader disappearing.
- LLM tests use factual anchors and forbidden fallback phrases instead of exact full-text matching.
- Stable application-owned `data-testid` attributes should replace temporary accessible selectors when the application team can add them.

## Troubleshooting

### A scheduled workflow does not start

Confirm:

1. the workflow YAML is committed to the repository's default branch;
2. the workflow is enabled under **Actions**;
3. the `schedule` block is not commented out;
4. the cron expression is valid and uses UTC;
5. organization policy allows GitHub Actions;
6. the run is labelled `schedule`, not `workflow_dispatch`.

GitHub cron is not guaranteed to start at the exact second and can be delayed during high platform load.

### No failure email arrives

Check the `Process ... email alerts` step and verify:

- all SMTP secrets exist;
- the sender is verified;
- the failure occurred inside the configured alert window;
- the incident was not suppressed by the cooldown;
- the recipient provider did not quarantine the message;
- the attachment limit is accepted by the SMTP provider.

### The monitor passed but no email arrived

That is expected. Healthy runs do not send routine success messages. A success email is sent only as recovery after a previously notified incident.

### Dashboard remains on “Loading”

Confirm the dashboard workflow generated:

```text
public/index.html
public/data/dashboard.json
```

Then confirm the deploy job succeeded and hard-refresh the browser. Open browser developer tools and check whether `data/dashboard.json` returns HTTP 200.

### Dashboard assets do not appear

The workflow expects dashboard assets under:

```text
dashboard/favicon.png
dashboard/bg-music.mp3
```

The asset-preparation script copies them into the Pages artifact.

### No screenshots or video in an email

Confirm the test produced files under `test-results/` before the alert step. The video becomes available only after the Playwright browser context closes. Large files may be omitted from email while remaining in the GitHub artifact.

### Trace or video is missing after a successful test

Successful-run videos are intentionally removed to reduce artifact size. Failure traces and videos are retained. Named stage screenshots may still be available depending on the test and workflow.

## Security and data-handling rules

- Never use real patient identities, CPR numbers, consultation audio, or medical records.
- Never print credentials, cookies, bearer tokens, or SMTP keys.
- Keep `.env` out of version control.
- Review screenshots, videos, traces, and artifacts before sharing them outside the authorized team.
- Use least-privilege GitHub permissions.
- Keep each monitor's alert state and concurrency group independent.
- Treat production-monitor fixture changes as controlled changes requiring review.

## Maintenance checklist

When the application changes:

1. run the affected monitor manually;
2. inspect stage screenshots and trace;
3. update page objects rather than duplicating selectors in tests;
4. update oracle terms only with verified fixture content;
5. test the alarm-delivery workflow after changing evidence or SMTP code;
6. run the dashboard workflow and verify the deployed JSON and UI;
7. document material behavior changes in this README.

## License and ownership

This repository is an internal production-monitoring project for the People's Clinic/FRAIA team. Add the organization's approved license and contribution policy before distributing it outside the authorized environment.
