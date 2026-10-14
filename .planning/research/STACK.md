# Stack Research

**Domain:** Production-grade Gemini function-calling agent service (FastAPI on Cloud Run) with agent evaluation, GitOps on local kind, Terraform IaC, and Prometheus/Cloud Logging observability, on a $0 GCP budget
**Researched:** 2026-10-14
**Confidence:** HIGH for versions. All versions below come from PyPI, the GitHub releases API, or npm, queried on 2026-10-14. MEDIUM for the opinionated choices; each one gives its reasoning.

> Scope: only what v2 adds or changes. The existing stack (FastAPI, SvelteKit 2 / Svelte 5, Firestore, GCS, Twilio, Gmail IMAP/SMTP) is documented in `.planning/codebase/STACK.md` and is not re-researched here.

---

## Headline Findings (read first)

1. **`google-genai` 2.30.1 supports `async def` tools in automatic function calling (AFC) when you call through `client.aio`.** Sync tools run via `asyncio.to_thread`. The current bug ("async tools passed to sync client") is fixed by switching to `await client.aio.models.generate_content(...)`. **However, still disable AFC and run a manual tool loop.** That is the only clean way to (a) inject `business_id` on the server side instead of letting the model choose it, (b) record each tool call for eval metrics and Prometheus counters, and (c) enforce an allow-list per conversation state. *(HIGH: verified in the SDK source, `_extra_utils.py`.)*
2. **`gemini-2.5-flash` is not deprecated, but Google says access is "limited to users who have actively used the 2.5 models"**, and it recommends `gemini-3.8-flash` / `gemini-3.5-flash-lite` for new projects. All of them have a free tier. Make the model a setting and let the eval harness pick it. *(HIGH: ai.google.dev models, deprecations, and pricing pages.)*
3. **The $0 budget has two sharp edges:** **Artifact Registry gives only 0.5 GB free**, so SHA-tagged images overflow it within a few pushes unless you set a cleanup policy. **Secret Manager gives only 6 active secret versions free**, so you must destroy old versions on rotation. *(HIGH: GCP Free Tier docs.)*
4. **FastAPI 0.143 now has built-in OpenTelemetry** (traces, metrics, and logs, enabled by default; OTLP auto-export is opt-in). Do not add `opentelemetry-instrumentation-fastapi` on top of it. Use `prometheus-client` for Prometheus metrics and turn off FastAPI's built-in HTTP metrics so nothing is counted twice. *(HIGH: FastAPI docs and release notes.)*
5. **kind v0.33.0 defaults to Kubernetes 1.37, but Argo CD 3.5 is only tested on 1.33–1.36.** Pin the node image to `kindest/node:v1.36.4@sha256:099e0493...`. *(HIGH: kind release notes and Argo CD install docs.)*
6. **Argo Workflows v4 CRDs must be applied with `--server-side`.** The plain `kubectl apply` shown in the release notes will fail on the full CRDs. *(HIGH: Argo Workflows install docs.)*
7. **The Terraform google provider is at 8.7.0, and the repo pins `~> 5.0`.** That jump crosses 3 major versions; 8.0 changed load balancer defaults and removed resources. Because the data is demo-only, start fresh state on `~> 8.7` rather than stepping through 6 and 7. *(MEDIUM: HashiCorp 8.0 GA blog plus secondary write-ups.)*

---

## Recommended Stack

### Core Technologies (backend runtime)

