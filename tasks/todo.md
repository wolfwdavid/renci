# Renci — Phase 1: Core SMS Loop (MVP)

## Scaffolding
- [ ] Root configs (.gitignore, README, package.json)
- [ ] API scaffolding (FastAPI, Dockerfile, requirements.txt)
- [ ] Web scaffolding (SvelteKit, Dockerfile, configs)
- [ ] Infra scaffolding (Terraform stubs, cloudbuild.yaml)

## API Backend
- [ ] FastAPI entry point + config
- [ ] Twilio SMS webhook handler
- [ ] SMS router (registration vs agent)
- [ ] SMS sender (outbound)
- [ ] Firestore client + business model
- [ ] Language detector (CJK detection)
- [ ] Agent core (Claude tool-use dispatcher)
- [ ] Agent tools (register, update_hours, show_status, show_help)
- [ ] Registration action (multi-step SMS flow)
- [ ] Profile action (update hours/contact)
- [ ] Bilingual system prompts

## Web Frontend
- [ ] SvelteKit project with Tailwind
- [ ] Landing page (renci.app)
- [ ] Dynamic [slug] route — load business from Firestore
- [ ] Default business template
- [ ] i18n setup (en + zh-Hans + zh-Hant)

## Verification
- [ ] SMS round-trip test
- [ ] Registration E2E test
- [ ] Tool-use test (update hours)
- [ ] Bilingual test

## Review
_(To be filled after implementation)_
