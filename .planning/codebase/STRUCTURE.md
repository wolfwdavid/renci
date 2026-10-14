# Codebase Structure

**Analysis Date:** 2026-10-14

## Directory Layout

```
renci/
├── apps/
│   ├── api/                      # Python FastAPI backend (agent, channels, Firestore)
│   │   ├── main.py               # FastAPI app, CORS, routers, email-poller lifespan
│   │   ├── config.py             # pydantic-settings `settings` singleton (reads .env)
│   │   ├── Dockerfile            # python:3.12-slim, uvicorn on $PORT (8080)
│   │   ├── requirements.txt      # Python deps
│   │   ├── routes/               # HTTP route modules (APIRouter per file)
│   │   │   ├── webhooks.py       # /webhooks/sms, /webhooks/email, /webhooks/email/poll, /agent/*
│   │   │   ├── api.py            # /api/v1/businesses/{slug}
│   │   │   └── health.py         # /health
│   │   ├── sms/                  # Twilio channel + the shared message router
│   │   │   ├── twilio_handler.py # IncomingSMS dataclass, parse_incoming_sms
│   │   │   ├── router.py         # route_message: registration vs agent
│   │   │   └── sender.py         # outbound Twilio SMS
│   │   ├── email_channel/        # Gmail IMAP/SMTP channel
│   │   │   ├── receiver.py       # IncomingEmail, fetch_unread_emails (IMAP)
│   │   │   ├── handler.py        # gateway filter -> IncomingSMS -> route_message -> reply
│   │   │   ├── poller.py         # background polling loop + start/stop
│   │   │   └── sender.py         # send_email_reply (SMTP_SSL)
│   │   ├── agent/                # Gemini agent
│   │   │   ├── core.py           # dispatch(), TOOLS list, Gemini client
│   │   │   ├── tools.py          # profile tools exposed to Gemini
│   │   │   ├── actions/          # side-effecting logic + extra tools
│   │   │   │   ├── profile.py        # update_hours/contact/description -> Firestore
│   │   │   │   ├── registration.py   # 6-step onboarding state machine
│   │   │   │   ├── ppp_data.py       # PPP CSV tools (pandas)
│   │   │   │   └── photo.py          # Twilio media download, menu-photo tool
│   │   │   └── prompts/
│   │   │       ├── system.py     # bilingual system prompt builder
│   │   │       └── templates.py  # bilingual response templates
│   │   ├── assistant/            # Stubs for future multi-turn assistant mode
│   │   │   ├── core.py           # handle_conversation (NotImplementedError)
│   │   │   └── memory.py         # session memory stubs
│   │   ├── db/
│   │   │   └── firestore.py      # AsyncClient singleton, owner/business CRUD, slugify
│   │   ├── models/               # Pydantic schemas (BusinessProfile, MenuItem, Owner, BUSINESS_TYPES)
│   │   ├── language/             # detect_language, is_traditional_chinese, SUPPORTED_LANGUAGES
│   │   ├── integrations/
│   │   │   └── storage.py        # GCS upload helper (not wired in)
│   │   ├── data/
│   │   │   └── ppp_loans_chinatown.csv  # bundled SBA PPP sample (zips 10002, 10013)
│   │   └── tests/                # pytest suite (flat, test_<area>.py)
│   └── web/                      # SvelteKit 2 + Svelte 5 + Tailwind 4 frontend
│       ├── package.json          # vite scripts, adapter-node
│       ├── svelte.config.js      # adapter-node, runes enabled for project files
│       ├── vite.config.ts        # sveltekit() + tailwindcss() plugins
│       ├── Dockerfile            # node:22-slim multi-stage, `node build` on 3000
│       ├── static/               # renci-logo.png, robots.txt
│       └── src/
│           ├── app.html, app.css, app.d.ts
│           ├── routes/
│           │   ├── +layout.svelte          # mounts AgentToggle + ChatWidget globally
│           │   ├── +page.svelte            # landing page
│           │   └── [slug]/
│           │       ├── +page.server.ts     # SSR fetch /api/v1/businesses/{slug}
│           │       └── +page.svelte        # renders DefaultTemplate
│           └── lib/
│               ├── components/   # ChatWidget.svelte, AgentToggle.svelte
│               ├── templates/    # DefaultTemplate.svelte (business site template)
│               ├── i18n/         # index.ts (t()), en.json, zh-Hans.json, zh-Hant.json
│               ├── assets/       # favicon.svg
│               └── index.ts      # $lib barrel (empty)
├── infra/
│   ├── cloudbuild.yaml           # build/push/deploy both images to Cloud Run (us-east1)
│   └── terraform/main.tf         # Firestore, GCS bucket, Cloud Run services, IAM
├── tasks/                        # todo.md, lessons.md, commits.log (workflow tracking)
├── .planning/codebase/           # GSD codebase map documents
├── index.html                    # standalone static landing page (not part of SvelteKit)
├── package.json                  # npm workspaces ["apps/web"], dev scripts (concurrently)
├── package-lock.json
├── .env.example                  # template for API env vars
├── .gitignore
├── README.md                     # product overview, architecture, setup
└── Gemini_Generated_Image_*.png  # large (2.5 MB) image asset at repo root
```