| Technology | Version | Purpose | Why Recommended | Conf. |
|---|---|---|---|---|
| Python | 3.13 (`python:3.13-slim`, latest patch 3.13.16) | Runtime | Matches the PROJECT.md constraint and is supported until 2029-10. Bump the Dockerfile from 3.12 to 3.13 so local, CI, and container all agree. 3.14 and 3.15 exist but give no benefit here. | HIGH |
| FastAPI | `0.143.0` (install as `fastapi[standard]`) | HTTP API | The `[standard]` extra brings in `python-multipart`, `uvicorn[standard]`, `pydantic-settings`, `httpx`, and the OTel SDK and OTLP exporter. That fixes the known missing `python-multipart` gap in one line. Note: 0.143 made OTel exporter auto-config opt-in (`FASTAPI_OTEL_AUTO_CONFIGURE`). | HIGH |
| Starlette | `1.8.0` (transitive) | ASGI | Starlette 1.x is now current. Pin it through `uv.lock`, not by hand. | HIGH |
| Uvicorn | `0.54.0` | ASGI server | **Run with `--proxy-headers --forwarded-allow-ips='*'` on Cloud Run** so `request.url.scheme` is `https`. Twilio signature checks need this (see below). | HIGH |
| Pydantic / pydantic-settings | `2.14.1` / `2.15.0` | Models / config | Already in use. Unify project, region, port, and model in one `Settings`. | HIGH |
| google-genai | `2.30.1` | Gemini client | 2.0.0 (2026-05-07) only broke the *Interactions* API. The `generate_content` path is unaffected, so `>=1.0` code upgrades cleanly. Use `client.aio`, `AutomaticFunctionCallingConfig(disable=True)`, `HttpOptions(retry_options=HttpRetryOptions(...))` for 429/5xx retries, and `response.usage_metadata.{prompt,candidates,thoughts,tool_use_prompt}_token_count` for cost metrics. | HIGH |
| Gemini model | `GEMINI_MODEL` setting. Default `gemini-2.5-flash` (current behavior); eval candidates `gemini-3.5-flash-lite`, `gemini-3.8-flash` | Agent LLM | All have a free tier. 2.5 Flash costs $0.30/$2.50 per MTok on paid. 3.5 Flash-Lite costs $0.30/$2.50. 3.8 Flash costs $0.75/$3.75 now, rising to $1.50/$7.50 on 2027-01-01. Choosing the model from eval results makes a strong portfolio story. **Stay on the AI Studio API key, not Vertex.** Vertex AI Gemini is billed with no free tier (MEDIUM: training data, not re-verified). | HIGH |
| twilio | `9.12.0` | SMS send + `RequestValidator` | `twilio.request_validator.RequestValidator(token).validate(url, params, signature)` handles port and no-port variants and uses constant-time compare. For async sends, use `Client(..., http_client=AsyncTwilioHttpClient())` with `messages.create_async(...)` (verified present in 9.12.0) instead of calling sync `create()` inside `async def`. | HIGH |
| google-cloud-firestore | `2.34.1` | Datastore | Existing `AsyncClient`. Use transactions or `create()` on a slug-keyed doc to make slugs unique. | HIGH |
| google-cloud-storage | `3.17.0` | Photos | 3.x is a major bump from `>=2.19`. Replace `blob.make_public()` (fails under UBLA) with bucket-level `roles/storage.objectViewer` for `allUsers` on a `public/` prefix bucket, or with signed URLs. | MEDIUM |

### Secrets

| Technology | Version | Purpose | Why | Conf. |
|---|---|---|---|---|
| **Cloud Run secret env refs** (Terraform `google_cloud_run_v2_service` → `env.value_source.secret_key_ref`) | n/a | Inject secrets as env vars | The app stays `pydantic-settings`-driven with no SDK and no code change. Secrets are read once per instance start, far under the 10k free access ops per month. **Recommended.** | HIGH |
| google-cloud-secret-manager | `2.31.0` | Runtime secret access | **Use only** in an `apps/api/scripts/` helper or in the eval harness when running outside Cloud Run. Do not add it to the request path. | HIGH |
| Kubernetes Secret from local `.env` (scripted, not committed) | n/a | Secrets on kind | Simplest $0 option. External Secrets Operator would need a long-lived GCP SA key on the laptop, which contradicts the keyless story. | MEDIUM |

**Secret budget (6 free active versions):** `GOOGLE_API_KEY`, `TWILIO_AUTH_TOKEN`, `RENCI_EMAIL_APP_PASSWORD`, `INTERNAL_API_TOKEN` (for poll trigger and agent toggle) = 4. `TWILIO_ACCOUNT_SID` and `TWILIO_PHONE_NUMBER` are not secret, so put them in plain env. `ANTHROPIC_API_KEY` lives only in GitHub Actions secrets and never in GCP. On rotation, `gcloud secrets versions destroy` the old version.

### Agent Evaluation

