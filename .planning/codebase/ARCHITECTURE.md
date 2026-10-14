<!-- refreshed: 2026-10-14 -->
# Architecture

**Analysis Date:** 2026-10-14

## System Overview

Renci is a two-service monorepo: a Python FastAPI backend (`apps/api/`) that runs an SMS/email AI agent for NYC Chinatown small-business owners, and a SvelteKit frontend (`apps/web/`) that renders each registered business as a public website at `/{slug}` and hosts a demo web chat. Both deploy as separate Cloud Run services (`infra/cloudbuild.yaml`, `infra/terraform/main.tf`).

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                          INBOUND CHANNELS                                 │
├───────────────────────┬────────────────────────┬─────────────────────────┤
│  Twilio SMS/MMS       │  Gmail IMAP poller      │  Web chat widget        │
│  POST /webhooks/sms   │  (background task)      │  POST /webhooks/email   │
│ `apps/api/routes/     │ `apps/api/email_channel/│ `apps/web/src/lib/      │
│  webhooks.py`         │  poller.py`, receiver.py│  components/ChatWidget` │
│                       │  handler.py`            │  -> routes/webhooks.py  │
└──────────┬────────────┴───────────┬────────────┴────────────┬────────────┘
           │  parse_incoming_sms     │  IncomingEmail ->        │ EmailMessage ->
           │  -> IncomingSMS         │  IncomingSMS             │ IncomingSMS
           ▼                         ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     MESSAGE ROUTER  `apps/api/sms/router.py`              │
│   route_message(IncomingSMS) -> looks up owner by phone/from address      │
└──────────────┬──────────────────────────────────────────┬────────────────┘
               │ owner missing or registration_step set   │ registered owner
               ▼                                          ▼
┌──────────────────────────────────┐   ┌──────────────────────────────────────┐
│ REGISTRATION STATE MACHINE        │   │ GEMINI AGENT  `apps/api/agent/core.py` │
│ `apps/api/agent/actions/          │   │ dispatch(): language detect, system   │
│  registration.py`                 │   │ prompt, multimodal parts, Gemini 2.5  │
│ name->type->address->confirm->    │   │ Flash with automatic function calling │
│ email -> create_business          │   │ over TOOLS list                       │
└───────────────┬──────────────────┘   └───────────────────┬──────────────────┘
                │                                          ▼
                │                      ┌──────────────────────────────────────┐
                │                      │ TOOLS                                 │
                │                      │ `apps/api/agent/tools.py` (profile)   │
                │                      │ `apps/api/agent/actions/ppp_data.py`  │
                │                      │ `apps/api/agent/actions/photo.py`     │
                │                      │ -> `agent/actions/profile.py`         │
                │                      └───────────────────┬──────────────────┘
                ▼                                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                               │
│  Firestore (owners, businesses)  `apps/api/db/firestore.py`               │
│  PPP CSV (pandas, in-memory)     `apps/api/data/ppp_loans_chinatown.csv`  │
│  GCS (unused helper)             `apps/api/integrations/storage.py`       │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │  GET /api/v1/businesses/{slug}
                                   ▼  (`apps/api/routes/api.py`)
┌──────────────────────────────────────────────────────────────────────────┐
│  PRESENTATION  SvelteKit (adapter-node)                                   │
│  `apps/web/src/routes/[slug]/+page.server.ts` -> DefaultTemplate.svelte   │
│  `apps/web/src/routes/+page.svelte` (landing)                             │
└──────────────────────────────────────────────────────────────────────────┘
```

