# Copilot Instructions for BlackDiamondHub

## Project Overview

BlackDiamondHub is a Django-based home automation and management hub for a vacation property at Sun Peaks, BC. It runs on Django 5.1 with Python 3.11, uses PostgreSQL for data storage, and integrates with Home Assistant for device control. The app is served via Daphne/Channels (ASGI) to support WebSockets.

## Django Apps

- **inventory** — Property inventory management with item tracking, images, and QR code labels (uses pyzbar for scanning)
- **vacation_mode** — Automates switching between vacation and home modes via Home Assistant REST API (thermostats, water heater, hot tub, TVs, fridge/freezer eco modes). Includes post-action state verification since HA silently drops commands to offline devices
- **sonos_control** — Sonos speaker control with Spotify integration via OAuth (social-auth)
- **cameras** — Live camera feeds via go2rtc + UniFi Protect Integration API
- **sunpeaks_webcams** — Sun Peaks resort webcam viewer
- **snow_report** — Snow/weather report display
- **scenes** — Home Assistant scene control
- **wifi** — WiFi QR code generator with password display
- **feedback** — User feedback submission and admin review (django-tables2)

## Tech Stack

- **Backend**: Django 5.1, Python 3.11, PostgreSQL, Daphne/Channels (ASGI)
- **Frontend**: Bootstrap 5 (crispy-bootstrap5), Font Awesome icons
- **Auth**: Django auth + social-auth-app-django (Spotify OAuth)
- **Home Assistant**: REST API at `192.168.10.212:8123`, token stored in `.env` as `HA_TOKEN`
- **Containerization**: Docker + docker-compose available
- **Environment**: `.env` file for secrets (not committed)

## UniFi Protect Integration API

- **API Docs**: https://developer.ui.com/protect/v6.2.88/get-v1metainfo (sidebar has all endpoints)
- **Auth**: API key via `X-API-KEY` header, key generated at unifi.ui.com → Settings → API Keys
- **Base URL**: `https://{UNIFI_PROTECT_HOST}/proxy/protect/integration/v1`
- **Camera list**: `GET /v1/cameras` — returns id, name, state, featureFlags (note: PTZ flags NOT exposed)
- **RTSPS streams**: `GET /v1/cameras/{id}/rtsps-stream` and `POST /v1/cameras/{id}/rtsps-stream` with `{"qualities": ["high"]}`
- **PTZ endpoints** (for PTZ cameras only, non-PTZ returns 400 "Camera is not a type of PTZ"):
  - `POST /v1/cameras/{id}/ptz/goto/{slot}` — Move to preset (slots 0-4, 204 on success, 404 if preset doesn't exist)
  - `POST /v1/cameras/{id}/ptz/patrol/start/{slot}` — Start patrol
  - `POST /v1/cameras/{id}/ptz/patrol/stop` — Stop patrol
- **go2rtc**: Proxies RTSPS streams to browser via WebRTC/MSE. `video-stream.js` web component (set src/mode/background as JS properties, NOT HTML attributes). Docker image: `alexxit/go2rtc`

## CI/CD

- **GitHub Actions** workflow in `.github/workflows/tests.yml`
- Two jobs: `unit-tests` (excludes selenium tag) and `selenium-tests` (selenium tag only, with retry via nick-fields/retry)
- Both jobs run on `ubuntu-22.04` with PostgreSQL 13 service container
- Selenium tests use headless Chrome with shared helpers in `tests/selenium_helpers.py`

## Branch & Git Workflow

- **All changes must go into a feature branch** — never commit directly to `main`
- **Only I (the user) merge PRs to main** — Copilot should push branches and may suggest creating a PR, but should not merge
- Branch naming: `feature/description`, `fix/description`
- `main` branch has protection rules: require PR, require status checks (unit-tests, selenium-tests), no force push, no deletion

## Testing

- Run unit tests: `venv\Scripts\python.exe manage.py test --exclude-tag=selenium --verbosity 2`
- Run vacation_mode tests only: `venv\Scripts\python.exe manage.py test vacation_mode --verbosity 2`
- Run all tests: `$env:PGPASSWORD='postgres'; venv\Scripts\python.exe manage.py test --verbosity 2`
- Selenium tests extend `StaticLiveServerTestCase` and use shared `get_chrome_options()` from `tests/selenium_helpers.py`
- Always run relevant tests after making changes

## Communication Preferences

- **Do NOT use the ask_questions tool with selectable options** — if you have questions, just ask them directly in the chat as plain text
- Keep explanations concise and direct
- When making changes, implement them rather than just suggesting

## Key Files

- `BlackDiamondHub/settings.py` — Django settings, installed apps, database config
- `BlackDiamondHub/urls.py` — URL routing for all apps
- `vacation_mode/executor.py` — HA service call execution engine with state verification
- `vacation_mode/steps.py` — Step definitions for vacation and home mode sequences
- `cameras/protect_api.py` — UniFi Protect API client (camera discovery, RTSPS streams, PTZ control)
- `cameras/views.py` — Camera feed views, go2rtc stream registration
- `tests/selenium_helpers.py` — Shared Selenium test utilities (login, Chrome options, network waits)
- `.env` — Environment variables (HA_TOKEN, DB credentials, etc.)
- `requirements.txt` — Python dependencies