| Technology | Version | Purpose | Why | Conf. |
|---|---|---|---|---|
| **Custom pytest harness** (`apps/api/evals/`) | pytest `9.1.1`, pytest-asyncio `1.4.0` | Golden + adversarial suites, tool-call accuracy, task success, latency and cost | The agent is stateful: Firestore, registration steps, and server-bound `business_id`. Deterministic metrics such as tool name/args match, cross-tenant write attempts, and language match need **in-process access to the manual tool loop and a fake Firestore**. A framework can't see those without an adapter anyway. Writing this harness is also the skill the target role wants to see. Datasets go in YAML/JSONL; results go to `evals/results/<sha>.json`, plus a JUnit XML for the CI gate. | MEDIUM (opinion) |
| anthropic | `1.13.0` | Claude as LLM judge | Use `client.messages.parse(model=..., output_format=JudgeVerdict, ...)` (a Pydantic model; structured outputs verified in SDK 1.13). That returns typed scores, not regex-parsed text. Judge model: **`claude-haiku-5-5`** for PR runs (from $0.10/$0.50 per MTok) and **`claude-sonnet-5-5`** ($2/$10) for nightly. Use the Batch API (50% off) for nightly. Both are retained until at least September/October 2027. | HIGH (API) / MEDIUM (model choice) |
| Inspect AI (optional, stretch) | `0.3.280` | Recognized eval framework and log viewer | UK AISI. Supports both `google/` and `anthropic/` providers, custom tool-using solvers, `model_graded_qa`, and `inspect view`. Worth adding later as a second front end over the same dataset if reviewers value a named framework. Not needed for v1. | MEDIUM |

**Judge cost (not GCP, but real money; flag to user):** about 150 cases × ~2k input / 300 output tokens is roughly $1 per run on Sonnet 5.5 and a few cents on Haiku 5.5. The PR gate should run **deterministic metrics on every PR**, and run the judge only on a label or nightly.

**Gemini free-tier rate limits** will throttle a 150-case eval run. Use `asyncio.Semaphore` concurrency of 2–4, plus `HttpRetryOptions` on 429.

### Japanese Support

| Technology | Version | Purpose | Why | Conf. |
|---|---|---|---|---|
| **Extend existing `language/detector.py` (stdlib regex, zero deps)** | n/a | EN / zh-Hans / zh-Hant / ja detection | Any Hiragana (`぀-ゟ`) or Katakana (`゠-ヿ`, `ㇰ-ㇿ`, half-width `ｦ-ﾟ`) means `ja`. This is deterministic, instant, and testable. **Precedence:** stored `owners.language` preference first, then script heuristic, then fallback. Kanji-only short messages such as 「明日休業」 are inherently ambiguous between ja and zh, so the owner's stored preference must win. | HIGH (approach) |
| fast-langdetect (optional fallback) | `1.0.1` | Ambiguous all-Han and Latin text | 0.8 MB wheel plus 0.3 MB `fasttext-predict`, bundling the ~1 MB lite model. Use only when the heuristic is unsure. Use the lite model only; the full model is a 126 MB download. | MEDIUM |
| Japanese tokenizer | **none** | n/a | Not needed. Gemini handles Japanese natively, and reply quality is scored by the Claude judge, not BLEU or token overlap. If you later need segmentation, use SudachiPy `0.7.0` with sudachidict-core `20260723.1`. | HIGH |
| Web i18n | add `apps/web/src/lib/i18n/ja.json` | UI strings | Same JSON-dictionary pattern as en/zh. No new library. | HIGH |

### Observability

| Technology | Version | Purpose | Why | Conf. |
|---|---|---|---|---|
| **structlog** | `26.1.0` | Structured JSON logs | Uses a processor chain. Add a custom processor that renames `level`→`severity` (uppercase) and `event`→`message`, and adds `logging.googleapis.com/trace = projects/<PROJECT>/traces/<id>` from `X-Cloud-Trace-Context` (the part before `/`) or from `traceparent`. Bind `request_id`, `business_id`, `channel`, and `tool` with `contextvars`. Use the JSON renderer on Cloud Run and the console renderer locally. Route stdlib `logging` (uvicorn, google libs) through `structlog.stdlib.ProcessorFormatter`. | HIGH |
| Cloud Run stdout ingestion | n/a | Log transport | Cloud Run parses JSON lines on stdout. `severity`, `message`, and `logging.googleapis.com/trace` are lifted into the LogEntry, and the trace field nests app logs under the request log. 50 GiB/month free. | HIGH |
| prometheus-client | `0.26.0` | `/metrics` | Domain metrics: `renci_tool_calls_total{tool,outcome}`, `renci_llm_tokens_total{model,kind}`, `renci_llm_cost_usd_total{model}`, `renci_agent_latency_seconds` (histogram), `renci_channel_messages_total{channel}`. | HIGH |
| prometheus-fastapi-instrumentator | `8.1.0` | HTTP RED metrics | Requires `starlette>=1.0`, so it is compatible. Exclude `/metrics` and `/health`. Then set `FastAPI(telemetry={"metrics": False})` so FastAPI's built-in OTel HTTP metrics don't duplicate it. | HIGH (version) / MEDIUM (combo) |
| FastAPI built-in OTel tracing | (bundled in 0.143) | Spans | Free to keep on. Exporting to Cloud Trace is optional and deferrable. If done, use `opentelemetry-exporter-gcp-trace` `1.15.0` via `telemetry={"tracer_provider": ...}`. Cloud Trace's free span allotment was **not verified** (pricing URL 404'd); training data says 2.5M spans/month. | LOW (free tier) |
| **Do not use** google-cloud-logging `3.17.0` | n/a | n/a | Its `StructuredLogHandler` auto-detects request trace only for Flask and Django, not FastAPI. Its API-transport handler makes network calls per log batch. Plain stdout JSON is simpler and free. | MEDIUM |

