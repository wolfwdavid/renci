# Renci 仁慈 — v2: Production-Grade Agent Platform

## What This Is

Renci is a multilingual AI agent (Gemini function calling) that lets Manhattan Chinatown mom-and-pop shop owners build and update a simple business website by email, SMS, or web chat — no website builder needed. v2 takes the hackathon build and turns it into a production-grade, secured, evaluated, GitOps-deployed service on GCP, primarily as a portfolio piece demonstrating applied AI agent engineering for an "AI Software Engineer" role (TEKsystems Tokyo / consumer e-commerce).

## Core Value

A reviewer can see, run, and verify a real AI agent that is **secure, measurably evaluated, and shipped through a reproducible GitOps pipeline** — every claim backed by a passing check, not a README assertion.

## Requirements

### Validated

<!-- Inferred from existing code (hackathon build, 22 commits, see .planning/codebase/). -->

- ✓ Owner registers a business via multi-step conversational flow (name, hours, address, contact) — existing
- ✓ Agent updates hours/contact/profile through Gemini 2.5 Flash function calling — existing
- ✓ Channels: Twilio SMS webhook, Gmail IMAP poller + SMTP reply, web chat widget — existing
- ✓ Bilingual EN / zh-Hans / zh-Hant language detection and reply templates — existing
- ✓ Per-business public page at `/[slug]` rendered by SvelteKit from Firestore — existing
- ✓ Menu photo → item extraction via Gemini Vision — existing (persistence incomplete)
- ✓ Neighborhood PPP loan data lookup from bundled CSV — existing
- ✓ FastAPI API + SvelteKit web deployed to Cloud Run (us-central1, project renci-491614) — existing
- ✓ 40 pytest tests pass once missing deps (python-multipart, pytest-asyncio) are installed — existing

### Active

<!-- Hypotheses until shipped. Grouped by intent; REQUIREMENTS.md holds REQ-IDs. -->

**Harden & secure**
- [ ] Fix dependency gaps and pin versions; reproducible install passes all tests
- [ ] Verify Twilio request signatures; authenticate email webhook, poll trigger, and agent toggle
- [ ] Restrict CORS to known origins
- [ ] Escape model output in TwiML responses
- [ ] Bind `business_id` server-side from the authenticated sender (never model-supplied) to block cross-tenant prompt injection
- [ ] Use the async Gemini client so tool calls don't block the event loop
- [ ] Move secrets to Secret Manager; unify project/region/port/image-tag config
- [ ] Prevent duplicate slugs and duplicate owner records (unified owner identity across channels)
- [ ] Fix photo upload (uniform bucket access) and menu-item persistence

**Agent evaluation**
- [ ] Golden conversation dataset (EN/ZH/JA) covering registration, updates, tool selection, refusals
- [ ] Tool-call accuracy and task-success metrics
- [ ] Adversarial suite: prompt injection, cross-tenant writes, unsafe actions
- [ ] LLM-as-judge scoring for reply quality/language match (Claude as judge, Gemini as agent)
- [ ] Latency and token-cost reporting per run; results persisted for trend tracking

**Japanese**
- [ ] Agent detects and replies in Japanese; web i18n adds `ja`; eval set includes JA cases

**CI/CD & GitOps**
- [ ] GitHub Actions: lint, typecheck, tests, eval gate on PR
- [ ] Keyless GCP auth via Workload Identity Federation; images to Artifact Registry tagged by SHA
- [ ] Cloud Run deploy from CI (replacing ad-hoc `--source` deploys)
- [ ] Kubernetes manifests (Kustomize/Helm) for API + web
- [ ] ArgoCD app-of-apps syncing from git to a local kind cluster
- [ ] Argo Workflows: nightly eval run + email poll CronWorkflow (replaces in-process poller)