Replies flow back on the same channel: TwiML XML body for SMS (`apps/api/routes/webhooks.py:18`), SMTP reply for email (`apps/api/email_channel/sender.py`), JSON `{"response": ...}` for the web chat.

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app | App construction, CORS, router registration, lifespan-managed email poller | `apps/api/main.py` |
| Settings | Env-driven config singleton (`settings`) via pydantic-settings | `apps/api/config.py` |
| Webhook routes | SMS webhook (TwiML), email webhook (JSON), manual poll, agent status/toggle | `apps/api/routes/webhooks.py` |
| Public API routes | `GET /api/v1/businesses/{slug}` for the frontend | `apps/api/routes/api.py` |
| Health route | `GET /health` | `apps/api/routes/health.py` |
| Twilio parser | `IncomingSMS` dataclass (the canonical inbound message type) and form parsing | `apps/api/sms/twilio_handler.py` |
| Message router | Decides registration vs agent dispatch | `apps/api/sms/router.py` |
| SMS sender | Outbound Twilio SMS (not wired into any flow) | `apps/api/sms/sender.py` |
| Email receiver | Blocking IMAP fetch of UNSEEN mail, marks as read | `apps/api/email_channel/receiver.py` |
| Email handler | Filters to carrier SMS-gateway senders, converts to `IncomingSMS`, replies via SMTP | `apps/api/email_channel/handler.py` |
| Email poller | Module-level loop flag, runs IMAP fetch in a ThreadPoolExecutor | `apps/api/email_channel/poller.py` |
| Email sender | Gmail SMTP_SSL reply | `apps/api/email_channel/sender.py` |
| Agent core | Builds prompt + parts, calls Gemini with `TOOLS`, extracts text | `apps/api/agent/core.py` |
| Agent tools (profile) | Tool functions exposed to Gemini; wrap profile actions and templates | `apps/api/agent/tools.py` |
| Profile actions | Sanitize and persist hours/contact/description updates | `apps/api/agent/actions/profile.py` |
| Registration | 6-step SMS onboarding state machine persisted on the owner doc | `apps/api/agent/actions/registration.py` |
| PPP data tools | pandas queries over the bundled SBA PPP CSV | `apps/api/agent/actions/ppp_data.py` |
| Photo tools | Twilio media download; `extract_menu_from_photo` tool (returns canned message) | `apps/api/agent/actions/photo.py` |
| Prompts | Bilingual system prompt and response templates | `apps/api/agent/prompts/system.py`, `apps/api/agent/prompts/templates.py` |
| Language | CJK lead-character language detection, traditional-Chinese heuristic | `apps/api/language/detector.py`, `apps/api/language/config.py` |
| Firestore repo | Async client singleton, owner/business CRUD, `slugify` | `apps/api/db/firestore.py` |
| Models | Pydantic `BusinessProfile`, `MenuItem`, `Owner`, `BUSINESS_TYPES` (documentation-only; Firestore uses raw dicts) | `apps/api/models/business.py`, `apps/api/models/owner.py` |
| Assistant (stub) | Future multi-turn conversational layer and session memory | `apps/api/assistant/core.py`, `apps/api/assistant/memory.py` |
| Storage (unused) | GCS photo upload helper | `apps/api/integrations/storage.py` |
| Web layout | Global CSS, mounts `AgentToggle` and `ChatWidget` on every page | `apps/web/src/routes/+layout.svelte` |
| Business page | SSR load of business by slug, renders template | `apps/web/src/routes/[slug]/+page.server.ts`, `apps/web/src/routes/[slug]/+page.svelte` |
| Business template | Renders name, hours, contact, menu, photos | `apps/web/src/lib/templates/DefaultTemplate.svelte` |
| Chat widget | Demo web chat; posts to `/webhooks/email` with a synthesized carrier-gateway address | `apps/web/src/lib/components/ChatWidget.svelte` |
| Agent toggle | Calls `/agent/status` and `/agent/toggle` | `apps/web/src/lib/components/AgentToggle.svelte` |
| i18n | `t(locale, key)` lookup over en / zh-Hans / zh-Hant JSON | `apps/web/src/lib/i18n/index.ts` |

## Pattern Overview

**Overall:** Channel adapters -> single message router -> LLM tool-calling agent -> function-style repository over Firestore. Frontend is a thin SSR read-only renderer over the API.

**Key Characteristics:**
- Every inbound channel is normalized to `IncomingSMS` (`apps/api/sms/twilio_handler.py:5`) before calling `route_message`. The sender identity (`from_number`) is the owner key: phone number (`+1...`) for SMS/gateway email, or raw `from_address` for the direct email webhook.
- Stateless per-message agent: no conversation history is passed to Gemini; only the current message plus a business-aware system prompt (`apps/api/agent/core.py:51-104`).
- Conversation state exists only for registration, stored on the owner document as `registration_step` + `registration_data` (`apps/api/agent/actions/registration.py`).
- Tools are plain Python functions whose signatures + docstrings become the Gemini function schema (google-genai automatic function calling). `business_id` and `language` are injected by instructing the model in the system prompt, not by binding (`apps/api/agent/core.py:77-82`).
- Bilingual (en/zh) everywhere: detection per message, branching in templates and prompts on `language == "zh"`.
- Persistence is a module of free async functions (`apps/api/db/firestore.py`) returning plain `dict`s with an injected `"id"` key; no ORM, Pydantic models are not used on the data path.