**`/metrics` on Cloud Run:** do not expose it publicly. Gate it behind the `INTERNAL_API_TOKEN` header, or serve it only when `APP_ENV != prod`. Prometheus on kind scrapes the kind deployment of the API, not Cloud Run.

### Kubernetes / GitOps (local kind, $0)

| Technology | Version | Install method | Why / Notes | Conf. |
|---|---|---|---|---|
| kind | `v0.33.0` | `winget install Kubernetes.kind` (Windows) / `helm/kind-action@v1.15.1` (CI) | **Pin node image** `kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed` in `kind-config.yaml`. The default 1.37 is outside Argo CD 3.5's tested range (1.33–1.36). | HIGH |
| kubectl | match node: 1.36.x | Docker Desktop's bundled one or winget | | HIGH |
| Argo CD | `v3.5.5` (Helm chart `argo-cd-10.10.3` if using Helm) | **Bootstrap once:** `kubectl create ns argocd && kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml`. After that, everything else, Argo CD itself included, is managed by a root app-of-apps `Application`. | Pin the tag, never `stable`. Server-side apply avoids the CRD annotation-size limit (MEDIUM). | HIGH |
| Argo Workflows | `v4.1.5` (Helm chart `argo-workflows-2.0.12`) | `kubectl create ns argo && kubectl apply -n argo --server-side -f https://github.com/argoproj/argo-workflows/releases/download/v4.1.5/install.yaml`, or deploy as an Argo CD Application from the chart. Locally, patch the server to `--auth-mode=server`. CLI from the release `argo-windows-amd64.gz`. | v4 ships full validating CRDs that **require server-side apply**. Use `CronWorkflow` for the nightly eval and the email poll, and `WorkflowTemplate` for reuse. | HIGH |
| Kustomize | `v5.8.3` (also built into `kubectl -k`; Argo CD bundles its own) | n/a | **Use Kustomize for our own manifests** (`deploy/k8s/base` plus `overlays/kind`): plain YAML, readable in review, and native to Argo CD. | HIGH |
| Helm | `v4.3.0` | winget / CI | **Use Helm only for third-party charts** (kube-prometheus-stack, optionally argo-workflows), declared as Argo CD `Application`s with `spec.source.chart` and a pinned `targetRevision`. Do not author a Helm chart for the app; templating two Deployments is over-engineering. | MEDIUM (opinion) |
| kube-prometheus-stack | chart `92.4.0` (operator `v0.94.1`, `kubeVersion >=1.25`) | Argo CD Application → `https://prometheus-community.github.io/helm-charts` | Gives Prometheus, Grafana, Alertmanager, and the operator CRDs. Add `ServiceMonitor` for the API, `PrometheusRule` for SLO burn-rate alerts, and dashboards as ConfigMaps labelled `grafana_dashboard: "1"` (sidecar). Trim for kind: disable `kubeEtcd`, `kubeControllerManager`, `kubeScheduler`, and `kubeProxy` scrapes (they fail on kind) and set small resource requests. Needs `ServerSideApply=true` in syncOptions (large CRDs). | HIGH (version) / MEDIUM (tuning) |
| Sloth (optional) | `v0.16.0` | CLI in CI | Generates multi-window multi-burn-rate `PrometheusRule`s from a short SLO spec. Hand-writing 2 SLOs is also fine. | MEDIUM |
| Image registry for kind | **GHCR** (public) | `docker/login-action@v4.6.0` with `GITHUB_TOKEN` | kind can't pull from private Artifact Registry without a key. Public GHCR is free and keeps AR under 0.5 GB. CI pushes the same SHA-tagged image to both. | MEDIUM |

### CI/CD (GitHub Actions)

