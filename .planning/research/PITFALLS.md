# Pitfalls Research

**Domain:** Hardening and productionizing a multilingual Gemini function-calling agent (FastAPI on Cloud Run) with LLM evals, GitHub Actions + WIF, Terraform, ArgoCD/Argo Workflows on local kind, and observability, on a $0 GCP budget, as a portfolio piece
**Researched:** 2026-10-14
**Confidence:** MEDIUM overall. HIGH for items checked against official docs (google-github-actions/auth README, Secret Manager and Artifact Registry pricing, Gemini API terms, Gemini deprecations page) and against this repo's own code. MEDIUM/LOW where only community sources or training data back a claim; those are marked inline.

Phase names below follow the intent groups in `.planning/PROJECT.md`. The roadmapper should map them to numbered phases:
- **P-Harden**: security and dependency hardening
- **P-Agent**: agent core refactor (async client, tool loop, tenant binding)
- **P-Eval**: eval harness, golden set, adversarial suite, judge
- **P-JA**: Japanese language support
- **P-CI**: GitHub Actions, WIF, Artifact Registry, Cloud Run deploy from CI
- **P-IaC**: Terraform (applied free tier plus plan-only paid modules)
- **P-GitOps**: kind, ArgoCD, Argo Workflows
- **P-Obs**: structured logs, Prometheus/Grafana, alerts, dashboard
- **P-Portfolio**: README, claims, demo, release

---

## Critical Pitfalls

### Pitfall 1: Twilio signature validation that fails behind Cloud Run, then gets "temporarily" disabled

**What goes wrong:**
`RequestValidator.validate(url, params, signature)` returns False for every real Twilio request. Twilio signs the exact public URL it called (`https://renci-api-...run.app/webhooks/sms`). Inside the container, FastAPI's `request.url` comes back as `http://...`, because Cloud Run terminates TLS at its front end. Uvicorn only trusts `X-Forwarded-Proto` from `--forwarded-allow-ips`, which defaults to `127.0.0.1`. Faced with 403s on every SMS, the developer adds `SKIP_TWILIO_VALIDATION=true`, and that flag ends up set in production.

Other ways the URL can mismatch:
- Cloud Run serves two hostnames: the deterministic `SERVICE-PROJECTNUMBER.REGION.run.app` and the legacy hashed `SERVICE-xxxx-uc.a.run.app`. The Twilio console may point at the other one.
- A custom domain or load balancer was added later.
- A trailing slash or query string differs.
- The validator is given the parsed form with values reordered or dropped. It needs every POST param exactly as sent.

**Why it happens:**
Twilio's docs describe the fix only in general proxy terms ("reconstruct the original URL using X-Forwarded-Proto"). Unit tests pass because the test client and the validator use the same base URL.

**How to avoid:**
- Don't rebuild the URL from request headers. Set `PUBLIC_BASE_URL` in config (one source of truth, also used to configure the Twilio console) and validate against `PUBLIC_BASE_URL + request.url.path + ('?' + query if query)`.
- Pass `dict(await request.form())` as params.
- Also start uvicorn with `--proxy-headers --forwarded-allow-ips='*'`. This is acceptable on Cloud Run because only Google's front end can reach the container. Use exec-form `CMD`.
- Allow no bypass flag in prod. If a dev bypass exists, the app should refuse to start when `APP_ENV=prod` and the bypass is set.
- Tests: generate a valid signature with `RequestValidator(token).compute_signature(url, params)` and assert 200. Assert 403 for a wrong signature, a missing header, a tampered param, and an `http://` vs `https://` mismatch.
- Smoke test after deploy: send a real SMS to the Twilio number, or replay a signed request from a script that uses the real token from Secret Manager, and check the logs.

**Warning signs:** 100% of real webhooks return 403 while tests are green. A config var named like `*_SKIP_*`/`*_DISABLE_*_VALIDATION`. Twilio debugger shows error 11200/11205.

**Phase to address:** P-Harden. The prod smoke check belongs in P-CI's post-deploy job.

---

### Pitfall 2: Media SSRF and credential exfiltration survive the signature fix

**What goes wrong:**
Once the signature check is in, the team treats `MediaUrl0` as trusted. However, `download_twilio_media` still sends Basic auth to any host with `follow_redirects=True`. A redirect from a legitimate Twilio media URL to a CDN is normal, and httpx drops auth on cross-origin redirects in recent versions, but relying on library defaults is fragile.

**How to avoid:** Allowlist `api.twilio.com` for the authenticated request, disable redirects on the authenticated hop, follow the redirect manually without credentials, cap the response size, and check the content-type before sending the bytes to Gemini (this also fixes the hardcoded `image/jpeg`). Add a test that a non-Twilio `MediaUrl` is rejected without any outbound call.

**Warning signs:** Media fetch code with `auth=` and no host check.

**Phase to address:** P-Harden.

---

### Pitfall 3: Async tools plus Gemini automatic function calling (AFC) that silently doesn't execute, and AFC itself hiding what evals need

**What goes wrong:**
- The current code passes `async def` tools to the **sync** `client.models.generate_content`. Coroutines are never awaited, so the model says "Hours updated!" while nothing is written to Firestore.
- Switching to `client.aio.models.generate_content` fixes the event-loop blocking. The python-genai docs confirm `client.aio` mirrors every method, but they do not clearly document async callables in AFC (LOW-MEDIUM confidence that it works on every pinned version).
- AFC also makes the tool-call trajectory implicit. Tool-call accuracy evals then have to dig through `automatic_function_calling_history`.
- AFC's default limit is 10 remote calls (official docs), so one confused turn can burn 10 free-tier requests.
- PyPI notes for google-genai 2.13 warn that the next major version will stop invoking AFC from direct `models.generate_content` calls (sync, stream, and async) and route it through chats instead. An unpinned `google-genai>=1.0.0` will break on upgrade.
- AFC builds tool schemas from Python signatures and docstrings. Removing `business_id` from a signature, or editing a docstring, silently changes the model-facing schema.

