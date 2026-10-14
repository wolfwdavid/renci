# Testing Patterns

**Analysis Date:** 2026-10-14

## Verified Test Run (2026-10-14)

Run in a fresh venv (Python 3.13.7) from `apps/api/` with `pip install -r requirements.txt pytest pytest-asyncio`:

| Setup | Result |
|-------|--------|
| `requirements.txt` + `pytest` + `pytest-asyncio` (as declared) | **2 failed, 38 passed** |
| Same, but without `pytest-asyncio` (`-p no:asyncio`) | **12 failed, 28 passed** (all `async def` tests fail: "async def functions are not natively supported") |
| Same, plus `python-multipart` | **40 passed** |

- The 2 failures are `tests/test_webhook.py::test_sms_webhook_new_user` and `tests/test_webhook.py::test_sms_webhook_returns_twiml`: `AssertionError: The python-multipart library must be installed to use form parsing.` `apps/api/routes/webhooks.py:12` calls `await request.form()`, and `python-multipart` is not listed in `apps/api/requirements.txt` (plain `fastapi` does not pull it in). This affects the production Twilio webhook too, not just tests.
- `pytest-asyncio` is also not listed in `apps/api/requirements.txt`; 12 tests depend on it.
- Test counts: `tasks/todo.md` says "29/29 tests passing" (stale, predates the Gemini migration and PPP/photo tests); `README.md` says "Expected: 40 tests passing". There are 40 test functions.
- The Claude-to-Gemini migration did not break the suite: no test imports `anthropic`, and no test calls `agent.core.dispatch` (the Gemini path is untested).
- Windows note: `twilio` installs files with very long paths; installing into a venv under a deep directory fails with `OSError ... Long Path support`. Use a short venv path (or enable Windows long paths).
- Measured line coverage with `pytest-cov` (app modules): `registration.py` 98%, `ppp_data.py` 98%, `language/detector.py` 91%, `sms/twilio_handler.py` 100%, `agent/core.py` 33%, `agent/tools.py` 20%, `db/firestore.py` 28%, `email_channel/*` 0%, `sms/sender.py` 0%, `integrations/storage.py` 0%. Overall (including test files) 57%.

## Test Framework

**Runner:**
- pytest (9.1.1 verified; not pinned anywhere)
- Config: none. No `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `conftest.py` in `apps/api/`. pytest-asyncio runs in its default strict mode, so every async test needs `@pytest.mark.asyncio`.
- Imports resolve because pytest is run from `apps/api/` (rootdir-based `sys.path`) and `apps/api/tests/__init__.py` exists.

**Assertion Library:**
- Plain `assert` statements (pytest assertion rewriting).

**Async / HTTP:**
- `pytest-asyncio` (1.4.0 verified) for `async def` tests.
- `httpx.AsyncClient` + `httpx.ASGITransport` for in-process FastAPI calls (`httpx` is in `requirements.txt`).

**Run Commands:**
```bash
cd apps/api && pip install -r requirements.txt pytest pytest-asyncio python-multipart  # one-time
cd apps/api && python -m pytest tests/ -v      # Run all tests (README command)
npm run test:api                                # Root script: cd apps/api && pytest
cd apps/api && python -m pytest tests/test_ppp.py -v                    # Single file
cd apps/api && python -m pytest --cov=. --cov-report=term               # Coverage (needs pytest-cov)
```
- No watch mode configured.
- Frontend: no test runner. The only check is `cd apps/web && npm run check` (`svelte-check` type checking).

## Test File Organization

**Location:**
- Separate directory: all API tests live in `apps/api/tests/` (flat, no subdirectories). Not co-located with source.
- No frontend tests exist under `apps/web/`.

**Naming:**
- Files: `test_<area>.py`. Mostly named after the module under test (`test_firestore.py`, `test_ppp.py`, `test_photo.py`, `test_registration.py`), but loosely: `test_agent.py` actually tests `language/detector.py` and `agent/prompts/templates.py`; `test_sms_router.py` tests `sms/twilio_handler.parse_incoming_sms`, not `sms/router.route_message`; `test_webhook.py` also covers `/health`.
- Functions: `test_<subject>_<scenario>` (`test_lookup_ppp_invalid_zip`, `test_address_confirm_no`, `test_slugify_special_chars`).

**Structure:**
```
apps/api/tests/
├── __init__.py              # empty; makes tests a package
├── test_agent.py            # 8 tests: detect_language, is_traditional_chinese, help/status templates
├── test_firestore.py        # 5 tests: slugify only (pure function)
├── test_photo.py            # 2 tests: extract_menu_from_photo
├── test_ppp.py              # 9 tests: PPP tools against real CSV in apps/api/data/
├── test_registration.py     # 9 async tests: each registration step with mocked Firestore
├── test_sms_router.py       # 4 tests: parse_incoming_sms
└── test_webhook.py          # 3 async tests: /health and /webhooks/sms via ASGI transport
```

## Test Structure

**Suite Organization:**
- Module-level test functions only; no test classes, no fixtures, no `conftest.py`.
- Each file starts with a one-line module docstring (`"""Tests for PPP loan data tools."""`).
- Async tests carry a one-line docstring describing the behavior being verified.

```python
"""Tests for the multi-step SMS registration flow."""

