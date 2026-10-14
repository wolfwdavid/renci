# Technology Stack

**Analysis Date:** 2026-10-14

## Languages

**Primary:**
- Python 3.12 (container) / 3.11+ (README prerequisite) - Backend API, AI agent, SMS/email channels, data tools (`apps/api/`)
- TypeScript 5.9 (strict) - SvelteKit frontend (`apps/web/src/`, config `apps/web/tsconfig.json`)

**Secondary:**
- Svelte 5 components (runes mode forced for project files) - UI (`apps/web/src/lib/components/*.svelte`, `apps/web/src/routes/**/*.svelte`)
- HCL (Terraform) - Infrastructure (`infra/terraform/main.tf`)
- YAML - Cloud Build pipeline (`infra/cloudbuild.yaml`)
- Static HTML/CSS - Standalone landing page at repo root (`index.html`, not part of SvelteKit build)
- JSON - i18n dictionaries (`apps/web/src/lib/i18n/en.json`, `zh-Hans.json`, `zh-Hant.json`)

## Runtime

**Environment:**
- Python 3.12 (`python:3.12-slim` base image in `apps/api/Dockerfile`), ASGI server Uvicorn
- Node.js 22 (`node:22-slim` multi-stage build in `apps/web/Dockerfile`; README requires Node 22+)

**Package Manager:**
- npm (workspaces) - root `package.json` declares workspace `apps/web`
  - Lockfiles: `package-lock.json` (root) and `apps/web/package-lock.json` - both present
  - `apps/web/.npmrc` sets `engine-strict=true`
- pip - `apps/api/requirements.txt` (range-pinned, no lockfile; no `pyproject.toml`)

## Frameworks

**Core:**
- FastAPI `>=0.115.0,<1.0` - HTTP API, webhooks, lifespan-managed background poller (`apps/api/main.py`)
- Pydantic `>=2.10.0` / pydantic-settings `>=2.7.0` - Request models and env config (`apps/api/config.py`, `apps/api/models/`)
- SvelteKit `^2.50.2` (lockfile 2.55.0) with Svelte `^5.54.0` - Web frontend with SSR (`apps/web/`)
- Tailwind CSS `^4.2.2` via `@tailwindcss/vite` - Styling (`apps/web/vite.config.ts`, `apps/web/src/app.css`)

**Testing:**
- pytest - Python test runner (`apps/api/tests/`); invoked via `npm run test:api` or `python -m pytest tests/ -v`
  - NOT listed in `apps/api/requirements.txt`; async tests in `apps/api/tests/test_webhook.py` and `apps/api/tests/test_registration.py` use `pytest.mark.asyncio`, which requires `pytest-asyncio` (also unlisted)
  - httpx `AsyncClient` + `ASGITransport` for in-process API tests (`apps/api/tests/test_webhook.py`)
  - `unittest.mock` (`AsyncMock`, `patch`) for mocking Firestore/agent calls
- svelte-check `^4.4.2` - Type checking for web (`npm run check` in `apps/web`)
- No JS unit test framework detected

**Build/Dev:**
- Vite `^7.3.1` - Web dev server/bundler (`apps/web/vite.config.ts`)
- `@sveltejs/adapter-node` `^5.5.4` - Produces Node server in `build/` (`apps/web/svelte.config.js`); `@sveltejs/adapter-auto` is installed but unused
- `@sveltejs/vite-plugin-svelte` `^6.2.4`
- concurrently `^9.1.0` - Root `npm run dev` runs API + web together (`package.json`)
- Uvicorn `uvicorn[standard]>=0.34.0` - `uvicorn main:app --reload --port 8000` for local dev
- Docker - Images for both apps (`apps/api/Dockerfile`, `apps/web/Dockerfile`)

## Key Dependencies