**Why it happens:** AFC demos are one-liners, and nobody tests `dispatch()`: coverage on `agent/core.py` is 33% and `dispatch` is never invoked.

**How to avoid:**
- Disable AFC (`automatic_function_calling=AutomaticFunctionCallingConfig(disable=True)`) and write an explicit loop:
  1. Call `client.aio.models.generate_content`.
  2. Read `response.function_calls`.
  3. Dispatch to a registry of server-side handlers that are already bound to the authenticated tenant.
  4. `await` each handler and append `FunctionResponse` parts.
  5. Stop at a max iteration count (for example 3).
- Record each `(tool_name, args, result, latency)`. This is your eval trace and metric source.
- Declare tool schemas explicitly with `types.FunctionDeclaration`, so the schema is reviewable in diffs and unaffected by docstring edits.
- Pin `google-genai==X.Y.Z` in a lockfile.
- Make the client injectable (pass it into `dispatch`) so tests can supply a fake model that returns scripted `function_call` parts. Assert the Firestore fake was written.

**Warning signs:** "Updated!" replies with unchanged Firestore docs. `RuntimeWarning: coroutine ... was never awaited` in logs. p95 latency on all endpoints rises during any LLM call, which means a sync call is blocking the event loop.

**Phase to address:** P-Agent. It must come before P-Eval, because evals need the trace.

---

### Pitfall 4: Tenant binding done in the prompt, or only "tested" by checking the model's reply

**What goes wrong:** The team removes `business_id` from the system prompt but leaves it as a tool parameter "for flexibility", or validates it against the owner only sometimes. Prompt-injection tests then assert that "the reply doesn't say it changed another business", which is a check on model text and not a security property.

Injection arrives through more than SMS text:
- business names and descriptions stored earlier (stored injection)
- OCR'd menu photos
- email bodies and subjects
- PPP CSV fields

**How to avoid:**
- Tools take no tenant identifier. Handlers close over `owner_id`/`business_id`, resolved server-side from the verified sender: Twilio signature plus E.164 normalization, or an authenticated session.
- Enforce this at the data layer too. `update_business(business_id, ...)` should assert `business.owner_id == ctx.owner_id`.
- Adversarial evals assert on side effects: zero writes to any tenant other than the caller's, with a Firestore fake or emulator seeded with two tenants. Also assert no tool calls outside the allowlist for that state (for example, no update tools mid-registration).
- Run each attack N times (for example 5) and report attack success rate. Model behavior is stochastic, so claim "structurally prevented; ASR measured at X/N", never "immune".
- Cap field lengths and strip control and markup content on description, name, and hours, since they render on public pages.

**Warning signs:** Any tool signature containing `business_id`, `owner_id`, or `phone`. Adversarial tests that only use `assert "sorry" in reply`.

**Phase to address:** P-Agent (binding) and P-Eval (adversarial suite).

---

### Pitfall 5: The $0 budget broken by the eval judge and the "use Vertex AI" advice

**What goes wrong:**
- PROJECT.md picks Claude as the LLM judge. The Anthropic API has no free tier, so every judged run costs real money. That is small but nonzero, and it conflicts with the "$0" constraint unless the user accepts an Anthropic spend cap separate from GCP.
- CONCERNS.md recommends `use_vertex_ai=True` with Workload Identity to drop the API key. Vertex AI Gemini calls are billed and have no free quota, unlike AI Studio keys. Following that advice moves the agent from free to paid.

**How to avoid:**
- Decide explicitly and record it in Key Decisions:
  - **Option A:** "$0 GCP; Anthropic judge capped at $N/month with a hard limit set in the Anthropic console, judge runs only nightly or manually, never per-PR."
  - **Option B:** Use a Gemini model from a *different* family/tier as judge on free quota, and document the self-preference caveat.
  - **Option C:** Make the judge optional. Deterministic checks (tool-call match, language match, length) gate CI; judge scores are reported only when available, marked "pending" otherwise.
- Keep the AI Studio API key (in Secret Manager) for Gemini. Do not switch to Vertex AI.
- Cache judge verdicts keyed by `(judge_model, rubric_version, transcript_hash)` so reruns of unchanged cases cost nothing.

**Warning signs:** Anthropic or Vertex charges appear. A judge step in a PR workflow that runs on every push.

**Phase to address:** P-Eval (judge design). Record the decision before roadmap finalization.

---

### Pitfall 6: Eval gate that's flaky, rate-limited, or meaningless

**What goes wrong:**
- The PR gate calls live Gemini on 50+ cases. The free tier allows roughly 10-15 RPM and about 1,000-1,500 requests/day for Flash models. That figure is LOW confidence: the numbers come from third-party sources, Google says limits are per project and shown in AI Studio, and there were reported cuts in Dec 2025. Each agent case can use 2-4 requests with tool loops.
- CI hits 429s, retries, and either times out or gets marked "allowed to fail". Then the gate gates nothing.
- Temperature 0 is still not deterministic, so a single-sample pass/fail flaps.
- Fork PRs get no secrets, so the eval job fails or is skipped on any external contribution.
- Golden cases are written by the same person who wrote the prompt, then tuned until they pass (overfitting).
- Free-tier Gemini inputs may be used by Google to improve products and may be seen by human reviewers (official Gemini API terms for "unpaid services"). Never put real owner data in eval sets or prod traffic on the free key. Demo data only, and disclose this in the README.

