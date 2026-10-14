# External Integrations

**Analysis Date:** 2026-10-14

## APIs & External Services

**AI / LLM - Google Gemini:**
- Gemini `gemini-2.5-flash` - Core agent: interprets owner SMS/email (text + MMS images), calls tools, writes reply
  - SDK/Client: `google-genai` (`from google import genai`, `from google.genai import types`) in `apps/api/agent/core.py`
  - Client factory: `_get_client()` in `apps/api/agent/core.py`
    - AI Studio mode (default): sets `os.environ["GOOGLE_API_KEY"]` from settings, then `genai.Client()`
    - Vertex AI mode (`USE_VERTEX_AI=true`): `genai.Client(vertexai=True, project=GCP_PROJECT_ID, location="us-east1")` using ADC
  - Auth: `GOOGLE_API_KEY` (AI Studio) or GCP service account / ADC (Vertex)
  - Call pattern: single synchronous `client.models.generate_content(...)` inside `async def dispatch()` (blocks event loop), `temperature=0.3`, `max_output_tokens=500`, `system_instruction` built by `apps/api/agent/prompts/system.py`
  - Tools: Python callables in `TOOLS` list (`apps/api/agent/core.py`) from `apps/api/agent/tools.py` and `apps/api/agent/actions/` - SDK auto-generates schemas from signatures/docstrings and runs automatic function calling
  - "Google ADK": referenced only in docstrings (`apps/api/agent/core.py`, `apps/api/agent/tools.py`); the `google-adk` package is not a dependency and no ADK `Agent`/`Runner` is used
  - Multimodal: MMS images downloaded and attached as `types.Part.from_bytes(..., mime_type="image/jpeg")` (MIME hardcoded)
  - Client is re-created on every message (no caching)

**Messaging - Twilio (SMS/MMS):**
- Inbound SMS webhook at `POST /webhooks/sms` (`apps/api/routes/webhooks.py`); form payload parsed by `parse_incoming_sms()` in `apps/api/sms/twilio_handler.py` (`From`, `Body`, `NumMedia`, `MediaUrl{i}`)
  - Response returned as inline TwiML `<Response><Message>...</Message></Response>` (reply text is NOT XML-escaped)
  - No Twilio request-signature validation (`X-Twilio-Signature`) is performed
