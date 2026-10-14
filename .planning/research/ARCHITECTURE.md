# Architecture Research

**Domain:** Production-hardening of a multi-channel LLM tool-calling agent (FastAPI + Gemini + Firestore) with eval, GitOps (Cloud Run + local kind/ArgoCD), IaC, and observability, all at $0 GCP spend
**Researched:** 2026-10-14
**Confidence:** MEDIUM-HIGH (app-level patterns HIGH; free-tier billing edges MEDIUM; tool versions MEDIUM)

---

## Standard Architecture

### Guiding principle

**One application, two thin trigger surfaces, two deployment targets, one source of config.**
Every new capability (security, jobs, eval, metrics) goes in the Python app as a plain module with a stable interface. Cloud Run and kind differ only in (a) who triggers jobs, (b) where secrets/data come from, (c) where telemetry lands. Nothing about business logic may differ between targets.

### System Overview (target state)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                      INBOUND (untrusted)                                       │
│  Twilio SMS        Web chat (SvelteKit)       Cloud Scheduler / Argo Cron      │
│  POST /webhooks/sms POST /webhooks/chat       POST /internal/jobs/* | CLI      │
├────────┬──────────────────┬──────────────────────────┬─────────────────────────┤
│ CHANNEL AUTH (new, apps/api/security/)                                          │
│  twilio_sig.verify   chat_session.verify (signed   internal_auth.verify_oidc    │
│  (X-Twilio-Signature) cookie -> sandbox identity)  (Google OIDC aud+SA email)   │
│        │                  │                                   │                 │
│        └──────► VerifiedSender(channel, identity, msg_id) ◄───┘ (email job)     │
├─────────────────────────────────────────────────────────────────────────────────┤
│ IDENTITY + ROUTER  apps/api/sms/router.py -> apps/api/identity/                  │
│  normalize(identity) -> owners/{e164|web:sid} (doc-ID keyed, create() idempotent)│
│  builds RequestContext(owner_id, business_id, language, channel, trace_id)      │
├──────────────────────┬──────────────────────────────────────────────────────────┤
│ REGISTRATION FSM     │ AGENT RUNTIME  apps/api/agent/                            │
│ (deterministic)      │  runner.run(ctx, message) ── ModelClient port ──► Gemini  │
│                      │     │ manual function-calling loop (AFC disabled)         │
│                      │     ▼                                                     │
│                      │  ToolExecutor: schema has NO business_id/language;        │
│                      │  validates args (Pydantic, extra=forbid), injects ctx,    │
│                      │  emits telemetry + audit event per call                   │
├──────────────────────┴──────────────────────────────────────────────────────────┤
│ REPOSITORY PORT  apps/api/db/  (Firestore impl | in-memory fake for tests/evals) │
│  owners/{id}  businesses/{id}  slugs/{slug}  processed_messages/{id}            │
│  eval_runs/{run_id}  usage_daily/{date}  config/email_poller                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ TELEMETRY  apps/api/observability/                                               │
│  JSON logs (stdout, Cloud Logging schema, trace field)  prometheus_client registry│
└─────────────────────────────────────────────────────────────────────────────────┘

DEPLOYMENT TARGETS (same image digest, same config base)
┌───────────────────────────────┐        ┌───────────────────────────────────────┐
│ GCP (real, $0)                │        │ Local kind (ArgoCD-managed)            │
│ Cloud Run api + web           │        │ ArgoCD app-of-apps -> deploy/k8s/...   │
│ Cloud Scheduler -> /internal  │        │ Argo Workflows CronWorkflows:          │
│ Secret Manager env refs       │        │   email-poll, nightly-eval             │
│ Firestore (real)              │        │ Firestore emulator pod                 │
│ Cloud Logging (stdout JSON)   │        │ kube-prometheus-stack + Pushgateway    │
│ Cloud Run built-in metrics    │        │ ServiceMonitor, PrometheusRule (SLO)   │
└───────────────────────────────┘        └───────────────────────────────────────┘
         ▲  deploy by digest                         ▲  git (Kustomize image tag)
         └────────── GitHub Actions (WIF) ───────────┘
                     build once -> push to AR + GHCR
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `security/twilio_sig.py` | Reject unsigned SMS webhooks; constrain MediaUrl host to `api.twilio.com`, no cross-host redirects | `twilio.request_validator.RequestValidator` against configured `PUBLIC_BASE_URL` (never `request.url`, which is the internal URL behind Cloud Run's front end) |
| `security/internal_auth.py` | Authenticate job triggers | Cloud Run: verify Google OIDC ID token (`google.oauth2.id_token.verify_oauth2_token`), check `aud` and `email == scheduler SA`. kind: jobs run as CLI in-cluster, no HTTP auth needed |
| `security/chat_session.py` | Web chat identity | Server-issued signed session (itsdangerous/HMAC) mapping to `web:{session_id}` sandbox owner. Client never sends an identity. Remove `from_address` from the public API |
| `identity/` | Single place that normalizes channel identity to an owner key | E.164 for SMS/gateway email, `web:{sid}` for chat; `owners/{key}` doc IDs with `create()` so duplicates are impossible |
| `agent/context.py` | `RequestContext` frozen dataclass | Built by router only; the only source of `business_id`/`language` for tools |
| `agent/runner.py` | Manual function-calling loop over `ModelClient` | `client.aio.models.generate_content` with `AutomaticFunctionCallingConfig(disable=True)`; max N tool rounds; returns `AgentResult(text, tool_calls[], usage, latency)` |
| `agent/executor.py` | Tool registry + dispatch | Each tool = (Pydantic args model, async handler(ctx, args)); `FunctionDeclaration` generated from args model; unknown args rejected |
| `agent/model_client.py` | Port over Gemini | `GeminiClient` (live), `ReplayClient` (recorded cassettes for CI evals), `ScriptedClient` (unit tests) |
| `db/` repository port | Persistence abstraction | `FirestoreRepo` (prod/emulator) and `InMemoryRepo` (tests/evals) behind a Protocol |
| `jobs/poll_email.py` | One poll cycle, idempotent | `run_once() -> PollReport`; lease doc + `processed_messages/{Message-ID}` create(); invoked by HTTP route or `python -m jobs.poll_email` |
| `evals/` | Golden + adversarial datasets, scorers, runner, reporters | In-process against `agent.runner` with `InMemoryRepo`; optional HTTP mode for deployed smoke |
| `observability/` | Logging, metrics, trace correlation | JSON formatter emitting `severity`, `message`, `logging.googleapis.com/trace`; `prometheus_client` metrics; middleware for request IDs |
| `apps/web` dashboard | Eval + usage views | SvelteKit route `/dashboard` reading `GET /api/v1/evals`, `/api/v1/usage` (Firestore-backed) |
| `deploy/k8s` | Kustomize base + kind overlay | Deployments, Services, ConfigMaps, ServiceMonitor; Firestore emulator in overlay |
| `deploy/argocd` | App-of-apps root + child Applications | Points at `deploy/k8s/overlays/kind`, `deploy/workflows`, `deploy/monitoring`, Helm charts for platform add-ons |
| `infra/terraform/envs/free-tier` | Applied GCP resources | Cloud Run services (image ignored), AR, Secret Manager, WIF, Firestore, GCS, Scheduler job |
| `infra/terraform/envs/gke-plan` | Plan-only GKE/VPC/LB | Uses same modules; CI runs `plan` only; never applied |

---

## Answers to the Key Design Questions

### (a) Binding tenant identity server-side

**Recommendation: disable Gemini automatic function calling and run an explicit function-calling loop with a ToolExecutor that injects `RequestContext`.** Do not use closures/`functools.partial` with AFC.

Why:
- AFC infers the schema from the Python signature; any parameter the function has, the model can fill. Partials and closures are fragile with schema inference, and `ContextVar` + AFC leaves the parameter-surface question to SDK internals.
- google-genai (latest 2.30.1, 2026-10-13) explicitly warns: "We are changing AFC behavior in the next major version ... users will not be able to invoke AFC from direct calls to `Models.generate_content`" (including async variants). Building on AFC from `generate_content` is building on a deprecated path. **HIGH confidence** (PyPI page).
- A manual loop is also the seam the eval harness and telemetry need: every tool call passes through one function where you can record name, args, result, latency, and assert "no cross-tenant write".
- It fixes the async-tools-in-sync-client bug for free (handlers are awaited by your code).

Flow:
1. Channel auth produces `VerifiedSender`. 2. Router resolves owner, builds `RequestContext`. 3. Runner sends declarations whose schemas contain only user-meaningful args (`hours`, `phone`, `description`). 4. On `response.function_calls`, executor validates args with `extra="forbid"`, calls `handler(ctx, args)`; handler writes only to `ctx.business_id`. 5. Function responses appended; loop until text or max rounds (3-5).

Defense in depth: repository write methods for business data take `ctx` (not a raw id) and assert `ctx.owner_id` owns the business.

```python
# apps/api/agent/executor.py
class UpdateHoursArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: dict[str, str]

TOOLS: dict[str, Tool] = {
    "update_business_hours": Tool(UpdateHoursArgs, update_hours_handler,
                                  "Update the owner's business hours."),
}

async def execute(ctx: RequestContext, call: types.FunctionCall) -> dict:
    tool = TOOLS.get(call.name)
    if tool is None:
        return {"status": "error", "message": "unknown tool"}
    try:
        args = tool.args_model.model_validate(call.args or {})
    except ValidationError:
        TOOL_CALLS.labels(call.name, "rejected").inc()
        return {"status": "error", "message": "invalid arguments"}
    with TOOL_LATENCY.labels(call.name).time():
        result = await tool.handler(ctx, args)   # business_id comes from ctx only
    audit_log(ctx, call.name, args, result)
    return result
```

### (b) Replacing the in-process email poller at $0

**Recommendation: extract `jobs/poll_email.run_once()`; delete the lifespan poller and `/agent/toggle`; trigger it two ways.**

| Target | Trigger | Auth | Cost |
|--------|---------|------|------|
| Cloud Run | Cloud Scheduler HTTP job -> `POST /internal/jobs/poll-email` every 5 min | OIDC token from a dedicated `scheduler-invoker` SA; app verifies `aud` + `email`; Cloud Run IAM also grants `run.invoker` | 3 free jobs per billing account (verified, Cloud Scheduler pricing). ~8.6k invocations/month, well inside Cloud Run free requests/CPU |
| kind | Argo `CronWorkflow` running the API image with `command: [python, -m, jobs.poll_email]` | None needed (in-cluster) | $0 |

Required properties of `run_once()` (independent of trigger):
- **Mutual exclusion:** Firestore lease doc `locks/email-poller` (transactional acquire with expiry). CronWorkflow also sets `concurrencyPolicy: Forbid`; Cloud Scheduler can overlap if a run is slow, so the lease is the real guard.
- **Idempotency:** `processed_messages/{Message-ID}` created with `create()` before routing; skip if it exists. Fetch with `BODY.PEEK` and set `\Seen` only after success (fixes the mark-before-process loss).
- **Enabled flag in Firestore** (`config/email_poller.enabled`), replacing the per-instance `_running` global. The admin toggle, if kept, writes this doc behind internal auth.
- **Returns a report** (fetched/processed/skipped/errors, duration) that is logged as one structured line and recorded in metrics.

Note the honesty angle: Cloud Run with scale-to-zero cannot run a background loop reliably (current bug); the scheduled-trigger model is the standard serverless fix.

Nightly eval on GCP side: use a **GitHub Actions `schedule`** workflow (free for public repos) rather than a second Scheduler job or Cloud Run Job, keeping the 3 free Scheduler slots for app needs. On kind, the same eval runs as a CronWorkflow.

### (c) Dual deployment targets without drift

**Recommendation: build once, address by digest, share one config base; Terraform owns the Cloud Run service shape, CI owns the image; Git owns the kind state.**

1. **Images:** One `release.yml` on push to `main` builds `api` and `web` once with buildx and pushes the same digest to both Artifact Registry (for Cloud Run) and GHCR public (for kind). Tag `sha-<short>`; deploy by `@sha256:` digest.
   - Why GHCR for kind: kind pulling from private AR needs a long-lived credential (JSON key, an anti-pattern) and AR internet egress is billed. GHCR public pulls are free. AR free storage is only 0.5 GiB per billing account (verified) - add an AR cleanup policy keeping the last ~3 versions or you will exceed it within a few releases.
2. **Cloud Run:** Terraform declares the services (SA, env from Secret Manager, scaling, ingress, port 8080, invoker IAM) with `lifecycle { ignore_changes = [template[0].containers[0].image, client, client_version] }`. CI runs `google-github-actions/deploy-cloudrun` with `image: ...@sha256:...` only. Existing services were created by `gcloud run deploy --source`; **`terraform import` them** rather than recreating (keeps URLs).
3. **kind:** After the Cloud Run deploy succeeds, CI runs `kustomize edit set image` in `deploy/k8s/overlays/kind` and commits `[skip ci]`. ArgoCD (auto-sync, prune, selfHeal) picks it up. If branch protection blocks bot commits, have ArgoCD track a dedicated `gitops/kind` branch that only CI writes. Do not add Argo CD Image Updater; one fewer moving part, and the git history *is* the deploy log.
4. **Config:** Single non-secret config file `deploy/config/common.env` (`PORT=8080`, `GEMINI_MODEL`, `LOG_FORMAT=json`, feature flags). Kustomize `configMapGenerator` consumes it directly; Terraform reads it via `locals` (`split` lines on `=`) into Cloud Run env. Target-specific deltas in `cloudrun.env` / `kind.env`. A CI check (`scripts/check-config-parity`) diffs the keys the app requires (`Settings` fields) against both.
5. **Web runtime config:** Switch to `$env/dynamic/public` / `$env/dynamic/private` so the same web image works on both targets (fixes the build-time `VITE_API_URL` bug). Required for build-once.
6. **Data/secrets per target:** Cloud Run uses real Firestore + Secret Manager env refs. kind uses a **Firestore emulator pod** (`FIRESTORE_EMULATOR_HOST`) and a `Secret` created from a local untracked `.env` by `scripts/kind-secrets.sh` (only the Gemini key needed). This keeps kind fully offline from GCP credentials. (Emulator image choice: MEDIUM confidence, verify `google-cloud-cli:emulators` tag at implementation.)

### (d) Repo layout for manifests and Terraform

See Recommended Project Structure below. Key decisions:
- **Kustomize, not Helm, for our own apps** (base + `overlays/kind` + reusable `components/`). Helm only for third-party platform charts (kube-prometheus-stack, argo-workflows, pushgateway) referenced from ArgoCD Applications with pinned chart versions.
- **No `overlays/cloudrun`:** Cloud Run is not Kubernetes. Do not pretend Knative YAML and Deployments share a base; share the config file and image digest instead.
- **Terraform: modules + two root envs.** `envs/free-tier` (applied, GCS backend) and `envs/gke-plan` (local backend, plan-only) both consume `modules/*`. A separate `bootstrap/` root (state bucket, WIF pool/provider, CI SAs) is applied once by hand because CI cannot create its own identity.
- `gke-plan` is CI-gated with `terraform plan -lock=false` using a read-only WIF SA (`roles/viewer`); plan needs credentials to evaluate data sources. Add `tflint` and a config scanner (Trivy/Checkov) so the never-applied module still has a verifiable check.

### (e) Where the eval harness lives and how it calls the agent

**Recommendation: `apps/api/evals/`, in-process by default, HTTP mode as a secondary smoke.**

- **In-process** (`AgentRunner` + `InMemoryRepo` + a `ModelClient`) is the only way to score what matters here: which tools were called with which args, whether a cross-tenant write was *attempted* (executor rejection) vs *achieved* (repo state), and per-call token/latency. HTTP would only see the reply text.
- **Two modes:**
  - `replay` (PR gate in GitHub Actions): `ReplayClient` serves recorded Gemini responses keyed by (case_id, prompt hash). Deterministic, free, fast; fails when prompts/tools change without re-recording, which is the correct regression signal. Judge is skipped (or uses cached judge scores).
  - `live` (nightly, GH Actions schedule + Argo CronWorkflow): real Gemini via free-tier key, Claude as judge. Re-records cassettes as an artifact for review.
- **HTTP mode** (`--target http://...`): runs a small smoke subset against the deployed service through the real channel auth (signed Twilio requests with a test auth token on kind). Proves the wiring, not the agent quality.
- **Results flow (one writer, many readers):**
  1. Runner produces `EvalRun` JSON (`run_id`, git SHA, model, dataset version, per-case results, aggregates: tool accuracy, task success, injection block rate, language match, judge score, p50/p95 latency, tokens, est. cost).
  2. Reporters: JUnit XML + markdown job summary (CI), JSON artifact, **Firestore `eval_runs/{run_id}`** (system of record, free tier), and on kind **Prometheus Pushgateway** (`eval_*` gauges labeled by suite) - Pushgateway is the standard pattern for batch-job metrics.
  3. Dashboard reads Firestore via `GET /api/v1/evals` on both targets; Grafana on kind reads Prometheus for trends/alerts.
  - Honesty constraint: README badges/numbers link to a specific `run_id`/CI run; nothing hand-typed.
- **Cost flag:** Claude-as-judge uses the Anthropic API, which is not covered by the $0 GCP constraint. Keep judge calls nightly-only and small; cache by (case, response hash).

### (f) Metrics and logging for both targets

**Instrument once in the app; vary only the collection backend.**

| Signal | App side (same everywhere) | Cloud Run | kind |
|--------|---------------------------|-----------|------|
| Logs | JSON to stdout: `severity`, `message`, `logging.googleapis.com/trace` (from `X-Cloud-Trace-Context`/`traceparent`), `request_id`, `channel`, `tool`, `tokens_in/out`; PII redacted (hash phone) | Auto-ingested by Cloud Logging; structured fields parsed (free 50 GiB/project) | `kubectl logs`; optional Loki later (not needed for MVP) |
| Metrics | `prometheus_client`: `http_request_duration_seconds`, `agent_tool_calls_total{tool,status}`, `llm_tokens_total{direction,model}`, `llm_request_duration_seconds`, `llm_cost_usd_total`, `agent_errors_total`, `email_poll_*` | **Do not run the GMP sidecar**: Managed Prometheus bills per sample and Google recommends instance-based billing for the sidecar (both break $0). Use Cloud Run built-in request/latency metrics + structured log fields; optionally a few log-based metrics in Terraform behind a flag (MEDIUM: verify they stay within the free Monitoring allotment). Keep `/metrics` disabled or internal-auth on Cloud Run | `ServiceMonitor` scrapes `/metrics`; Grafana dashboards as JSON in git; `PrometheusRule` multi-window burn-rate alerts |
| Usage rollup | Runner increments `usage_daily/{date}` (tokens, calls, cost) in Firestore, batched | Feeds dashboard | Same (emulator) |

The Firestore usage rollup is what makes the SvelteKit dashboard work on Cloud Run, where there is no Prometheus. Per-instance Prometheus counters on autoscaled Cloud Run would be misleading anyway.

---

## Recommended Project Structure

```
renci/
├── apps/
│   ├── api/
│   │   ├── main.py                  # no poller in lifespan; mounts internal router
│   │   ├── config.py                # Settings; no hardcoded project default
│   │   ├── security/                # twilio_sig.py, internal_auth.py, chat_session.py
│   │   ├── identity/                # normalize.py, resolve_owner()
│   │   ├── agent/
│   │   │   ├── context.py           # RequestContext
│   │   │   ├── runner.py            # manual FC loop, AgentResult
│   │   │   ├── executor.py          # tool registry, validation, ctx injection
│   │   │   ├── model_client.py      # GeminiClient | ReplayClient | ScriptedClient
│   │   │   ├── tools/               # one module per tool domain (profile, menu, ppp)
│   │   │   └── prompts/             # en / zh-Hans / zh-Hant / ja
│   │   ├── db/                      # repo.py (Protocol), firestore_repo.py, memory_repo.py
│   │   ├── jobs/                    # poll_email.py (run_once + __main__), common.py (lease)
│   │   ├── routes/                  # webhooks.py, chat.py, api.py, internal.py, health.py, metrics.py
│   │   ├── observability/           # logging.py, metrics.py, middleware.py
│   │   ├── evals/
│   │   │   ├── datasets/            # golden_{en,zh,ja}.jsonl, adversarial.jsonl
│   │   │   ├── cassettes/           # recorded model responses for replay mode
│   │   │   ├── scorers/             # tool_match.py, task_success.py, injection.py, language.py, judge.py
│   │   │   ├── runner.py            # python -m evals.runner --mode replay|live [--target URL]
│   │   │   └── reporters/           # junit, markdown, firestore, pushgateway
│   │   └── tests/
│   └── web/src/routes/dashboard/    # eval + usage pages
├── deploy/
│   ├── config/                      # common.env, cloudrun.env, kind.env (non-secret)
│   ├── k8s/
│   │   ├── base/                    # api/, web/ (Deployment, Service, SA, ConfigMap gen)
│   │   ├── components/              # firestore-emulator/, monitoring/ (ServiceMonitor)
│   │   └── overlays/kind/           # images: (CI-bumped), patches, emulator component
│   ├── workflows/                   # CronWorkflow email-poll, nightly-eval; WorkflowTemplates
│   ├── monitoring/                  # PrometheusRule (SLO burn), grafana dashboards (JSON CMs)
│   └── argocd/
│       ├── root-app.yaml            # app-of-apps entry (kubectl apply once)
│       └── apps/                    # renci.yaml, argo-workflows.yaml, kube-prometheus-stack.yaml, pushgateway.yaml, workflows.yaml, monitoring.yaml
├── infra/terraform/
│   ├── bootstrap/                   # state bucket, WIF pool/provider, CI SAs (manual apply once)
│   ├── modules/                     # cloud-run-service, artifact-registry, secrets, wif-binding,
│   │                                # firestore, gcs-assets, scheduler-job, network, gke-autopilot, https-lb
│   └── envs/
│       ├── free-tier/               # APPLIED: composes free modules; GCS backend
│       └── gke-plan/                # PLAN-ONLY: network + gke-autopilot + https-lb
├── scripts/                         # kind-up.sh, kind-secrets.sh, check-config-parity.sh (Git Bash + Linux)
└── .github/workflows/               # ci.yml, release.yml, nightly-eval.yml, terraform.yml
```
(`infra/cloudbuild.yaml` is deleted; it is a third conflicting deploy path.)

### Structure Rationale

- **evals inside `apps/api/`:** the API runs with `apps/api` as import root; in-process evals must import `agent.runner` the same way tests do. Keeps one Python env/lockfile.
- **`deploy/` vs `infra/`:** `infra/` = cloud resources (Terraform, slow-changing, applied by humans/CI with elevated SA). `deploy/` = workload state reconciled by ArgoCD and image bumps (fast-changing). Different owners, different blast radius.
- **`envs/` split by intent, not by environment name:** "applied" vs "plan-only" is the real distinction under the $0 constraint, and makes it obvious to a reviewer which code is live.

---

## Architectural Patterns

### Pattern 1: Ports and adapters at the three external seams
**What:** `ModelClient`, `Repo`, and `Clock/IdGen` are Protocols; prod, test, and eval each supply adapters.
**When:** Now. It is the prerequisite for evals, deterministic tests, and the kind emulator.
**Trade-offs:** Small upfront refactor of `agent/core.py` and `db/firestore.py`; avoid going further (no DI framework).

### Pattern 2: Job as library + thin triggers
**What:** Batch work is a pure-ish `run_once()` with locking and idempotency inside; HTTP route and CLI `__main__` are 10-line wrappers.
**When:** Email polling, eval runs, any future cron (PPP refresh).
**Trade-offs:** Duplicate triggers must both be tested; the lease makes overlapping triggers safe.

```python
# apps/api/jobs/poll_email.py
async def run_once(repo: Repo, mailbox: Mailbox) -> PollReport:
    if not await repo.poller_enabled(): return PollReport.skipped("disabled")
    async with repo.lease("email-poller", ttl=timedelta(minutes=4)) as held:
        if not held: return PollReport.skipped("lease held")
        for msg in await mailbox.fetch_unseen_peek(limit=20):
            if not await repo.claim_message(msg.message_id): continue  # create() fails if exists
            await handle_email(msg)          # -> VerifiedSender -> route_message
            await mailbox.mark_seen(msg.uid)
    ...
if __name__ == "__main__":
    report = asyncio.run(run_once(build_repo(), build_mailbox()))
    sys.exit(0 if report.ok else 1)
```

### Pattern 3: Build once, promote by digest
**What:** Images are immutable artifacts; environments differ only by config and data.
**When:** Always with two targets.
**Trade-offs:** Requires runtime (not build-time) config in SvelteKit.

### Pattern 4: Context-bound tool execution
**What:** Tool schemas expose only user-intent arguments; trusted context is injected by the executor (see (a)).
**When:** Any multi-tenant LLM tool use.
**Trade-offs:** You own the function-calling loop (max-rounds, error mapping) instead of the SDK; this is a feature for observability and evals.

---

## Data Flow

### Request flow (SMS, target state)
```
Twilio POST /webhooks/sms
  -> verify X-Twilio-Signature (PUBLIC_BASE_URL)        reject 403
  -> claim processed_messages/{MessageSid}              duplicate -> empty TwiML
  -> VerifiedSender(sms, +1E164) -> resolve owner -> RequestContext
  -> registration FSM | runner.run(ctx, msg)
        -> Gemini (aio, AFC off) <-> executor(ctx, call) -> repo writes scoped to ctx
        -> metrics + JSON log per model call / tool call; usage_daily rollup
  -> MessagingResponse (escaped) -> Twilio
```
(Follow-up, not required for this milestone: ACK-then-async-reply to stay under Twilio's 15 s timeout.)

### Scheduled flows
```
Cloud Scheduler (OIDC) --> /internal/jobs/poll-email --> jobs.poll_email.run_once
Argo CronWorkflow -----> pod: python -m jobs.poll_email --> same function
GH Actions schedule ---> python -m evals.runner --mode live --> Firestore eval_runs (+ artifact)
Argo CronWorkflow -----> python -m evals.runner --mode live --> Firestore(emulator) + Pushgateway
```

### Delivery flow
```
PR: ci.yml -> ruff/mypy/pytest, svelte-check, evals --mode replay (gate),
              kustomize build | kubeconform, terraform fmt/validate/plan (both envs)
main: release.yml -> buildx (api, web) -> push AR + GHCR (same digest)
      -> deploy-cloudrun @digest (WIF) -> smoke /health
      -> kustomize edit set image (overlays/kind) -> commit -> ArgoCD sync on kind
```

### Key data flows
1. **Identity:** channel credential -> `VerifiedSender` -> `owners/{normalized}` -> `RequestContext`. The model never sees or supplies an id.
2. **Telemetry:** runner/executor -> logs (both), Prometheus registry (kind scrape), `usage_daily` (dashboard everywhere).
3. **Eval results:** runner -> `EvalRun` -> Firestore (dashboard) + Pushgateway (Grafana, kind) + CI artifacts/summary.

---

## Suggested Build Order (dependencies)

1. **Foundation and seams** - pin deps (lockfile), unify config (port 8080, project/region, no hardcoded URLs), minimal `ci.yml` (tests on PR), introduce `ModelClient`/`Repo` ports, async Gemini client. *Everything below depends on these seams and on CI running.*
2. **Security core** - channel auth (Twilio sig, chat session, internal OIDC), identity normalization with doc-ID keys, `RequestContext` + executor (manual FC loop), TwiML escaping, CORS, media host allowlist, slug reservation. Extract `jobs/poll_email` with lease/idempotency; delete lifespan poller and public toggle. *Depends on 1. Unblocks eval adversarial suite (needs executor) and both deployment trigger models.*
3. **Observability instrumentation (app side)** - JSON logging, request/trace middleware, metrics registry, hooks in runner/executor, usage rollup. *Small; do with or right after 2 because evals reuse token/latency capture.*
4. **Eval harness + Japanese** - datasets, scorers, replay cassettes, PR gate, live mode, Firestore reporter. JA prompts land with JA eval cases. *Depends on 2-3.*
5. **Free-tier Terraform + bootstrap** - state bucket, WIF, AR (+cleanup policy), Secret Manager, Firestore, GCS, import existing Cloud Run services, Scheduler job. *Depends on 2 (internal endpoint exists). Must precede 6.*
6. **Release pipeline to Cloud Run** - build once, dual push, deploy by digest via WIF, nightly-eval workflow. *Depends on 5.*
7. **kind + ArgoCD + Argo Workflows + Prometheus/Grafana** - Kustomize base/overlay, emulator, app-of-apps, CronWorkflows, ServiceMonitor, PrometheusRule, Pushgateway reporter, CI tag bump. *Depends on 6 for images/tag-bump; manifests can be authored in parallel with 5-6.*
8. **Plan-only GKE/VPC/LB modules** - independent after module conventions from 5 exist; can run in parallel with 7.
9. **Dashboard** - SvelteKit `/dashboard` over `eval_runs` and `usage_daily`. *Depends on 4 (data) and 3 (usage); UI work can start once the API shape is fixed.*

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Demo / portfolio (now) | Single API service, scale-to-zero, Scheduler-triggered poll, Firestore. Sufficient. |
| Tens of real shops | ACK-then-reply for SMS (Cloud Tasks queue to an internal worker route), per-identity rate limits in Firestore, conversation memory with TTL |
| Hundreds+ | Drop carrier email gateways (Twilio only), move to GKE per the plan-only modules with Cloud Armor rate limits, GMP for metrics once budget exists |

### Scaling priorities
1. **First bottleneck:** inline LLM latency vs Twilio webhook timeout -> retries -> duplicate side effects (mitigated by MessageSid idempotency now; queueing later).
2. **Second bottleneck:** Gemini free-tier rate limits during nightly live evals colliding with live traffic -> separate API keys/projects for eval vs serving, or throttle eval concurrency.

---

## Anti-Patterns

### Anti-Pattern 1: Prompting the model with trusted IDs
**What people do:** "Always pass business_id=X" in the system prompt.
**Why it's wrong:** Prompt injection selects another tenant; also untestable.
**Do this instead:** Context-bound executor (Pattern 4).

### Anti-Pattern 2: Background loops in a request-scaled container
**What people do:** asyncio poller in FastAPI lifespan on Cloud Run.
**Why it's wrong:** Freezes at scale-to-zero, duplicates with N instances, per-instance toggle state.
**Do this instead:** Job-as-library + scheduler trigger + Firestore lease.

### Anti-Pattern 3: Two deployers for one Cloud Run service
**What people do:** Terraform manages the image and CI also runs `gcloud run deploy`.
**Why it's wrong:** Every apply reverts the deployed revision.
**Do this instead:** Terraform `ignore_changes` on image; CI owns image only. Delete `cloudbuild.yaml`.

### Anti-Pattern 4: Forcing Cloud Run into the Kustomize tree
**What people do:** Knative/Cloud Run YAML overlays sharing a k8s base.
**Why it's wrong:** Different schemas; fake reuse creates more drift, not less.
**Do this instead:** Share image digest and `deploy/config/*.env`; enforce parity with a CI check.

### Anti-Pattern 5: Build-time env in a build-once pipeline
**What people do:** `VITE_API_URL` inlined at build.
**Why it's wrong:** One image cannot serve two targets; the current prod bug.
**Do this instead:** SvelteKit `$env/dynamic/*`.

### Anti-Pattern 6: Eval that only checks reply text over HTTP
**What people do:** Black-box chat evals.
**Why it's wrong:** Cannot score tool choice, args, or cross-tenant attempts - the core claims.
**Do this instead:** In-process runner with trace capture; HTTP only for smoke.

### Anti-Pattern 7: GCP service-account JSON keys anywhere
**What people do:** Key in GitHub secret or in kind for AR/Firestore access.
**Why it's wrong:** Long-lived credential; contradicts the WIF story.
**Do this instead:** WIF in CI; GHCR public images + Firestore emulator on kind.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Gemini (AI Studio key) | `client.aio.models.generate_content`, AFC disabled, behind `ModelClient` | Pin google-genai exactly (2.30.x at research time); AFC semantics are changing in next major. Vertex AI would remove the key but is not free-tier |
| Twilio | Signed webhook in; `MessagingResponse` out | Validate against `PUBLIC_BASE_URL`; kind cannot receive real Twilio traffic, test with signed fixtures |
| Gmail IMAP/SMTP | Mailbox adapter used only by `jobs.poll_email` | PEEK then mark Seen after success; check `Authentication-Results` |
| Cloud Scheduler | HTTP target with OIDC | 3 free jobs per billing account |
| Anthropic (judge) | Called only from `evals/scorers/judge.py` | Not $0; nightly only, cached |
| GitHub Actions | WIF via `google-github-actions/auth` | Separate SAs: deployer (run.admin scoped, AR writer), planner (viewer) |
| ArgoCD / Argo Workflows | Helm-installed via ArgoCD Applications on kind | Pin chart versions; Argo Workflows has a 4.x line now - verify CRD/CronWorkflow field changes before pinning (LOW-MEDIUM) |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| routes <-> security | Direct call, returns `VerifiedSender` or raises 401/403 | Routes never construct identity from request bodies |
| router <-> agent | `runner.run(ctx, message)` | Only router builds `RequestContext` |
| agent <-> db | `Repo` Protocol, ctx-scoped write methods | Fake for tests/evals |
| evals <-> agent | In-process import | Same code path as prod minus channel auth |
| app <-> telemetry | Module-level metrics + logger | No backend-specific code in app |
| CI <-> kind | Git commit of image tag | ArgoCD pulls; CI never talks to the cluster |

---

## Sources

- google-genai on PyPI (latest 2.30.1, 2026-10-13; AFC deprecation warning for `generate_content`; `AutomaticFunctionCallingConfig(disable=True)`): https://pypi.org/project/google-genai/ - HIGH
- Cloud Scheduler pricing (3 free jobs per billing account): https://cloud.google.com/scheduler/pricing - HIGH
- Cloud Run Managed Prometheus sidecar (default scrape :8080/metrics, instance-based billing recommended): https://docs.cloud.google.com/run/docs/monitoring-managed-prometheus-sidecar - HIGH
- Managed Service for Prometheus per-sample pricing: https://cloud.google.com/managed-prometheus and https://docs.cloud.google.com/stackdriver/docs/managed-prometheus/cost-controls - MEDIUM (no free sample tier found)
- Artifact Registry pricing (0.5 GiB free per billing account; internet egress billed): https://cloud.google.com/artifact-registry/pricing - MEDIUM
- Argo Workflows releases (3.7.x patches; 4.x line exists): https://newreleases.io/project/github/argoproj/argo-workflows/release/v3.7.18 - LOW-MEDIUM, verify on GitHub
- Argo CD v3.3.x: https://gitea.alexlebens.dev/alexlebens/infrastructure/pulls/5999 - LOW, verify on GitHub releases
- Existing codebase map: `.planning/codebase/ARCHITECTURE.md`, `CONCERNS.md`, `STRUCTURE.md`

---
*Architecture research for: secured, evaluated, GitOps-deployed Gemini agent (Renci v2)*
*Researched: 2026-10-14*