**How to avoid:**
- Use two tiers:
  - **PR gate:** deterministic. Replay recorded model responses (cassettes) through the real tool loop, plus unit-level checks. No network, $0, stable.
  - **Live eval:** runs nightly or on manual dispatch, plus on any change to prompts, model ID, or tool schemas (path filter). It uses a client-side token-bucket throttle under the RPM limit, exponential backoff that honors `retry-after`, and a per-run request budget.
- Score with thresholds over repeated samples (for example, tool-call accuracy ≥ 0.9 over 3 samples per case), not exact per-case equality.
- Give the gate an explicit baseline file in git. Fail on regression greater than delta versus baseline, not against an absolute target you guessed.
- Hold out a set of cases that is not used while iterating on prompts.
- Persist every run as JSONL (`evals/results/<date>-<sha>.jsonl`) with model ID, prompt hash, SDK version, latency, and tokens. That makes trends real.

**Warning signs:** `continue-on-error: true` on the eval job. A pass rate that changes between reruns on the same SHA. 429s in logs. Eval runtime longer than 10 minutes.

**Phase to address:** P-Eval for the harness and tiers; P-CI for wiring.

---

### Pitfall 7: LLM-as-judge biases presented as objective quality numbers

**What goes wrong:** Judge scores are reported as "reply quality 4.6/5", but they are affected by:
- verbosity bias, which rewards longer replies even though SMS replies should be ≤300 chars
- self-preference within a model family (if Gemini judges Gemini)
- position bias in pairwise comparisons
- poor calibration on fine-grained scales
- weak judging of Chinese and Japanese nuance, such as Simplified vs Traditional and register

These biases are well documented: Zheng et al. MT-Bench, Saito et al. on verbosity, and work on self-preference (arXiv 2410.21819). The specific magnitudes cited by blogs are MEDIUM/LOW confidence.