- Outbound SMS: `send_sms()` in `apps/api/sms/sender.py` via `twilio.rest.Client` (sync call in async function)
- MMS media download: `download_twilio_media()` in `apps/api/agent/actions/photo.py` using `httpx.AsyncClient` with basic auth (account SID / auth token)
  - SDK/Client: `twilio>=9.0.0`, `httpx`
  - Auth: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`

**Messaging - Gmail IMAP/SMTP (email-to-SMS gateway channel):**
- Receiver: `apps/api/email_channel/receiver.py` - `imaplib.IMAP4_SSL("imap.gmail.com", timeout=10)`, fetches up to 5 most recent `UNSEEN` messages, marks them `\Seen`, extracts first `text/plain` part
- Sender: `apps/api/email_channel/sender.py` - `smtplib.SMTP_SSL("smtp.gmail.com", 465)`, plain-text reply with `Re:` subject
- Handler: `apps/api/email_channel/handler.py` - only processes senders matching `^\d{10,11}@<carrier gateway>` (`CARRIER_GATEWAYS` set: AT&T, T-Mobile, Verizon, Sprint, MetroPCS, Cricket, Boost); converts to `IncomingSMS` with `+1` phone and routes through `sms.router.route_message` (same pipeline as Twilio)
- Poller: `apps/api/email_channel/poller.py` - background asyncio loop (15 s interval, 15 s initial delay), blocking IMAP in a 1-worker `ThreadPoolExecutor`; module-global `_running` flag
  - Started in FastAPI lifespan (`apps/api/main.py`) only when both `RENCI_EMAIL` and `RENCI_EMAIL_APP_PASSWORD` are set
  - Controllable via `POST /agent/toggle`, `GET /agent/status`, manual `POST /webhooks/email/poll`
  - Auth: `RENCI_EMAIL`, `RENCI_EMAIL_APP_PASSWORD` (Gmail App Password)

**Civic Data - SBA PPP FOIA dataset (static file, no live API):**
- `apps/api/data/ppp_loans_chinatown.csv` (pre-filtered for zips 10002, 10013), loaded lazily into a module-global pandas DataFrame in `apps/api/agent/actions/ppp_data.py`
- Exposed as agent tools: `lookup_ppp_data`, `compare_ppp_by_industry`, `check_ppp_forgiveness`
- Source: https://data.sba.gov/dataset/ppp-foia (per `README.md`)

## Data Storage

**Databases:**
- Google Cloud Firestore (Native mode)
  - Connection: `GCP_PROJECT_ID` (default `renci-491614`), `FIRESTORE_DATABASE` (default `(default)`); credentials via ADC / Cloud Run service account
  - Client: `google.cloud.firestore_v1.AsyncClient`, lazy module-level singleton `get_db()` in `apps/api/db/firestore.py`
  - Collections:
    - `owners` - `phone`, `email`, `business_id`, `language`, `registration_step`, `registration_data`, `created_at` (queried by `phone`)
    - `businesses` - profile fields plus `slug`, `tier` (`free`), `photos`, `social`, `menu_items`, `theme`, `created_at`, `updated_at` (queried by `slug`)
  - All data access goes through functions in `apps/api/db/firestore.py` (`get_owner_by_phone`, `create_owner`, `update_owner`, `create_business`, `get_business`, `get_business_by_slug`, `update_business`)
  - Provisioned by Terraform: `google_firestore_database.default`, `location_id = "nam5"` (`infra/terraform/main.tf`)
  - No composite index definitions or security rules files in the repo
  - Session memory (`apps/api/assistant/memory.py`) is a stub intended to use Firestore later

**File Storage:**
- Google Cloud Storage bucket `renci-assets` (`GCS_BUCKET`)
  - Client: `google.cloud.storage.Client` in `apps/api/integrations/storage.py`; `upload_photo()` writes `{business_slug}/{filename}`, calls `blob.make_public()`, returns public URL
  - `make_public()` conflicts with `uniform_bucket_level_access = true` set in Terraform (object ACLs are disabled under UBLA)
  - Terraform CORS: `origin ["*"]`, `GET` only
  - `upload_photo` is not called from any agent tool currently
- Terraform state bucket: `renci-terraform-state` (GCS backend, prefix `terraform/state`)

**Caching:**
- None (in-process only: PPP DataFrame and Firestore client singletons)

## Authentication & Identity

**Auth Provider:**
- None. Owners are identified solely by phone number (`From` field / carrier-gateway email address) looked up in `owners` collection (`apps/api/sms/router.py`)
  - Registration is a multi-step SMS conversation (`apps/api/agent/actions/registration.py`) tracked via `registration_step`
- API endpoints are fully public: CORS `allow_origins=["*"]` with `allow_credentials=True` (`apps/api/main.py`); Cloud Run deployed with `--allow-unauthenticated` and IAM `allUsers` -> `roles/run.invoker`
- `POST /webhooks/email` accepts arbitrary `from_address` and is used by the public chat widget (`apps/web/src/lib/components/ChatWidget.svelte`), allowing impersonation of any registered phone number
- `POST /agent/toggle` is unauthenticated and called from `apps/web/src/lib/components/AgentToggle.svelte`

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry / Cloud Error Reporting SDK)

**Logs:**
- Python `logging` with `basicConfig(level=INFO)`, loggers `renci` (`apps/api/main.py`) and `renci.email_poller` (`apps/api/email_channel/poller.py`); stdout is collected by Cloud Run / Cloud Logging
- Many failures are silently swallowed (`except Exception: pass` for MMS downloads in `apps/api/agent/core.py`, lifespan shutdown in `apps/api/main.py`)

**Health:**
- `GET /health` returns `{"status": "healthy", "service": "renci-api"}` (`apps/api/routes/health.py`)

## CI/CD & Deployment

**Hosting:**
- Google Cloud Run (managed), two services:
  - `renci-api` - `apps/api/Dockerfile` (`python:3.12-slim`, `uvicorn main:app --host 0.0.0.0 --port $PORT`, default 8080)
  - `renci-web` - `apps/web/Dockerfile` (multi-stage `node:22-slim`, `node build`, port 3000)
- Terraform (`infra/terraform/main.tf`, provider `hashicorp/google ~> 5.0`): `google_cloud_run_v2_service` `api` (container_port 8000, 1 CPU / 512Mi) and `web` (port 3000, 1 CPU / 256Mi), scale 0-10, images tagged `:latest`; default `project_id = "renci-prod"`, `region = "us-east1"`
- Terraform does not set any env vars or secrets on the Cloud Run services, nor a service account
- Configuration drift:
  - Project: `renci-prod` (Terraform) vs `renci-491614` (`apps/api/config.py` default)
  - Region: `us-east1` (Terraform, Cloud Build, Vertex location) vs `us-central1` (README `gcloud run deploy`, hardcoded API URL in web components)
  - Image tags: Cloud Build pushes `:${SHORT_SHA}`; Terraform references `:latest`
  - API port: Terraform 8000 vs Dockerfile/README 8080 (works because Cloud Run injects `PORT`)

**CI Pipeline:**
- Google Cloud Build (`infra/cloudbuild.yaml`): docker build api + web -> push to Artifact Registry `${_REGION}-docker.pkg.dev/${PROJECT_ID}/renci/{api,web}:${SHORT_SHA}` -> `gcloud run deploy renci-api` / `renci-web` with `--allow-unauthenticated`; `_REGION: us-east1`
- No test, lint, or type-check step in the pipeline
- No GitHub Actions workflows detected
- README documents an alternative manual path: `gcloud run deploy ... --source .` (Cloud Build source deploys)

## Environment Configuration

**Required env vars (API, `apps/api/config.py`):**
- `GOOGLE_API_KEY` (or `USE_VERTEX_AI=true` with ADC)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` (SMS channel)
- `RENCI_EMAIL`, `RENCI_EMAIL_APP_PASSWORD` (email channel; poller disabled if unset)
- `GCP_PROJECT_ID`, `FIRESTORE_DATABASE`, `GCS_BUCKET`
- `APP_ENV`, `APP_URL`, `API_URL` (defined but not referenced elsewhere)