**Infrastructure as Code**
- [ ] Terraform for free-tier resources actually applied (Cloud Run, Artifact Registry, Secret Manager, WIF, Firestore, GCS)
- [ ] Terraform modules for GKE Autopilot, VPC, and HTTPS Load Balancer — validated with `terraform plan` in CI, never applied

**Observability & dashboard**
- [ ] Structured JSON logs with trace correlation in Cloud Logging
- [ ] Prometheus `/metrics` (request latency, tool calls, LLM tokens/cost, errors); Prometheus + Grafana on kind
- [ ] Alert rules (SLO burn rate) as code
- [ ] Eval & usage dashboard page (SvelteKit, designed with UI/UX Pro Max)

### Out of Scope

- Applying paid GCP resources (GKE nodes, Load Balancer, Serverless VPC connector) — user requires $0 spend; demonstrated via Terraform plan + local kind instead
- Kotlin/Spring Boot service — user chose Python-only depth over breadth
- Switching LLM provider away from Gemini — GCP-native fits target role; Claude used only as eval judge
- Real-user onboarding/marketing — portfolio-first; current data is demo only
- Voice channel — not needed to demonstrate target skills
- Porting tools from `ai-tools-index` — templated stubs, not production code

## Context

- **Origin:** Hackathon project by team "Blue Fire" (lead: David White Wolf). README is a pitch deck; live demo at renci-web-408375733910.us-central1.run.app.
- **Codebase map:** `.planning/codebase/` (STACK, INTEGRATIONS, ARCHITECTURE, STRUCTURE, CONVENTIONS, TESTING, CONCERNS) — mapped 2026-10-14.
- **Critical known issues (CONCERNS.md):** unauthenticated `/webhooks/email` allows impersonating any owner; no Twilio signature check + forged `MediaUrl` can exfiltrate Twilio credentials; unescaped TwiML; model-chosen `business_id`; async tools passed to sync Gemini client; email poller incompatible with Cloud Run scale-to-zero; Terraform/Cloud Build/live deploy drift (renci-prod vs renci-491614, us-east1 vs us-central1, :latest vs :SHA, port 8000 vs 8080); `VITE_API_URL` unset in prod; no CI.
- **"ADK" mentions are inaccurate** — code uses `google-genai` directly. Fix docstrings.
- **Target role signals:** AI agent dev + evaluation, FastAPI, REST microservices, GCP (Cloud Run, GKE, Logging, LB, VPC), GitHub Actions + ArgoCD + Argo Workflows, IaC, Prometheus/ELK, Claude Code usage.
- **Local tooling:** Windows 11, Docker Desktop + kubectl present; gcloud and terraform not yet installed.

## Constraints

- **Budget**: $0 GCP spend — free tiers only; paid resources exist as code, not deployed
- **Honesty**: No fabricated metrics; every README/resume claim must map to a passing test, eval result, or CI run; unrun results marked "pending"
- **Tech stack**: Python 3.13 + FastAPI, SvelteKit, Gemini 2.5 Flash, Firestore, GCP — Python-only backend
- **Platform**: Developer machine is Windows; scripts must work in Git Bash and CI Linux
- **Git**: No AI attribution in commits/PRs; work on branches, PR to main
- **Data**: Demo only — safe to reset Firestore and redeploy

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Extend renci rather than start a new repo | Only existing project already on FastAPI + Cloud Run + Terraform + Gemini agent | — Pending |
| Portfolio-first audience | User's goal is the AI SWE application; no real users depend on it | — Pending |
| $0 budget: kind for ArgoCD/Argo Workflows; GKE/LB/VPC Terraform plan-only | User requirement "keep it free" | — Pending |
| Keep Gemini as agent model; Claude as eval judge | GCP-native for role; cross-provider judge reduces self-grading bias | — Pending |
| Python-only backend | Depth over breadth | — Pending |
| Add Japanese in v1 | Tokyo-based role | — Pending |
| Security hardening before any new features | Live public endpoints are currently exploitable | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-14 after initialization*