**How to avoid:**
- Prefer **deterministic checks first**: exact tool name and argument match, language-ID match on the reply, script check (Hans vs Hant vs kana present), length ≤ limit, and required facts present.
- Use the judge only for what can't be computed, such as politeness or helpfulness, with a binary or 3-point rubric and a required rationale field.
- Use a cross-family judge. Claude judging Gemini is good; if the fallback is Gemini, note the self-preference caveat.
- For pairwise A/B (prompt v1 vs v2), swap positions and count only verdicts that agree in both orders.
- Calibrate: hand-label about 30 cases, report judge-human agreement (Cohen's kappa) in the eval README, and re-check when the rubric changes. If kappa is below about 0.6, fix the rubric before trusting scores.
- Pin the judge model ID and rubric version in every result row.

**Warning signs:** Judge scores rise when replies get longer. Everything scores 4-5. No human-labeled sample exists.

**Phase to address:** P-Eval.

---

### Pitfall 8: Japanese misdetected as Chinese, and kana-led messages falling back to English

**What goes wrong:** This is verified in `apps/api/language/detector.py`, which returns the language of the first CJK-ideograph or ASCII letter.
- A Japanese message beginning with kanji, such as 「営業時間を変更したい」, returns `"zh"` because 営 is in U+4E00-9FFF.
- A message beginning with kana, such as 「こんにちは」, matches neither branch. The fallback counts only Han characters, so a short kana message with one Latin token (for example 「こんにちは、Renciです」) becomes `"en"`.
- `is_traditional_chinese` checks a fixed marker set. Japanese shinjitai overlap: 時, 開, 来 vs 來, 会 vs 會, 国 vs 國. Japanese can't be distinguished from Chinese by Han characters alone.
- Short SMS ("OK", "はい", "好") gives little signal.
- Off-the-shelf detectors (langdetect, fastText lid.176) are also unreliable on texts under about 20 characters and on code-switched Chinatown messages (LOW-MEDIUM confidence from training data).

**How to avoid:**
- Rule first: **any hiragana (U+3040-309F) or katakana (U+30A0-30FF, U+31F0-31FF, half-width U+FF66-FF9F) means `ja`**. Kana is a near-certain Japanese signal. Then Han-only text becomes `zh`, refined to Hans or Hant by a larger character-pair table (opencc-style mapping) rather than about 40 markers.
- Make language sticky per owner. Store `preferred_language` at registration and use it when detection is low-confidence: short, Han-only, or mixed text.
- Let Gemini reply in the user's language, but verify the reply's script in evals: a `ja` reply must contain kana, a `zh-Hant` reply must not be Simplified-dominant.
- Golden set: include kanji-only Japanese, kana-only, JA with English brand names, zh-Hans/zh-Hant pairs that are ambiguous in Japanese, Cantonese-colloquial written Chinese (係/唔/嘅), and emoji-only messages.
- Add `ja` to every template and i18n file. A missing key silently falls back to English or Chinese.

**Warning signs:** JA test inputs routed to `zh` templates. Language-match eval below about 95% on JA. Japanese replies containing Simplified-only characters.

**Phase to address:** P-JA, with cases added to P-Eval's golden set.

---

### Pitfall 9: WIF provider that any GitHub repo can use, or overbroad impersonation

**What goes wrong:**
- The provider is created without an attribute condition, or with only `assertion.repository_owner == 'wolfwdavid'`. The google-github-actions/auth README says to "always add an Attribute Condition"; Google now rejects GitHub providers without one (MEDIUM confidence).
- The condition is scoped by owner but not repo, so every repo the user owns, including forks of random projects, can mint tokens.
- The deployer SA gets `roles/editor` or `roles/owner`. Branch is not restricted, so any PR branch can deploy.
- `pull_request_target` workflows check out PR code with secrets and an OIDC token available.

**How to avoid:**
- Map `attribute.repository_id`, `attribute.repository_owner_id`, `attribute.ref`, and `attribute.event_name`. Condition on numeric IDs, which survive renames and resist the squatting that name-based checks allow: `assertion.repository_id == '<id>' && assertion.repository_owner_id == '<id>'`.
- Bind deploy permissions with `principalSet://.../attribute.repository/<owner>/<repo>`. Additionally restrict deploy to `ref == 'refs/heads/main'` in the condition or via a GitHub Environment with protection rules.
- Split roles:
  - CI (PR) principal: Artifact Registry reader plus `terraform plan` read-only viewer, or nothing at all.
  - Deploy (main) principal: `run.developer`, `artifactregistry.writer`, and `iam.serviceAccountUser` scoped to the runtime SA only.
- Workflow `permissions: { contents: read, id-token: write }` per job, never top-level `write-all`. Never use `pull_request_target`.
- Add `gha-creds-*.json` to `.gitignore` **and `.dockerignore`**. The auth action writes a credentials file into `$GITHUB_WORKSPACE` (official README), and `docker build .` will copy it into the image.

**Warning signs:** `attribute_condition` empty or owner-only in Terraform. `roles/editor` anywhere. `docker history` or `dive` shows `gha-creds-*.json`.

**Phase to address:** P-CI. The WIF resources live in P-IaC, so the Terraform must exist first or be bootstrapped manually once and then imported.

---

### Pitfall 10: Accidental GCP spend from "free" resources and plan-only modules

**What goes wrong:**

Cost traps verified against official pricing pages:
- **Artifact Registry**: 0.5 GiB/month free per *billing account*. A FastAPI image with pandas, grpc, and google-cloud libraries is about 300-600 MB, and images are tagged per commit, so you exceed the free storage within a few pushes.
- The existing ad-hoc `gcloud run deploy --source` deploys already created a `cloud-run-source-deploy` AR repo and a `run-sources-*` GCS bucket that accumulate silently.
- **Secret Manager**: 6 active secret versions free per billing account. Every rotation adds a version; each old active version beyond the 6 costs $0.06/month.
- **Cloud Storage**: 5 GB-month free only in us-east1, us-west1, and us-central1, pooled. A Terraform state bucket in `US` multi-region or `asia-northeast1` (tempting for a Tokyo role) is not free.

Other traps:
- **Plan-only modules** (GKE Autopilot, VPC, HTTPS LB, Cloud NAT) live in the same root module or same state as applied resources. One `terraform apply` creates a global forwarding rule (about $18/month), NAT, and GKE (MEDIUM: prices from training data). The Serverless VPC connector bills for always-on instances.
- **Cloud Run**: `min-instances>=1` or "CPU always allocated" (the tempting fix for the in-process poller) leave the free request-based tier.
- **Egress**: public pulls from Artifact Registry. For example, making the AR repo public so kind can pull it means internet egress beyond the free allowance.
- **Logging**: verbose prompt and response logging plus bot traffic. The 50 GiB/project free ingestion is generous, but log-based metrics and sinks can add cost (MEDIUM).
- Budget alerts **notify, they don't cap**.

**How to avoid:**
- Keep separate Terraform roots: `infra/terraform/live/` (applied) and `infra/terraform/showcase/` (plan-only, `backend "local"` or no backend). CI runs only `terraform plan` on showcase, with a read-only SA. No workflow, script, or Makefile target applies showcase. Add a CI check that fails if a `showcase` apply path appears.
- AR cleanup policy in Terraform: keep the last N=3 tagged versions and delete untagged images older than 1 day. Delete the `cloud-run-source-deploy` repo and stop `--source` deploys. Same region as Cloud Run (us-central1), so pulls are free.
- Create secrets with Terraform (`google_secret_manager_secret`) but **add versions out of band** with `gcloud secrets versions add`, which also keeps secret values out of Terraform state. Destroy old versions after rotation.
- State bucket in `us-central1`, versioning on, lifecycle rule to keep 5 noncurrent versions.
- Create a budget of $1 with alerts at 50% and 100%. Optionally add a Pub/Sub-triggered function that detaches billing at 100%, which is a documented Google pattern (MEDIUM). Check the Billing report weekly during the build.
- `gcloud services list --enabled` audit. Don't enable `container.googleapis.com` or `vpcaccess` just for plan, unless plan requires it (plan for new resources generally doesn't call those APIs; data sources do).

**Warning signs:** Any non-zero line on the billing report. An AR repo over 0.4 GiB. `terraform state list` in the live root showing `google_container_cluster` or `google_compute_global_forwarding_rule`.

**Phase to address:** P-IaC for structure, cleanup policies, and budget. P-CI must enforce plan-only. Run an audit of existing deploy leftovers at the start of P-Harden.

---

### Pitfall 11: Local kind presented as "production GitOps", with prod depending on a laptop

**What goes wrong:**
- PROJECT.md moves the email poller to an Argo CronWorkflow on **local kind**. Production (Cloud Run) then only processes email while the laptop is on and Docker Desktop is running. The "nightly eval CronWorkflow" likewise runs only when the machine is awake, so trend charts have gaps and "nightly" is an unverifiable claim.
- ArgoCD syncs manifests to kind, while the real deploy is Cloud Run from CI. Reviewers notice the two paths deploy different things.