**Web:**
- `VITE_API_URL` (SSR fetch in `apps/web/src/routes/[slug]/+page.server.ts`); not in `.env.example`

**Secrets location:**
- Local: `apps/api/.env` (gitignored), template `.env.example` at repo root
- Production: no Secret Manager integration in Terraform or Cloud Build; secrets must be set manually on the Cloud Run service

## Webhooks & Callbacks

**Incoming:**
- `POST /webhooks/sms` - Twilio inbound SMS/MMS (form-encoded), returns TwiML (`apps/api/routes/webhooks.py`)
- `POST /webhooks/email` - JSON `{from_address, body, subject}`; used by web chat widget and for testing/email-forwarding services
- `POST /webhooks/email/poll` - manual trigger of one IMAP poll cycle
- `GET /agent/status`, `POST /agent/toggle` - control email poller
- `GET /api/v1/businesses/{slug}` - public business profile read for SvelteKit SSR (`apps/api/routes/api.py`)
- `GET /health`

**Outgoing:**
- Gemini API / Vertex AI `generateContent` (`apps/api/agent/core.py`)
- Twilio REST API (send SMS) and Twilio media URLs (MMS download)
- Gmail IMAP (`imap.gmail.com:993`) and SMTP (`smtp.gmail.com:465`)
- Firestore and Cloud Storage APIs
- Web -> API: SSR fetch via `VITE_API_URL`; browser fetches to hardcoded `https://renci-api-408375733910.us-central1.run.app` (`ChatWidget.svelte`, `AgentToggle.svelte`)

---

*Integration audit: 2026-10-14*
