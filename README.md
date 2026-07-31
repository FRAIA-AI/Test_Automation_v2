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
```

Each workflow uses Python 3.12, has a timeout and its own concurrency group, and uploads failure evidence for 14 days. They do not push to `gh-pages`, deploy a dashboard, or compete for a shared branch.

Scheduled triggers are initially commented out. Configure the repository secrets, run each workflow manually, and then enable the three schedules.

Required repository secrets:

```text
TEST_USERNAME
TEST_PASSWORD
ADMIN_USERNAME
ADMIN_PASSWORD
```

`AUTH_COOKIE_NAME` defaults safely to `pc-accessToken`; add it as a secret if the application later renames that cookie.

## Selector and validation policy

Selectors are scoped and bilingual English/Danish. Direct file inputs are used instead of clicking localized “Browse Files” controls, eliminating the previous disabled-button and overlay failure.

When application changes are possible, stable `data-testid` attributes should eventually replace the temporary accessible selectors.

The next phase after local stabilization is structured result publication and a single dashboard-deployment workflow. That work should begin only after all four local journeys are verified.