## Layers

**Transport / Channel Layer:**
- Purpose: Receive inbound messages, convert to `IncomingSMS`, return replies in channel format.
- Location: `apps/api/routes/webhooks.py`, `apps/api/sms/`, `apps/api/email_channel/`
- Contains: FastAPI route handlers, Twilio form parser, IMAP/SMTP code, background poller.
- Depends on: `sms/router.py`, `config.settings`
- Used by: Twilio, Gmail inbox, `apps/web` ChatWidget/AgentToggle.

**Routing Layer:**
- Purpose: Owner lookup and branch to registration or agent.
- Location: `apps/api/sms/router.py`
- Depends on: `db/firestore.get_owner_by_phone`, `agent/core.dispatch`, `agent/actions/registration.handle_registration`
- Used by: `routes/webhooks.py`, `email_channel/handler.py`

**Agent Layer:**
- Purpose: LLM orchestration, tool definitions, prompts, deterministic flows.
- Location: `apps/api/agent/` (`core.py`, `tools.py`, `actions/`, `prompts/`), `apps/api/language/`
- Depends on: `google.genai`, `db/firestore.py`, `pandas` (PPP), `httpx` (media download)
- Used by: `sms/router.py`

**Data Layer:**
- Purpose: Firestore reads/writes, bundled CSV dataset.
- Location: `apps/api/db/firestore.py`, `apps/api/data/ppp_loans_chinatown.csv`, `apps/api/integrations/storage.py`
- Depends on: `google.cloud.firestore_v1.AsyncClient`, `config.settings`
- Used by: router, agent tools/actions, `routes/api.py`

**Presentation Layer (web):**
- Purpose: Public business sites and demo landing page.
- Location: `apps/web/src/`
- Depends on: API `GET /api/v1/businesses/{slug}` (via `VITE_API_URL`), webhook endpoints (hardcoded Cloud Run URL in components).
- Used by: End users / browsers.

## Data Flow

### Primary Request Path (Twilio SMS -> agent -> Firestore)

1. Twilio POSTs form data to `/webhooks/sms` (`apps/api/routes/webhooks.py:9-18`).
2. `parse_incoming_sms` builds `IncomingSMS` with `From`, `Body`, `MediaUrl{i}` (`apps/api/sms/twilio_handler.py:12-26`).
3. `route_message` calls `get_owner_by_phone` (Firestore query on `owners.phone`) (`apps/api/sms/router.py:7-21`, `apps/api/db/firestore.py:31-39`).
4. Owner missing or `registration_step` truthy -> `handle_registration` (`apps/api/agent/actions/registration.py:12-39`). Otherwise -> `dispatch(message, owner, business_id)`.
5. `dispatch` loads the business doc, runs `detect_language`, builds the system prompt, appends text and downloaded MMS image parts, and appends an instruction telling the model which `business_id`/`language` to pass (`apps/api/agent/core.py:51-82`).
6. `client.models.generate_content(model="gemini-2.5-flash", tools=TOOLS, temperature=0.3, max_output_tokens=500)` runs with automatic function calling (`apps/api/agent/core.py:87-96`).
7. Tool calls (e.g. `update_business_hours`) call `agent/actions/profile.py` -> `db/firestore.update_business` which sets `updated_at` and updates the `businesses/{id}` doc (`apps/api/agent/tools.py:17-55`, `apps/api/db/firestore.py:104-107`).
8. First text part of the response is returned; fallback is `help_response(language)` (`apps/api/agent/core.py:99-104`).
9. Webhook wraps text in TwiML `<Response><Message>` and returns `application/xml` (`apps/api/routes/webhooks.py:17-18`).

### Email Poller Path (carrier SMS-to-email gateway)