## Directory Purposes

**`apps/api/routes/`:**
- Purpose: FastAPI `APIRouter` modules; each file exports `router` and is included in `apps/api/main.py`.
- Contains: Thin handlers that parse input and delegate to `sms/router.py` or `db/firestore.py`.
- Key files: `apps/api/routes/webhooks.py`, `apps/api/routes/api.py`

**`apps/api/sms/`:**
- Purpose: Twilio channel adapter and the channel-agnostic `route_message`.
- Contains: `IncomingSMS` (the canonical inbound message type used by all channels).
- Key files: `apps/api/sms/router.py`, `apps/api/sms/twilio_handler.py`

**`apps/api/email_channel/`:**
- Purpose: Email-as-SMS channel via Gmail IMAP polling and SMTP replies.
- Key files: `apps/api/email_channel/handler.py`, `apps/api/email_channel/poller.py`

**`apps/api/agent/`:**
- Purpose: Everything the LLM agent needs: client + dispatch, tool surface, side-effecting actions, prompts.
- Key files: `apps/api/agent/core.py` (`TOOLS` registry), `apps/api/agent/tools.py`, `apps/api/agent/actions/*.py`, `apps/api/agent/prompts/*.py`

**`apps/api/db/`:**
- Purpose: The only Firestore access point. Collections: `owners`, `businesses`.
- Key files: `apps/api/db/firestore.py`

**`apps/api/models/`:**
- Purpose: Pydantic schema definitions and the `BUSINESS_TYPES` menu mapping used by registration.
- Key files: `apps/api/models/business.py`, `apps/api/models/owner.py`

**`apps/api/language/`:**
- Purpose: en/zh detection used by agent and registration.
- Key files: `apps/api/language/detector.py`

**`apps/api/assistant/`, `apps/api/integrations/`:**
- Purpose: Future-facing stubs (conversational mode, session memory, GCS uploads). Not imported by the live request path.

**`apps/api/tests/`:**
- Purpose: pytest tests importing modules as top-level packages (run from `apps/api/`).
- Key files: `test_webhook.py`, `test_sms_router.py`, `test_registration.py`, `test_agent.py`, `test_ppp.py`, `test_photo.py`, `test_firestore.py`

**`apps/web/src/routes/`:**
- Purpose: SvelteKit file-based routes.
- Key files: `apps/web/src/routes/+layout.svelte`, `apps/web/src/routes/[slug]/+page.server.ts`

**`apps/web/src/lib/`:**
- Purpose: Shared Svelte code imported via `$lib/...`.
- Contains: `components/` (global widgets), `templates/` (business site layouts), `i18n/`.

**`infra/`:**
- Purpose: GCP deployment (Cloud Build pipeline, Terraform).

## Key File Locations

**Entry Points:**
- `apps/api/main.py`: FastAPI `app` (run with `uvicorn main:app` from `apps/api/`)
- `apps/web/src/routes/+layout.svelte`: root web layout
- `apps/web/src/routes/[slug]/+page.server.ts`: business site SSR loader
- `package.json` (root): `npm run dev` runs API (port 8000) and web concurrently

**Configuration:**
- `apps/api/config.py`: all backend settings (Twilio, Gemini, email, GCP, URLs)
- `.env.example`: env var template (copy to `apps/api/.env`; `config.py` reads `.env` relative to CWD)
- `apps/web/svelte.config.js`, `apps/web/vite.config.ts`, `apps/web/tsconfig.json`
- `infra/cloudbuild.yaml`, `infra/terraform/main.tf`

**Core Logic:**
- `apps/api/sms/router.py`: message routing
- `apps/api/agent/core.py`: Gemini dispatch and `TOOLS`
- `apps/api/agent/tools.py`: profile tools
- `apps/api/agent/actions/registration.py`: onboarding flow
- `apps/api/db/firestore.py`: persistence

**Testing:**
- `apps/api/tests/`: backend tests (`npm run test:api` or `pytest` in `apps/api/`)
- No frontend tests; `npm run check` in `apps/web/` runs `svelte-check`

## Naming Conventions