**Critical (Python, `apps/api/requirements.txt`):**
- `google-genai>=1.0.0` - Gemini client; `gemini-2.5-flash` with automatic function calling over Python callables (`apps/api/agent/core.py`). Docstrings mention "Google ADK" but the ADK package (`google-adk`) is NOT installed or imported; tools are plain functions passed to `GenerateContentConfig(tools=...)` (`apps/api/agent/tools.py`)
- `google-cloud-firestore>=2.19.0` - Primary datastore via `AsyncClient` (`apps/api/db/firestore.py`)
- `twilio>=9.0.0` - Outbound SMS (`apps/api/sms/sender.py`)
- `pandas>=2.2.0` - Loads and queries PPP loan CSV (`apps/api/agent/actions/ppp_data.py`, data in `apps/api/data/ppp_loans_chinatown.csv`)

**Infrastructure (Python):**
- `google-cloud-storage>=2.19.0` - Photo/asset uploads (`apps/api/integrations/storage.py`)
- `httpx>=0.28.0` - Authenticated Twilio MMS media download (`apps/api/agent/actions/photo.py`) and test client
- `python-dotenv>=1.0.0` - `.env` loading (pydantic-settings reads `.env` directly)
- Python stdlib `imaplib`, `smtplib`, `email` - Gmail email channel (`apps/api/email_channel/`)

**Frontend:**
- No runtime dependencies; all packages in `apps/web/package.json` are devDependencies (bundled at build time). Production image copies full `node_modules` regardless.

## Configuration

**Environment:**
- Backend config is a single `Settings(BaseSettings)` singleton in `apps/api/config.py`, reading env vars and `.env` (relative to CWD, i.e. `apps/api/.env`). Import as `from config import settings`.
- Template: `.env.example` at repo root (copy to `apps/api/.env`). `.env`, `.env.local`, `.env.production` are gitignored.
- Variables: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `GOOGLE_API_KEY`, `USE_VERTEX_AI`, `RENCI_EMAIL`, `RENCI_EMAIL_APP_PASSWORD`, `GCP_PROJECT_ID` (default `renci-491614`), `FIRESTORE_DATABASE` (default `(default)`), `GCS_BUCKET` (default `renci-assets`), `APP_ENV`, `APP_URL`, `API_URL`
- Container: `PORT` (default 8080 in `apps/api/Dockerfile`)
- Frontend: `VITE_API_URL` (build-time, used in `apps/web/src/routes/[slug]/+page.server.ts`, fallback `http://localhost:8000`). `apps/web/src/lib/components/ChatWidget.svelte` and `AgentToggle.svelte` hardcode `https://renci-api-408375733910.us-central1.run.app` instead.

**Build:**
- `apps/web/svelte.config.js` - adapter-node, runes enabled for non-`node_modules` files
- `apps/web/vite.config.ts` - `sveltekit()` + `tailwindcss()` plugins
- `apps/web/tsconfig.json` - extends `.svelte-kit/tsconfig.json`, `strict: true`, `moduleResolution: bundler`
- `apps/api/Dockerfile`, `apps/web/Dockerfile` - container builds
- `infra/cloudbuild.yaml` - CI build/push/deploy
- `infra/terraform/main.tf` - GCP resources

**Root scripts (`package.json`):**
- `npm run dev` - API (port 8000) + web (port 5173) concurrently
- `npm run dev:api`, `npm run dev:web`, `npm run build:web`, `npm run test:api`

## Platform Requirements

**Development:**
- Python 3.11+ (3.12 recommended to match container), Node.js 22+
- GCP project with Firestore (Application Default Credentials for Firestore/GCS clients)
- Gemini API key (AI Studio) or Vertex AI access (`USE_VERTEX_AI=true`)
- Gmail account with App Password for email channel; Twilio account for SMS

**Production:**
- Google Cloud Run: `renci-api` (FastAPI container) and `renci-web` (Node adapter container, port 3000)
- Images in Artifact Registry `${REGION}-docker.pkg.dev/${PROJECT_ID}/renci/{api,web}`
- Region inconsistency: `infra/cloudbuild.yaml` and `infra/terraform/main.tf` use `us-east1`; README deploy commands and hardcoded frontend URLs use `us-central1`

---

*Stack analysis: 2026-10-14*