1. `lifespan` starts `start_email_poller(15)` as an asyncio task when `RENCI_EMAIL` and `RENCI_EMAIL_APP_PASSWORD` are set (`apps/api/main.py:16-32`).
2. After a 15s startup delay, every 15s `poll_emails_once` runs `fetch_unread_emails` (max 5 UNSEEN, marks Seen) in a single-thread executor (`apps/api/email_channel/poller.py:19-57`, `apps/api/email_channel/receiver.py:25-91`).
3. `handle_email` ignores senders not matching `^\d{10,11}@<carrier gateway>`; extracts `+1XXXXXXXXXX` (`apps/api/email_channel/handler.py:27-56`).
4. Builds `IncomingSMS` (body falls back to subject), calls `route_message`, sends reply with `send_email_reply` over SMTP_SSL (`apps/api/email_channel/handler.py:58-70`).

### Web Chat Path

1. `ChatWidget.svelte` collects phone + carrier, builds `<digits>@<gateway>` (or `demo@renci.app`), POSTs `{from_address, body, subject}` to `${API_URL}/webhooks/email` (`apps/web/src/lib/components/ChatWidget.svelte:13-71`).
2. `email_webhook` builds `IncomingSMS(from_number=msg.from_address, ...)` with no gateway filtering or phone extraction, then `route_message` (`apps/api/routes/webhooks.py:28-37`).
3. Response returned as JSON `{"response", "from"}`; no SMTP reply is sent on this path.

Note: the web chat keys the owner by the full gateway email string, while the poller keys by `+1` phone. The same person is a different owner record on the two paths.

### Registration Flow (deterministic, no LLM)

1. Unknown sender -> `create_owner(phone)` with `registration_step="name"`, return welcome (`apps/api/agent/actions/registration.py:16-18`, `apps/api/db/firestore.py:42-56`).
2. Steps `name -> type -> address -> address_confirm -> email` update `owners/{id}` with the next step and accumulated `registration_data` (`apps/api/agent/actions/registration.py:51-115`).
3. On valid email: `slugify(name)`, `create_business` (adds `tier`, `photos`, `social`, `menu_items`, `theme`, timestamps), then set `registration_step=None`, `business_id` on owner (`apps/api/agent/actions/registration.py:118-157`, `apps/api/db/firestore.py:67-80`).

### Public Website Render

1. Browser hits `/{slug}`; `+page.server.ts` fetches `${VITE_API_URL}/api/v1/businesses/{slug}` and 404s on failure (`apps/web/src/routes/[slug]/+page.server.ts`).
2. API calls `get_business_by_slug` (`apps/api/routes/api.py`, `apps/api/db/firestore.py:93-101`).
3. `+page.svelte` sets `<svelte:head>` and renders `DefaultTemplate` with the business dict.

**State Management:**
- Backend: Firestore is the only durable state (`owners`, `businesses` collections). In-process state: Firestore client singleton, PPP DataFrame cache, poller `_running` flag.
- Frontend: Svelte 5 runes (`$state`, `$props`, `$effect`) local to components; no stores.

## Key Abstractions

**IncomingSMS (canonical inbound message):**
- Purpose: Channel-agnostic message passed to the router and agent.
- Examples: `apps/api/sms/twilio_handler.py:5`, constructed in `apps/api/routes/webhooks.py:30`, `apps/api/email_channel/handler.py:58`
- Pattern: `@dataclass` with `from_number`, `body`, `media_urls`, `num_media`. New channels must adapt into this type.

**Agent tool function:**
- Purpose: Capability exposed to Gemini.
- Examples: `apps/api/agent/tools.py`, `apps/api/agent/actions/ppp_data.py`, `apps/api/agent/actions/photo.py`
- Pattern: Top-level function with typed defaulted params, Google-style docstring with `Args:`, returns `{"status": "success"|"error", "message": str, ...}`. Register by adding to `TOOLS` in `apps/api/agent/core.py:26-36`. Accept `business_id: str = ""` and `language: str = "en"` if needed (injected via prompt).

**Action module:**
- Purpose: Side-effecting business logic separated from the tool schema surface.
- Examples: `apps/api/agent/actions/profile.py`, `apps/api/agent/actions/registration.py`
- Pattern: async functions that call `db/firestore.py`.

