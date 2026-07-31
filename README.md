# Peoples Clinic Monitoring v2

This is a clean rebuild of the production monitor. It remains independent of the current working project and does not deploy a dashboard.

## Test suite

Pytest collects four tests:

```text
tests/smoke/test_login_logout.py
  Login -> dashboard -> logout

tests/regression/test_consultation.py
  Login -> mic check -> patient -> live consultation -> WebM API
  -> verified transcription -> valid note -> save -> feedback -> dashboard

tests/fnx/test_fnx_parser.py
  FNX upload -> known CPR and patient-name parsing

tests/fnx/test_fnx_ai.py
  FNX analytics upload -> summary facts -> question -> contextual follow-up
```

The FNX parser and AI tests are deliberately separate because parsing is deterministic while LLM output is validated with flexible factual anchors.

`LOGIN_PROCESSING_FAILED` receives one controlled retry in a completely fresh browser context. Other failures are not retried.

## Local setup in WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install --with-deps chromium
cp .env.example .env
```

Configure `.env`:

```dotenv
BASE_APP_URL=https://clinic.peoplesdoctor.ai
TEST_USERNAME=smoke-monitor@example.invalid
TEST_PASSWORD=replace-me
ADMIN_USERNAME=deep-monitor@example.invalid
ADMIN_PASSWORD=replace-me

# Peoples Clinic bearer-token cookie.
AUTH_COOKIE_NAME=pc-accessToken
```

Never commit `.env`.

## Required fixture files

Copy the two existing binary fixtures into v2:

```text
test_data/consultation-audio.webm
test_data/2024-12-14_CGM_P300_1_Ref.FNX
```

See [test_data/README.md](test_data/README.md). Review the two oracle JSON files before running deep tests:

```text
test_data/consultation-audio.oracle.json
test_data/fnx.oracle.json
```

The consultation oracle must contain distinctive words actually spoken in the WebM audio. This prevents an accepted-but-unprocessed audio upload from being mistaken for success.

## Running locally

List the suite without executing production journeys:

```bash
pytest --collect-only -q
```

Run each monitor:

```bash
pytest tests/smoke/test_login_logout.py -v
pytest tests/regression/test_consultation.py -v
pytest tests/fnx/test_fnx_parser.py -v
pytest tests/fnx/test_fnx_ai.py -v
```

Run all four:

```bash
pytest -v
```

Useful marker selections:

```bash
pytest -m smoke -v
pytest -m regression -v
pytest -m fnx -v
pytest -m "fnx and not ai" -v
```

These are production synthetic monitors. The regression test creates and saves a consultation. Run it only with the approved automation account and synthetic fixtures.

## Failure evidence

Failed tests retain:

```text
test-results/screenshots/
test-results/traces/
test-results/videos/
```

Videos record only the Chromium page, not the desktop, terminal, microphone, or other applications. Successful-run videos are removed automatically.

Open a trace:

```bash
playwright show-trace test-results/traces/<trace-name>.zip
```

## GitHub Actions

Three independent workflows are included:

```text
.github/workflows/smoke.yml       intended every 10 minutes
.github/workflows/regression.yml  intended hourly
.github/workflows/fnx.yml         intended every 2 hours at minute 15
.github/workflows/email-alert-test.yml  manual SMTP verification
```

Each workflow uses Python 3.12, has a timeout and its own concurrency group, uploads failure evidence for 14 days, and processes stateful email alerts. They do not push to `gh-pages`, deploy a dashboard, or compete for a shared branch.

Scheduled triggers are initially commented out. Configure the repository secrets, run each workflow manually, and then enable the three schedules.

Required repository secrets:

```text
TEST_USERNAME
TEST_PASSWORD
ADMIN_USERNAME
ADMIN_PASSWORD
MAIL_SERVER_ADDRESS
MAIL_SERVER_PORT
MAIL_USERNAME
MAIL_PASSWORD
MAIL_SENDER_ADDRESS
MAIL_RECIPIENT_ADDRESS
```

`AUTH_COOKIE_NAME` defaults safely to `pc-accessToken`; add it as a secret if the application later renames that cookie.

For Brevo SMTP, use:

```text
MAIL_SERVER_ADDRESS = smtp-relay.brevo.com
MAIL_SERVER_PORT = 587
MAIL_USERNAME = the Brevo SMTP login
MAIL_PASSWORD = the active Brevo SMTP key
MAIL_SENDER_ADDRESS = a sender verified in Brevo
MAIL_RECIPIENT_ADDRESS = the address that should receive alerts
```

Enter secret values without surrounding quote marks. MailSlurp credentials are not used by this alert system.

## Email alert behavior

Each monitor keeps independent incident state in the GitHub Actions cache:

```text
First failure in the notification window -> failure email
Continuing failure after 60 minutes       -> reminder email
Continuing failure before 60 minutes      -> no duplicate email
First successful run after a mailed alert -> recovery email
Healthy run with no open incident         -> no email
```

Failure and reminder emails are sent from 04:00 up to 17:00 UTC (the end is exclusive), matching the previous daytime alert policy. A recovery email may be sent outside that window so an open incident is clearly closed. Emails include the captured pytest output and a direct link to the GitHub Actions run and its artifacts.

If SMTP delivery fails, the workflow reports that configuration/delivery error and leaves the incident eligible for a retry on the next run. SMTP secrets are never printed.

To verify the alarm after adding all six mail secrets, open **Actions → Email Alarm Test (v2) → Run workflow**. It sends a harmless message with the subject `✅ EMAIL TEST`; it does not run a production test or create an incident. Then run each real monitor manually. Do not invalidate production credentials merely to force a failure email.

## Selector and validation policy

Selectors are scoped and bilingual English/Danish. Direct file inputs are used instead of clicking localized “Browse Files” controls, eliminating the previous disabled-button and overlay failure.

When application changes are possible, stable `data-testid` attributes should eventually replace the temporary accessible selectors.

The next phase after local stabilization is structured result publication and a single dashboard-deployment workflow. That work should begin only after all four local journeys are verified.