**How to avoid:**
- Be explicit about the split. Production runs on Cloud Run; the production email poll is triggered by **Cloud Scheduler** (3 free jobs per billing account, MEDIUM) calling an OIDC-authenticated `/internal/email/poll` endpoint. Or drop the email channel.
- Nightly live evals run on a **GitHub Actions scheduled workflow**, which is reliable and free for public repos, and commit results. The Argo CronWorkflow version is the GitOps demonstration, labeled as such in the README ("runs on the local kind reference environment").
- The kind environment deploys the *same image digests* that CI built, via a Kustomize `images:` bump committed by CI. That shows real GitOps promotion even though the cluster is local.
- Include a `make kind-up` script, and an asciinema or screenshot record of ArgoCD synced/healthy, as evidence.

**Warning signs:** README says "runs nightly" with no scheduled-workflow history. Email replies stop overnight.

**Phase to address:** P-GitOps (scope statement). Production poll trigger belongs in P-Harden or P-Agent.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `SKIP_TWILIO_VALIDATION` env flag | Unblocks local dev | Gets left on in prod; whole security story collapses | Only if the app refuses to boot with it when `APP_ENV=prod` |
| Keep Gemini AFC instead of an explicit loop | Fewer lines | Hidden trajectory, async ambiguity, breaks on SDK major bump | Never for this project; tool-trace evals are the point |
| `:latest` image tags | Simple manifests | ArgoCD can't detect changes; kind's `Always` pull policy causes ErrImagePull; no rollback | Never; tag by SHA, pin digests in Kustomize |
| One Terraform root for applied and plan-only resources | Less directory structure | One `apply` creates paid GKE/LB | Never under $0 constraint |
| Live-model eval as PR gate | "Real" numbers on every PR | Flaky, 429s, burns daily quota, fork PRs fail | Only behind a path filter plus manual label, never required |
| `forwarded-allow-ips='*'` | Correct scheme on Cloud Run | Header spoofing if the container is reachable directly | OK on Cloud Run/behind ingress; not on a bare VM |
| Hand-written golden set only | Fast to start | Overfit to author's phrasing | MVP only; add holdout and adversarial variants before claiming numbers |
| Prometheus labels with `business_id`/`slug` | Per-tenant graphs | Cardinality grows with tenants | Never as a metric label; use logs or exemplars |
| Storing judge outputs nowhere | Simplicity | Cannot show trends, re-pay judge cost | Never; JSONL in repo or GCS |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Twilio webhook | Validating against `request.url` (http, internal host) | Validate against configured `PUBLIC_BASE_URL` + path; same value set in Twilio console |
| Twilio webhook | Doing LLM work inline; Twilio's 15 s timeout causes retries and duplicate writes | Idempotency on `MessageSid` (Firestore `create()` on `inbound/{MessageSid}`); ACK fast if latency is near 10 s, reply via REST |
| Twilio TwiML | f-string `<Message>{text}</Message>` | `MessagingResponse().message(text)`; test with `&`, `<`, `]]>` |
| google-genai | Unpinned `>=1.0.0`; sync client in async route | Pin exact; `client.aio`; explicit tool loop; inject client for tests |
| Gemini 2.5 Flash | `max_output_tokens=500` while thinking is on: thinking tokens can consume the budget and leave empty `response.text` (MEDIUM) | Set `thinking_config.thinking_budget` explicitly (0 or small) and handle `None` text; log `usage_metadata.thoughts_token_count` |
| Gemini model lifecycle | Hardcoded `gemini-2.5-flash`. The official deprecations page says 2.5 access is limited to projects that used it recently and suggests newer models for new projects, so a fresh project or key may get 404 | Model ID in config; eval gate must re-run on model change; record model ID in every eval row; check https://ai.google.dev/gemini-api/docs/deprecations at start of P-Agent |
| Gemini free tier | Real PII sent on unpaid quota (used for product improvement, human review possible) | Demo data only; README disclosure |
| Firestore in tests/evals | Evals write to the real demo DB, burning the 20k writes/day free quota and polluting the demo | Firestore emulator in CI (`gcloud emulators firestore` or Docker image); separate eval collection prefix |
| GitHub Actions WIF | Missing `id-token: write`; owner-only condition | Per-job permissions; condition on `repository_id` and ref |
| Artifact Registry to kind | kind can't pull private AR without a JSON key (contradicts "keyless") | Push the same image to **public GHCR** for kind (free), AR for Cloud Run; or `kind load docker-image` in a local script |
| ArgoCD install | `kubectl apply` of install manifest fails: CRD annotation too long (ApplicationSet CRD) | `kubectl apply --server-side --force-conflicts` or Helm chart (MEDIUM, known issue) |
| ArgoCD app-of-apps | CRs synced before their CRDs (Argo Workflows, ServiceMonitor) fail dry-run | Sync waves (`argocd.argoproj.io/sync-wave`), `SkipDryRunOnMissingResource=true` |
| kind ingress | Ingress controller installed but not reachable from Windows host | kind config `extraPortMappings` + `ingress-ready=true` node label, or just `kubectl port-forward` and document it |
| SvelteKit env | Secrets or API URL in `VITE_*`/`PUBLIC_*` are inlined into client bundle at build | Use `$env/dynamic/private` server-side; never put secrets in public-prefixed vars |
| Cloud Run structured logs | Using `logging.basicConfig` text; or `google-cloud-logging` client API (extra latency/cost) | JSON to stdout with `severity`, `message`, `logging.googleapis.com/trace` = `projects/PROJECT/traces/TRACE_ID` parsed from `X-Cloud-Trace-Context`/`traceparent` |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sync Gemini/SMTP/Twilio calls in `async def` | All endpoints' p95 = LLM latency; `/health` slow during chats | `client.aio`, `asyncio.to_thread` for SMTP/Twilio/GCS | 2+ concurrent requests per instance |
| Tool loop without cap | One message triggers 5-10 model calls; 429s; Twilio timeout | Max 3 iterations; per-turn request budget | First ambiguous user message |
| Live eval without throttle | 429 storms, eval job takes 30+ min | Token bucket under RPM; concurrency 1-2; cache | >~10 cases/min on free tier |
| Prometheus high-cardinality labels (`business_id`, `phone`, `model_response`, `error_message`, raw `language` from model, full URL path with slug) | Prometheus memory climbs on kind; Grafana slow; series count > 10k | Labels only from bounded enums: `channel`, `tool`, `status`, `model`, `route` template (`/[slug]` not actual slug), `lang` in {en, zh-Hans, zh-Hant, ja, other}; tokens as counters, latency as histograms with few buckets | Hundreds of tenants, or any free-text label (immediately) |
| kube-prometheus-stack + ArgoCD + Argo Workflows on Docker Desktop with default WSL2 memory | Pods `OOMKilled`/`Pending`, Docker Desktop freezes | `.wslconfig` memory=8GB+; use a slim Prometheus (no Alertmanager HA, short retention) or `prometheus` chart without node-exporter extras; single-node kind | ~6 GB total requests on 16 GB host (LOW-MEDIUM) |
| Completed Argo Workflows never GC'd | etcd/apiserver slow, `kubectl get wf` huge | `ttlStrategy`, `podGC: OnPodCompletion`, CronWorkflow `successfulJobsHistoryLimit`/`failedJobsHistoryLimit` | Weeks of 15-min email polls (~100/day) |
| CronWorkflow overlap | Two email polls run simultaneously, causing double replies | `concurrencyPolicy: Forbid`, `startingDeadlineSeconds`, explicit `timezone` | When a poll takes longer than the interval |
| Cold start with pandas + grpc | First SMS after idle takes 5-10 s and nears Twilio's timeout | Replace pandas with `csv` for the 31-row file; lazy imports; slim image | Scale-to-zero (always, at demo traffic) |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Secrets in CI logs via `set -x`, `env` dumps, `echo $SECRET \| base64`, or pytest failure diffs printing `Settings()` | Token disclosure in public Actions logs (public repo = world-readable) | `pydantic.SecretStr` for all secrets; no `set -x` in steps with secrets; `::add-mask::` for derived values; GitHub masking doesn't catch transformed values |
| Secret committed then "removed" | Remains in git history and forks | Run `gitleaks detect` on full history **now** (hackathon repo with 22+ commits, `.env.example` unreviewed); rotate any hit, as removal alone is insufficient; add gitleaks to pre-commit + CI |
| `COPY . .` in Dockerfile without `.dockerignore` | `.env`, `gha-creds-*.json`, `.terraform/`, tfstate baked into public image | `.dockerignore` allowlist style; scan image with `trivy`/`dive` in CI |
| Terraform state containing secret values | `google_secret_manager_secret_version.secret_data` stored plaintext in state bucket/local file | Never manage secret *values* in Terraform; `.gitignore` `*.tfstate*`, `.terraform/`, `*.tfvars` with values |
| Prompt and response logging with PII | Phone numbers and emails in Cloud Logging and Grafana; also sent to the Gemini free tier | Redaction filter in the log formatter (hash E.164 to a short id); log tool names and arg *keys*, not values |
| Unauthenticated `/agent/toggle`, `/webhooks/email/poll`, `/metrics` | Cost DoS, info leak | Internal routes require Google OIDC (Cloud Scheduler SA) and are verified in-app; `/metrics` not exposed publicly on Cloud Run (scrape only on kind, or protect) |
| Web chat keeps `from_address` client-supplied "for the demo" | Impersonation persists through the public widget | Demo mode uses an isolated sandbox tenant per browser session with no access to real tenants; or OTP |
| Eval adversarial suite committed with working exploit strings against the *live* endpoint | Anyone can replay against prod | Fine to commit (they are tests), but prod must be fixed first; run adversarial suite in CI against the patched code |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Agent confirms actions that failed (menu "added", hours "updated" when tool errored) | Owner trusts a site that's wrong | Reply text derived from tool *result* status; eval asserts reply claim matches side effect |
| Language flips mid-conversation (kanji-led JA message gets Chinese reply) | Confusing, feels broken to the Tokyo-facing reviewer | Sticky `preferred_language`; kana rule |
| Replies exceed SMS segment limits (CJK is UCS-2: 70 chars/segment) | Multi-part, costly, out-of-order SMS | Length budget per language (≤ ~140 CJK chars), checked in evals |
| Eval dashboard showing numbers without context (no N, no date, no model ID) | Reviewer can't trust or interpret | Every metric shows N, run date, commit SHA, model, and links to raw JSONL |