**Repository functions:**
- Purpose: Firestore access.
- Examples: `get_owner_by_phone`, `create_owner`, `update_owner`, `create_business`, `get_business`, `get_business_by_slug`, `update_business` in `apps/api/db/firestore.py`
- Pattern: `db = get_db()` then collection call; return `dict` with `"id"` added, or `None`.

**Bilingual template:**
- Purpose: User-facing response text.
- Examples: `apps/api/agent/prompts/templates.py`, `apps/api/agent/prompts/system.py`
- Pattern: function `(data, language) -> str` with `if language == "zh":` branch.

**Business template (web):**
- Purpose: Render a business site.
- Examples: `apps/web/src/lib/templates/DefaultTemplate.svelte`
- Pattern: Svelte 5 component taking `business` prop with a local `Business` interface. `theme.template` in Firestore is always `"default"`; there is no template selector yet.

## Entry Points

**API server:**
- Location: `apps/api/main.py` (`app`)
- Triggers: `uvicorn main:app` (root `package.json` `dev:api`, `apps/api/Dockerfile` CMD on `$PORT`=8080)
- Responsibilities: Register routers, CORS `*`, start/stop email poller via lifespan.

**HTTP endpoints:**
- `POST /webhooks/sms`, `POST /webhooks/email`, `POST /webhooks/email/poll`, `GET /agent/status`, `POST /agent/toggle` — `apps/api/routes/webhooks.py`
- `GET /api/v1/businesses/{slug}` — `apps/api/routes/api.py`
- `GET /health` — `apps/api/routes/health.py`

**Background task:**
- Location: `apps/api/email_channel/poller.py:start_email_poller`
- Triggers: app lifespan, or `/agent/toggle`.

**Web server:**
- Location: `apps/web/svelte.config.js` (adapter-node), built output run with `node build` (`apps/web/Dockerfile`).
- Routes: `/` (`apps/web/src/routes/+page.svelte`), `/{slug}` (`apps/web/src/routes/[slug]/`).

**Static root page:**
- Location: `index.html` at repo root — standalone landing page, not part of the SvelteKit app.

**Deployment:**
- `infra/cloudbuild.yaml` builds/pushes both images and deploys `renci-api` / `renci-web` to Cloud Run in `us-east1`.
- `infra/terraform/main.tf` declares Firestore, GCS bucket `renci-assets`, and both Cloud Run services.

## Architectural Constraints

- **Threading:** Single asyncio event loop (uvicorn). IMAP fetch is offloaded to a 1-worker `ThreadPoolExecutor` (`apps/api/email_channel/poller.py:10`). Blocking calls still run on the event loop: `client.models.generate_content` (sync Gemini call, `apps/api/agent/core.py:87`), `send_email_reply` SMTP (`apps/api/email_channel/handler.py:68`), Twilio `messages.create` (`apps/api/sms/sender.py:12`), GCS upload (`apps/api/integrations/storage.py`), and pandas CSV load.
- **Async tools with sync client:** Profile tools in `apps/api/agent/tools.py` are `async def` but are invoked through the synchronous `client.models.generate_content` automatic function calling. Verify google-genai awaits coroutines on the sync path before adding more async tools; if not, use `client.aio.models.generate_content`.
- **Global state:** `_client` Firestore singleton (`apps/api/db/firestore.py:6`), `_df` PPP DataFrame cache (`apps/api/agent/actions/ppp_data.py:28`), `_running` / `_executor` poller state (`apps/api/email_channel/poller.py:9-10`), `settings` (`apps/api/config.py:31`). `agent_status`/`agent_toggle` in `apps/api/routes/webhooks.py` read `_running` by `from ... import _running`, which captures the value at import time of that call (works only because it re-imports per request).
- **Process-local poller:** Poller state is per-instance; with Cloud Run scaling to multiple instances (`max_instance_count = 10`) each instance polls independently and `/agent/toggle` only affects the instance that served it.
- **Import style:** Modules import each other as top-level packages (`from db.firestore import ...`), so the API must run with `apps/api/` as CWD / on `sys.path`. Several imports are deferred inside functions to avoid import cycles or optional deps (`apps/api/main.py:21`, `apps/api/routes/webhooks.py:43,51,58`, `apps/api/email_channel/poller.py:15,31`).
- **Circular imports:** `email_channel/handler.py` -> `sms/router.py` -> `agent/core.py`; `email_channel/poller.py` imports the handler lazily to keep startup independent of the agent stack. No hard cycles detected.
- **Owner identity:** Owner key is `owners.phone` matching `IncomingSMS.from_number` exactly; no normalization across channels.
- **SMS length:** Prompt demands <300 characters, `max_output_tokens=500`; no truncation enforced.