| Action / Tool | Version | Purpose | Notes | Conf. |
|---|---|---|---|---|
| actions/checkout | `v7` (7.0.1) | | Must come before `auth`. | HIGH |
| astral-sh/setup-uv | `v10` (10.3.0) | Python + deps | `enable-cache: true`; `uv sync --locked`. | HIGH |
| actions/setup-node | `v7` (7.1.0) | Web check/build | | HIGH |
| google-github-actions/auth | `v3` | Keyless GCP auth | Needs `permissions: { contents: read, id-token: write }`. Use **WIF through a deployer service account** (`service_account:` input), not direct WIF. Pushing to Artifact Registry and `gcloud run deploy` with `--service-account` need an SA identity, so direct `principalSet` grants don't cover everything. Provider attribute condition: `assertion.repository == 'wolfwdavid/renci' && assertion.ref == 'refs/heads/main'` for the deploy provider. PRs use a separate plan-only SA with read roles. Runs on Node 24. | HIGH (action) / MEDIUM (SA-vs-direct choice) |
| google-github-actions/setup-gcloud | `v3` (3.0.1) | gcloud CLI | | HIGH |
| google-github-actions/deploy-cloudrun | `v3` | Deploy by image digest | Deploy `image@sha256:...`, never `:latest`. | HIGH |
| docker/setup-buildx-action / build-push-action / metadata-action | `v4.4.1` / `v7.4.0` / `v6.2.0` | Build and tag `:${{ github.sha }}` | Use `cache-to: type=gha`. | HIGH |
| hashicorp/setup-terraform | `v4` (4.0.1) | fmt/validate/plan | | HIGH |
| helm/kind-action | `v1.15.1` | Optional CI smoke test (`kubectl apply -k` and rollout check on ephemeral kind) | | HIGH |
| actions/upload-artifact | `v7` (7.0.2) | Eval results JSON / JUnit | | HIGH |

### Infrastructure as Code

| Technology | Version | Purpose | Why / Notes | Conf. |
|---|---|---|---|---|
| Terraform CLI | `1.16.5` (`required_version = "~> 1.16"`) | IaC | Matches the role's keyword (Terraform, not OpenTofu). | HIGH |
| hashicorp/google provider | `8.7.0` (`version = "~> 8.7"`) | GCP resources | Current repo `~> 5.0` is 3 majors stale. 8.0 flipped the default `load_balancing_scheme` to `EXTERNAL_MANAGED` for backend services and global forwarding rules, removed retired-service resources, and turned some lists into sets. Write the new LB module against 8.x from the start. | HIGH (version) / MEDIUM (change list) |
| Layout | two root modules | Applied vs plan-only | `infra/terraform/live/` holds the free-tier resources that are **applied**: Cloud Run v2 ×2, Artifact Registry with `cleanup_policies` keeping the last 3 per image, Secret Manager, WIF pool and providers, deployer SA, Firestore, and GCS. `infra/terraform/showcase/` holds the GKE Autopilot, VPC, and HTTPS LB modules: **`terraform plan` only**, separate state prefix, with **no apply job in CI at all**. That way paid resources can't be created by accident. | HIGH (opinion, $0-critical) |
| State backend | GCS bucket in `us-central1` | Remote state | Inside the 5 GB free regional storage (us-east1, us-west1, us-central1 only). Pick **us-central1** for everything; it matches the live services. | HIGH |
| TFLint + google ruleset | `v0.64.0` + `tflint-ruleset-google v0.40.0` | Lint | | HIGH |
| Trivy (config scan) | `v0.75.0` | IaC / image misconfig scan | Optional. Pin the binary by version and checksum, not a floating action tag. | MEDIUM |

### Development Tools (Python)

| Tool | Version | Purpose | Notes | Conf. |
|---|---|---|---|---|
| uv | `0.13.1` | Package/env manager, lockfile | Replace `requirements.txt` with `apps/api/pyproject.toml` + `uv.lock`. Dockerfile: `COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /bin/uv` then `uv sync --locked --no-dev`. Works the same in Git Bash and Linux CI. | HIGH |
| ruff | `0.17.0` | Lint + format | Replaces black, isort, and flake8. Enable `S` (bandit), `ASYNC`, `B`, `UP`, `I`. `ASYNC` catches blocking calls in async functions, which is directly relevant to the known bugs. | HIGH |
| mypy | `2.4.0` | Type check (CI gate) | Stable and the most recognized choice. Use `strict = true` on new modules (`evals/`, `observability/`, `security/`) and gradual elsewhere. | HIGH |
| ty | `0.0.87` | n/a | **Don't use yet.** Still pre-1.0. | HIGH |
| pytest / pytest-asyncio | `9.1.1` / `1.4.0` | Tests | Set `asyncio_mode = "auto"` in pyproject. | HIGH |
| respx | `0.23.1` | Mock httpx (Twilio media fetch) | | HIGH |
| pre-commit (optional) | hooks `v6.0.0` | Local gate | | MEDIUM |