## "Looks Done But Isn't" Checklist

- [ ] **Twilio signature:** Verified with a *real* Twilio request on the deployed URL, not just unit tests. Check Cloud Logging shows 200 for a real SMS and 403 for a curl forgery.
- [ ] **Async tools:** A test with a fake model returning a `function_call` asserts the Firestore fake was *written*, and no "never awaited" warnings appear (`-W error::RuntimeWarning`).
- [ ] **Tenant isolation:** No tool schema contains a tenant id (a test enumerates declarations). The cross-tenant attack eval shows 0 foreign writes over N trials.
- [ ] **Eval gate:** It fails when you deliberately break the prompt. Verify by opening a sabotage PR once and linking the red run.
- [ ] **Eval results:** JSONL committed or published with model ID, prompt hash, SDK version, and N. The README numbers match the latest file.
- [ ] **WIF:** Terraform shows `attribute_condition` with `repository_id`. A workflow from a different repo can't auth (assert, or reason from the condition). No JSON keys exist: `gcloud iam service-accounts keys list` shows only system-managed keys.
- [ ] **No secrets in artifacts:** gitleaks on full history is clean, and the trivy/dive image scan shows no `.env` or `gha-creds`.
- [ ] **$0:** Billing report for the month shows $0.00. AR usage is under 0.5 GiB, active secret versions number 6 or fewer, and the state bucket is in us-central1.
- [ ] **Plan-only infra:** `terraform plan` for the showcase root runs green in CI, and the showcase root has no apply path anywhere.
- [ ] **ArgoCD:** The app is Synced/Healthy *on the SHA-tagged image CI built*, not a locally built `:latest`.
- [ ] **CronWorkflows:** History limits and `concurrencyPolicy: Forbid` are set. The production email poll does not depend on kind.
- [ ] **Structured logs:** In Cloud Logging, entries show correct severity colors (not all "DEFAULT"), and clicking a trace groups request logs.
- [ ] **Metrics:** `/metrics` series count stays stable after 100 synthetic messages from 100 different phones.
- [ ] **Japanese:** A kanji-only JA input, a kana-only input, and a JA+English input all get JA replies containing kana. `ja` keys exist in every web i18n file.
- [ ] **Windows/CI parity:** Scripts have LF endings (`.gitattributes` `*.sh text eol=lf`) and run in Git Bash with `MSYS_NO_PATHCONV=1` where paths such as `/metrics` or `--format=value(...)` get mangled.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Secret leaked to git or public CI log | MEDIUM | Rotate immediately (Twilio auth token, Gemini key, Gmail app password); add the new version to Secret Manager; destroy old versions; purge with `git filter-repo` only after rotating; re-run gitleaks |
| Paid resource accidentally applied | LOW-MEDIUM | `terraform destroy -target` in the offending root; check Billing for the charge; move the resource to the showcase root; add a CI guard |
| AR over free tier | LOW | Apply cleanup policy; `gcloud artifacts docker images delete` old digests; delete `cloud-run-source-deploy` repo |
| WIF misconfigured too broad | LOW | Tighten `attribute_condition`; audit Cloud Audit Logs for `GenerateAccessToken`/STS exchanges from unexpected `repository` attributes |
| Eval numbers published, later found flaky or overfit | MEDIUM (credibility) | Re-run with N samples plus holdout; update README with the corrected numbers and a changelog note. Honesty beats a silent edit |
| Model ID becomes unavailable (404) | LOW if configurable | Switch model in config; run the full live eval; record the new baseline; note it in CHANGELOG |
| Duplicate owners or slugs in Firestore | LOW (demo data) | Reset demo data (allowed per PROJECT.md); migrate to natural-key doc IDs |

