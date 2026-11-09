# Renci v2 — Production-Grade Agent Platform: Plan

Status: PLANNED 2026-11-08. Not started. Phase 1 of v1 (hackathon MVP) is archived in `todo-v1-phase1.md`.

Source of truth for requirements: `.planning/PROJECT.md` (Active section). Research in `.planning/research/`, codebase map in `.planning/codebase/`.
GSD next step: write `.planning/REQUIREMENTS.md` and `.planning/ROADMAP.md` from this outline (`/gsd-new-project` was initialized but stopped before the roadmap).

Target: TEKsystems Tokyo "AI Software Engineer" JD — AI agents + evaluation, FastAPI, GCP Cloud Run/GKE/Logging/LB/VPC, GitHub Actions + ArgoCD + Argo Workflows, IaC, Prometheus/ELK.
Hard constraint: $0 GCP spend. Paid resources (GKE nodes, LB, VPC connector) are Terraform-planned only, never applied. Confirm with the user before any `terraform apply`.

## Prerequisites (local machine)

- [x] terraform installed (winget, v1.17.0, 2026-11-08; restart shell for PATH)
- [x] gcloud installed (winget, SDK 592.0.0, 2026-11-08; restart shell for PATH). Still to do: `gcloud auth login` + `gcloud config set project renci-491614` (user runs)
- [x] kind installed (scoop, v0.33.0, 2026-11-08); Docker Desktop and kubectl already present
- [ ] `uv`/pip install passes and the existing 40 tests run green (python-multipart, pytest-asyncio were missing)

## Phase 1 — Harden and secure
- [ ] Pin dependencies; reproducible install; all tests pass in CI
- [ ] Verify Twilio request signatures; authenticate email webhook, poll trigger, agent toggle
- [ ] Restrict CORS to known origins
- [ ] Escape model output in TwiML
- [ ] Bind `business_id` server-side from the authenticated sender (blocks cross-tenant prompt injection)
- [ ] Async Gemini client so tool calls do not block the event loop
- [ ] Secrets to Secret Manager; unify project/region/port/image-tag config
- [ ] Prevent duplicate slugs and duplicate owner records (unified owner identity across channels)
- [ ] Fix photo upload (uniform bucket access) and menu-item persistence

## Phase 2 — Agent evaluation
- [ ] Golden conversation dataset (EN/ZH/JA): registration, updates, tool selection, refusals
- [ ] Tool-call accuracy and task-success metrics
- [ ] Adversarial suite: prompt injection, cross-tenant writes, unsafe actions
- [ ] LLM-as-judge (Claude judges, Gemini is the agent) for reply quality and language match
- [ ] Latency and token-cost per run; results persisted for trends
- [ ] `make eval` produces a report a reviewer can rerun

## Phase 3 — Japanese
- [ ] Agent detects and replies in Japanese
- [ ] Web i18n adds `ja`
- [ ] Eval set includes JA cases and passes

## Phase 4 — CI/CD
- [ ] GitHub Actions: lint, typecheck, tests, eval gate on PR
- [ ] Keyless GCP auth via Workload Identity Federation
- [ ] Images to Artifact Registry tagged by SHA
- [ ] Cloud Run deploy from CI (replaces ad-hoc `--source` deploys)

## Phase 5 — GitOps
- [ ] Kustomize manifests for API + web
- [ ] ArgoCD app-of-apps syncing from git to a local kind cluster
- [ ] Argo Workflows: nightly eval run + email-poll CronWorkflow (replaces in-process poller)

## Phase 6 — Infrastructure as Code
- [ ] Terraform for free-tier resources, actually applied: Cloud Run, Artifact Registry, Secret Manager, WIF, Firestore, GCS
- [ ] Terraform modules for GKE Autopilot, VPC, HTTPS LB — `terraform plan` in CI only, never applied

## Phase 7 — Observability and dashboard
- [ ] Structured JSON logs with trace correlation in Cloud Logging
- [ ] Prometheus `/metrics`: request latency, tool calls, LLM tokens/cost, errors; Prometheus + Grafana on kind
- [ ] Alert rules (SLO burn rate) as code
- [ ] Eval and usage dashboard page in SvelteKit

## Order and dependencies

1 → 2 → 4 are the critical path (secure, measured, shipped through CI). 3 slots in after 2. 5 and 7 both need the kind cluster. 6 can run alongside 4 once gcloud auth works.

## Housekeeping
- [ ] Branch `production-hardening` has 5 unpushed planning commits; push it (or merge to main) once the user confirms the planning docs should be public (renci is a public repo)
- [ ] Tailored resume for the TEK JD goes in a NEW Drive doc, never overwriting originals

## Review

(To fill in as phases complete.)
