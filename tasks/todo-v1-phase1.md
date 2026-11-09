# Renci — Phase 1: Core SMS Loop (MVP)

## Scaffolding
- [x] Root configs (.gitignore, README, package.json)
- [x] API scaffolding (FastAPI, Dockerfile, requirements.txt)
- [x] Web scaffolding (SvelteKit, Dockerfile, configs)
- [x] Infra scaffolding (Terraform stubs, cloudbuild.yaml)

## API Backend
- [x] FastAPI entry point + config
- [x] Twilio SMS webhook handler
- [x] SMS router (registration vs agent)
- [x] SMS sender (outbound)
- [x] Firestore client + business model
- [x] Language detector (CJK detection)
- [x] Agent core (Claude tool-use dispatcher)
- [x] Agent tools (register, update_hours, show_status, show_help)
- [x] Registration action (multi-step SMS flow)
- [x] Profile action (update hours/contact)
- [x] Bilingual system prompts

## Web Frontend
- [x] SvelteKit project with Tailwind
- [x] Landing page (renci.app)
- [x] Dynamic [slug] route — load business from Firestore
- [x] Default business template
- [x] i18n setup (en + zh-Hans + zh-Hant)

## Verification
- [x] SMS round-trip test (webhook + TwiML response)
- [x] Registration E2E test (all 6 steps + validation)
- [x] Tool-use test (agent prompts + templates)
- [x] Bilingual test (language detection + response templates)
- [x] Slugify tests (basic, Chinese, mixed, special chars)
- [x] Health endpoint test

## Review
29/29 tests passing. Phase 1 complete with full test coverage.
Language detector uses lead-language heuristic for mixed Chinese/English input.