**Files:**
- Python: `snake_case.py` modules (`twilio_handler.py`, `ppp_data.py`).
- Python tests: `test_<area>.py` in `apps/api/tests/`.
- Svelte components: `PascalCase.svelte` (`ChatWidget.svelte`, `DefaultTemplate.svelte`).
- SvelteKit route files: `+page.svelte`, `+page.server.ts`, `+layout.svelte`; dynamic params in brackets (`[slug]`).
- i18n: BCP-47-ish locale names (`en.json`, `zh-Hans.json`, `zh-Hant.json`).

**Directories:**
- Python packages: lowercase, `snake_case` (`email_channel`), each with an empty `__init__.py`.
- The email package is `email_channel` (not `email`) to avoid shadowing the stdlib `email` module. Do not create packages named after stdlib modules.
- Web: lowercase plural (`components`, `templates`).

**Symbols:**
- Python functions `snake_case`; private helpers prefixed `_` (`_handle_name`, `_load_data`, `_get_client`); module-level private state prefixed `_` (`_client`, `_df`, `_running`).
- Tool functions are verb-first and descriptive since the name is shown to the model (`update_business_hours`, `lookup_ppp_data`).
- Firestore field names `snake_case`; bilingual fields suffixed `_en` / `_zh` (`description_en`, `name_zh`).

## Where to Add New Code

**New agent tool:**
- Tool function: `apps/api/agent/tools.py` (profile-type) or a new `apps/api/agent/actions/<domain>.py` (domain-specific, like `ppp_data.py`).
- Persisting logic: `apps/api/agent/actions/<domain>.py` calling `apps/api/db/firestore.py`.
- Register: add to `TOOLS` in `apps/api/agent/core.py`.
- Prompt guidance: add a rule line to both language branches in `apps/api/agent/prompts/system.py`.
- User-facing text: add a bilingual function in `apps/api/agent/prompts/templates.py`.
- Tests: `apps/api/tests/test_<domain>.py`.

**New inbound channel:**
- Adapter package: `apps/api/<channel>_channel/` (receiver/handler/sender split like `apps/api/email_channel/`).
- Convert to `IncomingSMS` and call `route_message` from `apps/api/sms/router.py`.
- Webhook endpoint: `apps/api/routes/webhooks.py` (or a new router file included in `apps/api/main.py`).

**New HTTP API endpoint for the frontend:**
- `apps/api/routes/api.py` under the `/api/v1` prefix.

**New Firestore operation or collection:**
- Add async functions to `apps/api/db/firestore.py` following `get_db()` + return `dict` with `"id"`.
- Add/extend the Pydantic schema in `apps/api/models/`.

**New config value:**
- Field on `Settings` in `apps/api/config.py` plus an entry in `.env.example`.

**New web page:**
- `apps/web/src/routes/<path>/+page.svelte`; server data in `+page.server.ts` using `import.meta.env.VITE_API_URL`.

**New business site template:**
- `apps/web/src/lib/templates/<Type>Template.svelte`, selected in `apps/web/src/routes/[slug]/+page.svelte` (e.g. by `business.theme.template` or `business_type`).

**New shared web component:**
- `apps/web/src/lib/components/<Name>.svelte`; globally mounted widgets go in `apps/web/src/routes/+layout.svelte`.

**Translations:**
- Add keys to all three files in `apps/web/src/lib/i18n/` and read via `t(locale, 'a.b')`.

**Utilities:**
- Backend text/language helpers: `apps/api/language/`. Slug helpers live in `apps/api/db/firestore.py` (`slugify`).
- Frontend: `apps/web/src/lib/` (export via `$lib/...` path imports; `lib/index.ts` is an empty barrel).

**Infrastructure:**
- New GCP resources: `infra/terraform/main.tf`. New build/deploy steps: `infra/cloudbuild.yaml`.

## Special Directories

**`apps/api/data/`:**
- Purpose: Bundled PPP CSV loaded at runtime by `apps/api/agent/actions/ppp_data.py` (path resolved relative to the module).
- Generated: No
- Committed: Yes

**`apps/api/assistant/`:**
- Purpose: Placeholder for future multi-turn mode; not referenced by the router.
- Generated: No
- Committed: Yes

**`tasks/`:**
- Purpose: Workflow tracking (`todo.md`, `lessons.md`, `commits.log`).
- Generated: No
- Committed: Yes

**`.planning/`:**
- Purpose: GSD planning artifacts and codebase map.
- Generated: Yes (by GSD commands)
- Committed: Yes

**`apps/web/.svelte-kit/`, `apps/web/build/`, `node_modules/`, `__pycache__/`, `.venv/`:**
- Purpose: Build outputs and dependencies.
- Generated: Yes
- Committed: No (`.gitignore`)

---

*Structure analysis: 2026-10-14*