## Installation

```bash
# apps/api (uv-managed; versions are lower bounds, uv.lock holds exact pins)
uv add "fastapi[standard]>=0.143" "uvicorn[standard]>=0.54" "google-genai>=2.30.1" \
       "twilio>=9.12" "google-cloud-firestore>=2.34" "google-cloud-storage>=3.17" \
       "pydantic>=2.14" "pydantic-settings>=2.15" "structlog>=26.1" \
       "prometheus-client>=0.26" "prometheus-fastapi-instrumentator>=8.1" "pandas>=3.0"
# optional
uv add "fast-langdetect>=1.0.1"
# dev + eval
uv add --dev "pytest>=9.1" "pytest-asyncio>=1.4" "respx>=0.23" "ruff>=0.17" "mypy>=2.4" \
             "anthropic>=1.13" "google-cloud-secret-manager>=2.31"
```

```bash
# local cluster (Git Bash on Windows)
kind create cluster --name renci --config deploy/kind/kind-config.yaml   # node v1.36.4@sha256 pinned
kubectl create ns argocd
kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml
kubectl apply -n argocd -f deploy/argocd/root-app.yaml   # app-of-apps: workflows, monitoring, renci
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|---|---|---|
| Manual tool loop (AFC disabled) | AFC with `client.aio` and async tools | Only for stateless tools with no tenant or authorization context. AFC hides the call list from metrics and can't inject `business_id`. |
| Custom pytest eval harness | **Inspect AI 0.3.280** | Add as a second front end if a named framework or log viewer is wanted. Best of the frameworks for tool-using agents. |
| Custom pytest eval harness | DeepEval 4.2.8 | Teams that want Confident AI hosting. It has 31 runtime deps, nudges toward a SaaS login, and its built-in metrics don't see our in-process tool state. |
| Custom pytest eval harness | promptfoo 0.124.1 (Node) | Prompt-level red-teaming of a stateless endpoint. It adds Node to the Python eval path, conflicts with the "Python-only backend" decision, and can't inspect Firestore side effects. |
| structlog | python-json-logger 4.2.0 | A minimal drop-in JSON formatter if you don't want contextvars binding. Fine, but you'd hand-roll the trace and context plumbing structlog already gives you. |
| prometheus-client + instrumentator | OTel metrics via `opentelemetry-exporter-prometheus` 0.66b1 | If you standardize on OTel end-to-end. The exporter is still `b` (beta) versioned, and Prometheus-native names are what Grafana dashboards and SLO rules expect. |
| Kustomize (own app) | Helm chart for app | If the app had many environments or values-driven variants. Here there is one overlay (kind). |
| WIF via service account | Direct WIF (`principalSet`) | Read-only jobs like `terraform plan` or secret reads, where no SA token is needed. |
| Stdlib script heuristic | lingua-language-detector 2.2.0 | Never here. The **wheel is 170 MB**, which by itself is a third of the 0.5 GB Artifact Registry free tier. |
| GHCR for kind images | Artifact Registry + pull secret | If the repo is private. That needs an SA key on the laptop, which is not keyless. |

## What NOT to Use

| Avoid | Why | Use Instead |
|---|---|---|
| `client.models.generate_content` (sync) inside `async def` | Blocks the event loop. AFC raises `UnsupportedFunctionError` for coroutine tools on the sync path. | `await client.aio.models.generate_content(...)` |
| Model-supplied `business_id` tool parameter | Cross-tenant prompt injection | Remove it from tool signatures and inject it from the authenticated sender in the manual loop |
| `google-adk` | Not used. Docstrings wrongly claim it. Adding it now is churn without benefit. | Fix the docstrings and keep `google-genai` directly |
| Vertex AI Gemini (`USE_VERTEX_AI=true`) in prod | Billed with no free tier (MEDIUM) | AI Studio API key from Secret Manager |
| Rebuilding the Twilio URL from `X-Forwarded-Host` | Spoofable and brittle | A `PUBLIC_BASE_URL` setting + `request.url.path` + query → `RequestValidator.validate`. In tests, sign with `compute_signature`. No "skip in debug" bypass. |
| `CORSMiddleware(allow_origins=["*"], allow_credentials=True)` | Invalid and unsafe combination | Explicit origin list from settings |
| `:latest` image tags / `gcloud run deploy --source` | Drift; non-reproducible | SHA tag + digest deploy from CI |
| Service-account JSON keys in GitHub secrets | Long-lived credential | WIF (`google-github-actions/auth@v3`) |
| `opentelemetry-instrumentation-fastapi` | Duplicates FastAPI 0.143's built-in instrumentation | `FastAPI(telemetry={...})` |
| google-cloud-logging `StructuredLogHandler` / API handler | No FastAPI request detection; API handler makes network calls | structlog → stdout JSON |
| lingua-language-detector | 170 MB wheel | Regex script heuristic (+ fast-langdetect lite) |
| ty, Pyright-as-gate | ty is pre-1.0; two type checkers is noise | mypy 2.4 |
| Argo CD/Workflows `stable`/`latest` URLs | Unpinned GitOps defeats the purpose | Tag-pinned URLs / chart `targetRevision` |
| Default kind node (1.37) | Outside Argo CD 3.5's tested range | `kindest/node:v1.36.4@sha256:...` |
| In-process email poller on Cloud Run | Scale-to-zero kills it | Authenticated `POST /internal/email/poll` triggered by an Argo `CronWorkflow` |
| Cloud Scheduler as the poll trigger | Free tier not verified on the current free-features page; also redundant with Argo | Argo CronWorkflow (note: it runs only while kind is up, an accepted portfolio trade-off) |
| `tenacity>=9.2` pinned by hand | `google-genai` 2.30.1 requires `tenacity<9.2.0`, so a hand pin causes a resolver conflict | `HttpRetryOptions` in google-genai, or let uv resolve tenacity |

## Stack Patterns by Variant

**PR CI (every push to a PR):**
- ruff check, ruff format --check, mypy, pytest (unit), `svelte-check`, `terraform fmt -check` + `validate` + tflint (both roots), `terraform plan` (live + showcase, via the read-only WIF SA), eval **deterministic suite** with mocked or recorded Gemini.
- Because: fast, free, and no judge spend per push.

**Eval gate (label `run-evals`, or nightly Argo CronWorkflow / scheduled Action):**
- Live Gemini (free tier, concurrency 2–4) + Claude judge (Haiku on PR, Sonnet nightly), results JSON committed or uploaded, compared to a baseline threshold.
- Because: real model behavior is non-deterministic and costs judge tokens.

**main merge:**
- Build → push GHCR + Artifact Registry (`:sha`) → deploy Cloud Run by digest → bump the image tag in `deploy/k8s/overlays/kind/kustomization.yaml` (commit from CI) → Argo CD on kind syncs it.

## Version Compatibility

| Package A | Compatible With | Notes |
|---|---|---|
| google-genai 2.30.1 | pydantic ≥2.12.5, httpx ≥0.28.1, **tenacity <9.2.0** | Pin nothing transitive by hand; trust `uv.lock`. |
| prometheus-fastapi-instrumentator 8.1.0 | starlette ≥1.0 (<2) | FastAPI 0.143 resolves Starlette 1.8.0, so this works. |
| fastapi 0.143.0 | opentelemetry-api ≥1.44 (now a hard dep) | OTel API always installed; SDK/exporter via `[standard]`. |
| anthropic 1.13.0 | `httpx2` (separate package from `httpx`) | Both coexist; it's a dev/eval-only dependency anyway. |
| lingua-language-detector 2.2.0 | Python ≥3.12 | Irrelevant: not recommended. |
| pandas 3.0.6 | Python ≥3.11 | **Major bump from 2.x.** Copy-on-write and the new default string dtype can change PPP lookup behavior. Run the existing PPP tests after upgrading, or replace pandas with the stdlib `csv` module (saves ~27 MB of wheels toward the AR budget). |
| google-cloud-storage 3.17.0 | — | Major bump from 2.x. Re-check the upload path. |
| Argo CD v3.5.5 | Kubernetes 1.33–1.36 (tested) | Hence the kind node pin. |
| Argo Workflows v4.1.5 | server-side apply required | `kubectl apply --server-side`; Argo CD app needs `ServerSideApply=true`. |
| kube-prometheus-stack 92.4.0 | kubeVersion ≥1.25 | OK on 1.36. |
| google provider 8.7.0 | Terraform ≥1.x (use 1.16.5) | LB default scheme changed in 8.0. |
| google-github-actions/auth v3 | Node 24 runners | `ubuntu-latest` is fine. |

## $0 Budget Checklist (flag to roadmap)

| Resource | Free allotment (verified 2026-10-14) | Risk | Mitigation |
|---|---|---|---|
| Artifact Registry | **0.5 GB** storage | HIGH: 2 images × N SHAs overflows quickly | `cleanup_policies` keep-latest-3, slim images (uv, no dev deps, maybe drop pandas), GHCR for kind |
| Secret Manager | **6 active versions**, 10k access ops, 3 rotation notifications | MEDIUM | ≤5 secrets; destroy old versions on rotate |
| Cloud Run | 2M req, 180k vCPU-s, 360k GiB-s, 1 GB egress (NA) | LOW | `min-instances=0`, `max-instances` ≤3 |
| Firestore | 1 GiB, 50k reads / 20k writes per day | LOW (eval runs use a fake or emulator, not prod) | Eval harness never hits prod Firestore |
| Cloud Storage | 5 GB-months, **us-east1/us-west1/us-central1 only** | LOW | Everything in us-central1 |
| Cloud Logging | 50 GiB/project | LOW | INFO level; don't log full prompts at INFO |
| Cloud Build | 2,500 min e2-standard-2 | n/a | Retire `infra/cloudbuild.yaml`; build in GitHub Actions |
| GKE Autopilot / LB / VPC | One free Autopilot cluster *management fee* only; compute, LB, and NAT bill | **Would cost money** | Plan-only root, no apply job exists |
| Gemini API (AI Studio) | Free tier on 2.5 Flash / 3.5 Flash-Lite / 3.6 and 3.8 Flash; **free-tier data "used to improve products"** | Rate limits | Demo data only; throttle evals |
| Anthropic (judge) | **No free tier; not GCP** | About $1 per Sonnet run | Haiku on PR, Batch API nightly, label-gated |
| Cloud Trace | **Not verified** | LOW | Defer export |

## Sources

- PyPI JSON API (`https://pypi.org/pypi/<pkg>/json`), queried 2026-10-14: all Python versions, `requires_dist`, and wheel sizes. HIGH
- GitHub releases API for kind, argo-cd, argo-workflows, argo-helm, terraform, terraform-provider-google, google-github-actions/*, kustomize, helm, prometheus-community/helm-charts, setup-uv, docker/*, tflint, trivy, ty, and sloth. HIGH
- kind v0.33.0 release notes (default node 1.37.0, digest list). HIGH
- https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/ (tested Kubernetes 1.33–1.36; server-side apply for CRDs). HIGH
- https://argo-workflows.readthedocs.io/en/latest/installation/ (v4 full CRDs require server-side apply). HIGH
- https://ai.google.dev/gemini-api/docs/models, /deprecations, /pricing (model IDs, 2.5 Flash access note, free tier, prices). HIGH
- google-genai 2.30.1 wheel source: `_extra_utils.py` (async AFC on `aio` path; sync path raises for coroutines), `types.py` (`HttpRetryOptions`, `usage_metadata` fields). HIGH
- googleapis/python-genai CHANGELOG 2.0.0 (breaking changes limited to Interactions). HIGH
- twilio 9.12.0 wheel: `request_validator.py`, `AsyncTwilioHttpClient`, `create_async`. HIGH
- https://www.twilio.com/docs/usage/tutorials/how-to-secure-your-flask-app-by-validating-incoming-twilio-requests (URL/proxy pitfalls). HIGH
- anthropic 1.13.0 wheel (`messages.parse(output_format=...)`, `output_config`); https://platform.claude.com/docs/en/models/overview (model IDs, prices, retirement dates). HIGH
- https://fastapi.tiangolo.com/advanced/opentelemetry/ and FastAPI 0.143.0 release notes (built-in OTel, opt-in auto-config). HIGH
- https://docs.cloud.google.com/run/docs/logging (special JSON fields, `X-Cloud-Trace-Context` correlation). HIGH
- https://docs.cloud.google.com/free/docs/free-cloud-features (free-tier limits). HIGH
- https://github.com/google-github-actions/auth (v3, Node 24, WIF modes, attribute conditions). HIGH
- https://hashicorp.com/blog/terraform-provider-for-google-cloud-80-now-generally-available + https://infoq.com/news/2026/10/terraform-google-cloud-provider (8.0 breaking changes). MEDIUM
- https://inspect.aisi.org.uk/ (providers, tool-calling, model-graded scorers). MEDIUM
- https://deepeval.com/docs/getting-started (pytest integration, Confident AI positioning). MEDIUM
- Vertex AI Gemini having no free tier, and Cloud Trace 2.5M free spans: training data only. LOW, flagged inline.