## Portfolio-Credibility Pitfalls

Treated as critical because the Core Value is "every claim backed by a passing check".

| Pitfall | Warning Sign | Prevention | Phase |
|---------|--------------|------------|-------|
| Unverifiable claims ("production-grade", "99.9% SLO", "secure") | Adjectives without links | Every README claim links to a CI run, test file, eval JSONL, or screenshot. Add a "Claims ledger" table: claim → evidence → status (verified/pending) | P-Portfolio, maintained every phase |
| Fake or synthetic metrics passed off as real (Grafana screenshots from load-generator traffic, SLO burn on zero traffic) | Perfect-looking graphs | Label synthetic traffic as synthetic; show eval metrics (real) rather than prod traffic (nonexistent) | P-Obs, P-Portfolio |
| Single giant commit or squash-everything history | Reviewer sees 1 commit with 200 files | Small, conventional commits per plan step on feature branches, merged by PR with CI checks visible; keep PR descriptions substantive. No AI attribution per user rules | All phases |
| Stale or contradictory numbers (README "40 tests" vs todo "29") | Already present | Generate counts from CI (badge or job summary), never hand-typed | P-Harden (fix), P-CI (automate) |
| Claims about the kind/Argo stack that imply cloud production | "Deployed on Kubernetes with ArgoCD" | Precise wording: "GitOps reference environment on kind; production on Cloud Run; GKE/LB as Terraform plan validated in CI" | P-GitOps, P-Portfolio |
| Inaccurate tech names ("ADK" when code uses google-genai) | Interviewer asks about ADK | Fix docstrings and README in P-Harden | P-Harden |
| Live demo broken when reviewer visits (cold start, quota exhausted, model 404) | 500s or empty replies | Uptime check (Cloud Monitoring uptime checks have a free allowance, MEDIUM) or scheduled GH Action smoke test; graceful "demo quota exhausted" message; recorded demo video as a fallback | P-Portfolio |
| Exposing exploitable endpoints while advertising the repo | Reviewer finds the open `/webhooks/email` | Harden first (already a Key Decision); don't publicize until P-Harden ships | P-Harden |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Twilio signature URL mismatch / bypass flag | P-Harden | Real SMS → 200; forged curl → 403; boot fails with bypass in prod |
| Media SSRF | P-Harden | Test: non-Twilio MediaUrl → no outbound request |
| Leaked secrets in history / images / logs | P-Harden (history scan), P-CI (gitleaks, trivy, masking) | gitleaks clean; image scan clean |
| Existing paid leftovers (`cloud-run-source-deploy`, `run-sources-*`) | P-Harden (audit) | AR/GCS usage under free tier |
| Async AFC / tool loop / SDK pin | P-Agent | Fake-model test asserts writes; lockfile pinned |
| Tenant binding | P-Agent | Schema test; cross-tenant eval 0/N |
| Gemini model lifecycle and thinking-token truncation | P-Agent | Model in config; empty-text handling test |
| Judge cost vs $0 | P-Eval (decision before start) | Key Decision recorded; spend cap set or judge optional |
| Flaky / rate-limited eval gate | P-Eval, P-CI | Replay gate deterministic across 3 reruns; live eval throttled |
| Judge bias | P-Eval | Kappa vs ~30 human labels reported |
| JA/ZH detection | P-JA | Golden-set language-match ≥ threshold incl. kanji-only JA |
| WIF scoping / gha-creds in image | P-CI (IaC resources in P-IaC) | Condition uses repository_id; no SA keys; dockerignore |
| Plan-only modules applied / cost traps | P-IaC | Separate roots; $1 budget alert; billing $0 |
| Terraform state secrets / location | P-IaC | Bucket us-central1; no secret_data in state |
| kind resource exhaustion, image loading, CRD apply | P-GitOps | `make kind-up` succeeds from clean on Windows; SHA image synced |
| Prod depending on laptop (poller/nightly) | P-GitOps scope + P-Harden (Cloud Scheduler) | Email processed with laptop off |
| CronWorkflow overlap/GC | P-GitOps | `concurrencyPolicy: Forbid`, TTL set |
| Structured log format / trace | P-Obs | Severity and trace grouping visible in Cloud Logging |
| Prometheus cardinality | P-Obs | Series count stable under 100 distinct senders |
| Portfolio claims | P-Portfolio (ledger maintained per phase) | Every claim links to evidence |