import pytest
from unittest.mock import AsyncMock, patch
from sms.twilio_handler import IncomingSMS
from agent.actions.registration import handle_registration


def _make_sms(body: str, from_number: str = "+12125551234") -> IncomingSMS:
    return IncomingSMS(
        from_number=from_number,
        body=body,
        media_urls=[],
        num_media=0,
    )


@pytest.mark.asyncio
async def test_type_step_invalid_input():
    """Invalid type selection gets re-prompted."""
    owner = {
        "id": "o1",
        "phone": "+12125551234",
        "registration_step": "type",
        "registration_data": {"name": "Wong's Bakery"},
    }
    with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner):
        result = await handle_registration(_make_sms("banana"))
    assert "1-7" in result
```
(from `apps/api/tests/test_registration.py`)

**Patterns:**
- Setup: inline dict literals for owner/business state per test; small `_make_<thing>()` private helper for repeated constructors.
- Teardown: none needed; mocks are scoped with `with patch(...)` context managers.
- Assertions: substring checks on reply text, often accepting either language (`assert "email" in result.lower() or "电邮" in result`). Dict-returning tools are checked by key (`result["status"] == "success"`, `"%" in result["forgiveness_rate"]`).
- Pure functions (detector, slugify, templates, parser, PPP tools) are tested directly with no mocking.

## Mocking

**Framework:** `unittest.mock` (`patch`, `AsyncMock`). No `pytest-mock`.

**Patterns:**
```python
# Patch async Firestore helpers where they are looked up (the importing module)
with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner), \
     patch("agent.actions.registration.create_business", new_callable=AsyncMock, return_value="biz123"), \
     patch("agent.actions.registration.update_owner", new_callable=AsyncMock):
    result = await handle_registration(_make_sms("wong@gmail.com"))