## Anti-Patterns

### Instructing the model to pass trusted IDs

**What happens:** `business_id` and `language` are tool parameters the model must fill in, guided by text in the system instruction (`apps/api/agent/core.py:77-82`).
**Why it's wrong:** The model can omit, hallucinate, or be prompt-injected into another `business_id`, writing to another business's document.
**Do this instead:** Bind trusted context server-side (closures/partials per request, or execute function calls manually and inject `business_id` before calling the action in `apps/api/agent/actions/profile.py`).

### Unescaped TwiML

**What happens:** Agent text is interpolated directly into XML (`apps/api/routes/webhooks.py:17`).
**Why it's wrong:** `&`, `<`, `>` in model output produce invalid TwiML.
**Do this instead:** Use `twilio.twiml.messaging_response.MessagingResponse` or `xml.sax.saxutils.escape`.

### Hardcoded API URL in components

**What happens:** `ChatWidget.svelte` and `AgentToggle.svelte` hardcode `https://renci-api-...us-central1.run.app`, while `[slug]/+page.server.ts` uses `VITE_API_URL`.
**Why it's wrong:** Local dev and other environments hit production; region differs from `infra/` (`us-east1`).
**Do this instead:** Read `import.meta.env.VITE_API_URL` (or `$env/static/public`) in all components, as in `apps/web/src/routes/[slug]/+page.server.ts`.

### Unused Pydantic models on the data path

**What happens:** `BusinessProfile` / `Owner` exist (`apps/api/models/`) but Firestore functions take/return raw dicts and `create_business` sets defaults separately (`apps/api/db/firestore.py:67-80`).
**Why it's wrong:** Schema defaults are duplicated and can drift.
**Do this instead:** When touching persistence, validate through `models/` and use `model_dump()` for writes.

### Blocking I/O in async handlers

**What happens:** Sync Gemini/SMTP/Twilio calls inside `async def` functions.
**Why it's wrong:** Blocks the event loop, stalling all other requests (including Twilio webhooks with 15s timeout).
**Do this instead:** Use `client.aio` for Gemini and `asyncio.to_thread(...)` for SMTP/Twilio, mirroring the executor pattern in `apps/api/email_channel/poller.py:23`.

## Error Handling

**Strategy:** Best-effort, swallow-and-fallback. No global exception handlers.

**Patterns:**
- Agent returns a friendly string on missing business or empty response (`apps/api/agent/core.py:54-55, 73-74, 104`).
- MMS download failures are silently skipped (`apps/api/agent/core.py:70-71`).
- Tools return `{"status": "error", "message": ...}` dicts rather than raising (`apps/api/agent/tools.py`).
- Poller logs and continues per email and per cycle (`apps/api/email_channel/poller.py:24-36, 53-56`).
- API 404 via `HTTPException` (`apps/api/routes/api.py`); web 404 via SvelteKit `error(404, ...)`.
- Gemini exceptions in `dispatch` are not caught; they propagate as 500 from the webhook.

## Cross-Cutting Concerns

**Logging:** stdlib `logging` at INFO, logger names `renci` and `renci.email_poller` (`apps/api/main.py:11-12`, `apps/api/email_channel/poller.py:7`). Most modules do not log.
**Validation:** Pydantic only for the `/webhooks/email` body (`EmailMessage`). Registration does minimal checks (choice in `BUSINESS_TYPES`, `@` and `.` in email).
**Authentication:** None. No Twilio signature validation on `/webhooks/sms`; `/webhooks/email`, `/agent/toggle`, `/webhooks/email/poll` are public; CORS `allow_origins=["*"]`; Cloud Run services are `allUsers` invokers.
**Internationalization:** Backend en/zh via `language/detector.py` + template branches; frontend en / zh-Hans / zh-Hant JSON via `apps/web/src/lib/i18n/index.ts`.

---

*Architecture analysis: 2026-10-14*