## Sources

- google-github-actions/auth README (attribute conditions, `id-token: write`, `gha-creds-*.json` in .gitignore/.dockerignore): https://github.com/google-github-actions/auth (HIGH)
- python-genai docs (AFC default max 10 remote calls, disabling AFC, `client.aio`): https://googleapis.github.io/python-genai/ (HIGH for the documented items; async-callable AFC behavior not documented, so LOW)
- google-genai PyPI 2.13.0 note on AFC moving to chats in the next major: https://pypi.org/project/google-genai/2.13.0/ (MEDIUM, seen via search snippet)
- Gemini API deprecations page (2.5 models: access limited to recent users, newer models suggested): https://ai.google.dev/gemini-api/docs/deprecations (MEDIUM: summarized by fetch tool; re-check at P-Agent start)
- Forum report of 2.5 Flash 404s before announced dates: https://discuss.ai.google.dev/t/gemini-2-5-flash-and-gemini-2-5-flash-lite-returning-404-no-longer-available-today-july-9-contradicts-oct-16-2026-shutdown-date/174267 (LOW)
- Gemini API Additional Terms (unpaid services used to improve products; human review): https://ai.google.dev/terms (HIGH)
- Gemini free-tier rate limits (third-party, conflicting, project-specific): https://blog.laozhang.ai/en/posts/gemini-api-free-tier, https://benchlm.ai/blog/posts/gemini-api-pricing (LOW; check AI Studio quota page)
- Twilio: Fixing request validation 403s behind a proxy: https://support.twilio.com/hc/en-us/articles/50535649249307-Fixing-Twilio-Request-Validation-403-Errors-Behind-a-Proxy ; Webhooks security: https://www.twilio.com/docs/usage/webhooks/webhooks-security (HIGH)
- Uvicorn settings (`forwarded_allow_ips` default 127.0.0.1): https://uvicorn.dev/settings/ ; FastAPI behind a proxy: https://fastapi.tiangolo.com/advanced/behind-a-proxy/ (HIGH)
- Artifact Registry pricing (0.5 GiB free per billing account): https://cloud.google.com/artifact-registry/pricing (HIGH)
- Secret Manager pricing (6 active versions, 10k accesses free per billing account): https://cloud.google.com/secret-manager/pricing (HIGH)
- Cloud Storage Always Free region restriction (us-east1/us-west1/us-central1): secondary sources, e.g. https://nittanyai.psu.edu/alliance-programs/nittany-ai-challenge/platform-access-and-training-materials/google-cloud/ (MEDIUM; confirm at https://cloud.google.com/free)
- LLM-as-judge biases: Self-Preference Bias in LLM-as-a-Judge https://arxiv.org/pdf/2410.21819 ; practitioner audit https://tianpan.co/blog/2026-04-27-llm-judge-bias-audit-length-position-format (MEDIUM)
- kind image pull policy with `:latest`: https://dev.to/devdpk/running-custom-docker-images-inside-kind-cluster-o37 ; https://oneuptime.com/blog/post/2026-02-09-image-pull-policy-always-ifnotpresent-never/view (MEDIUM)
- WIF attribute-condition practice with repository/owner IDs: https://security.googlecloudcommunity.com/community-blog-42/securing-your-ci-cd-pipeline-eliminate-long-lived-credentials-with-workload-identity-federation-2-3909 (MEDIUM)
- Repo evidence: `apps/api/language/detector.py` (first-char Han → zh; kana unhandled), `apps/api/requirements.txt` (unpinned `google-genai>=1.0.0`), `.planning/codebase/CONCERNS.md`, `.planning/codebase/TESTING.md` (HIGH)
- Training-data-only (LOW, verify in phase research): ArgoCD CRD client-side apply size limit, kind ingress `extraPortMappings`, Argo Workflows `ttlStrategy`/`podGC`/`concurrencyPolicy`, Cloud Scheduler 3 free jobs, Gemini 2.5 thinking tokens counting toward `max_output_tokens`, GCP LB/NAT hourly prices, short-text language-ID unreliability.

---
*Pitfalls research for: production-hardening a Gemini function-calling agent with evals and GitOps on $0*
*Researched: 2026-10-14*