```
(`apps/api/tests/test_registration.py`)

```python
# Patch the router function seen by the FastAPI route, then call the app in-process
with patch("routes.webhooks.route_message", new_callable=AsyncMock, return_value="Welcome to Renci!"):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/webhooks/sms", data={"From": "+12125551234", "Body": "Hi", "NumMedia": "0"})
assert resp.status_code == 200
assert "<Message>" in resp.text
```
(`apps/api/tests/test_webhook.py`)

**What to Mock:**
- Firestore access (`db.firestore` functions) — always patch at the consumer module path, e.g. `agent.actions.registration.update_owner`, `agent.tools.get_business`, `sms.router.get_owner_by_phone`.
- The SMS router when testing HTTP routes (`routes.webhooks.route_message`).
- External network services in any new test: Gemini (`agent.core._get_client` or `genai.Client`), Twilio (`sms.sender.get_twilio_client`, `agent.actions.photo.download_twilio_media`), Gmail IMAP/SMTP (`email_channel.receiver.connect_imap`, `email_channel.handler.send_email_reply`), GCS (`integrations.storage.get_storage_client`).
- Use `new_callable=AsyncMock` for any `async def` target.

**What NOT to Mock:**
- Pure helpers: `detect_language`, `slugify`, template builders, `parse_incoming_sms`, `is_sms_gateway_email`, `extract_phone_from_gateway`.
- The PPP dataset: `apps/api/tests/test_ppp.py` reads the real committed CSV `apps/api/data/ppp_loans_chinatown.csv` (cached in module global `_df`). Keep tests tied to known zips `10013` / `10002` and use `99999` for the empty case.
- `main.app` itself — import it and drive it through `ASGITransport`. Importing `main` is safe in tests because the email poller only starts when `RENCI_EMAIL` and `RENCI_EMAIL_APP_PASSWORD` are set, and `ASGITransport` does not run lifespan.

## Fixtures and Factories

**Test Data:**
```python
owner = {
    "id": "o1",
    "phone": "+12125551234",
    "registration_step": "email",
    "registration_data": {"name": "Wong's Bakery", "business_type": "bakery", "address": "65 Mott St, New York, NY"},
}
```
- Canonical sample business is "Wong's Bakery" / "黄记饼家", slug `wongs-bakery`, phone `+12125551234` / `212-555-1234`, email `wong@gmail.com`, address `65 Mott St`. Reuse these values for consistency with existing tests and the landing-page demo in `apps/web/src/routes/+page.svelte`.

**Location:**
- Inline in each test function; one helper `_make_sms()` in `apps/api/tests/test_registration.py`. No shared fixtures file. If a fixture is needed across files, create `apps/api/tests/conftest.py`.
- Static data fixture: `apps/api/data/ppp_loans_chinatown.csv` (production data, also used by tests).

## Coverage

**Requirements:** None enforced. No coverage config, `pytest-cov` not in requirements, and `infra/cloudbuild.yaml` has no test step (images build and deploy without running tests). `.gitignore` already ignores `.coverage`, `htmlcov/`, `.pytest_cache/`.

**View Coverage:**
```bash
cd apps/api && pip install pytest-cov && python -m pytest --cov=. --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Pure-function tests: language detection, slugify, response templates, Twilio form parsing, PPP pandas queries, photo tool stub.
- State-machine tests: each step of `handle_registration` with Firestore mocked (`apps/api/tests/test_registration.py`), covering valid and invalid input per step.

**Integration Tests:**
- In-process HTTP tests via `httpx.ASGITransport` for `/health` and `/webhooks/sms` (TwiML shape and content-type) in `apps/api/tests/test_webhook.py`, with the router mocked.
- No tests against real Firestore, Gemini, Twilio, Gmail, or GCS; no emulator setup.

**E2E Tests:**
- Not used. No Playwright/Vitest in `apps/web/`. The "SMS round-trip" and "Registration E2E" items in `tasks/todo.md` refer to the mocked pytest tests above.

**Untested areas (add tests here first):**
- `apps/api/agent/core.py` `dispatch()` (Gemini call, MMS handling, fallback to help).
- `apps/api/agent/tools.py` tool functions and `apps/api/agent/actions/profile.py`.
- `apps/api/sms/router.py` `route_message()` branching (new / mid-registration / registered owner).
- `apps/api/email_channel/` (handler gateway filtering, poller, receiver, sender).
- `apps/api/routes/api.py` `/api/v1/businesses/{slug}` (200 and 404), `/webhooks/email`, `/agent/status`, `/agent/toggle`.
- All of `apps/web/`.

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_health_endpoint():
    """Health endpoint returns healthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
```
(`apps/api/tests/test_webhook.py`)

**Error / Invalid-Input Testing:**
- The codebase returns error strings/dicts instead of raising, so "error" tests assert on the returned message rather than using `pytest.raises`:
```python
def test_forgiveness_invalid_zip():
    result = check_ppp_forgiveness("99999")
    assert "No PPP data" in result["message"]
```
(`apps/api/tests/test_ppp.py`)
```python
with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner):
    result = await handle_registration(_make_sms("notanemail"))
assert "valid email" in result.lower() or "有效的电邮" in result
```
(`apps/api/tests/test_registration.py`)
- `pytest.raises` is not used anywhere; use it only for code that genuinely raises (e.g. `HTTPException`, `NotImplementedError` in `apps/api/assistant/core.py`).

**Bilingual Assertions:**
- Test both `"en"` and `"zh"` branches for any new template/tool (`test_help_response_english` / `test_help_response_chinese` in `apps/api/tests/test_agent.py`).

---

*Testing analysis: 2026-10-14*
