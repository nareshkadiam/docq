# DocQ: Document Q&A Assistant (learning project)

## Goal
Learn cloud deployment, observability, tracing, evaluation, authentication, CI/CD and security on GCP by building a small AI app and running it through a full SDLC loop with Claude Code doing the typing and me making the decisions.

## The app (kept deliberately simple)
Upload documents, ask questions, get answers grounded in those documents.
The app is a vehicle. The real subject is everything around it.

## Stack (GCP)
- Compute: Cloud Run (container)
- Database: Cloud SQL Postgres + pgvector (later)
- Secrets: Secret Manager
- LLM: Gemini via Vertex AI (IAM auth, no API key)
- Observability: OpenTelemetry -> Cloud Trace / Logging / Monitoring
- LLM tracing: Langfuse or Arize Phoenix
- Later: Terraform, GitHub Actions (Workload Identity Federation), auth provider, evals

## Roadmap

### Phase 0: Safety net
- [ ] New GCP project dedicated to this
- [ ] Billing budget + email alerts (50%, 100%)
- [ ] MFA on Google account, gcloud CLI installed
- [ ] GitHub repo created

### Phase 1: Deploy and access (manual first)
- [ ] 1. Tiny app with /health, runs locally
- [ ] 2. Dockerized, runs locally
- [ ] 3. Deployed to Cloud Run by hand (gcloud run deploy)
- [ ] 4. /ask endpoint calling Gemini via Vertex AI
- [ ] 5. Tear down everything, redeploy from scratch

### Phase 2: Observability and tracing
- [ ] Structured logs
- [ ] OpenTelemetry traces for each request
- [ ] Metrics: latency, errors, token usage, cost
- [ ] LLM tracing (prompt, response, latency per call)
- [ ] One dashboard and one alert

### Phase 3: CI/CD
- [ ] GitHub Actions: test, lint, build image
- [ ] Deploy via Workload Identity Federation (no long-lived keys)
- [ ] Secret scanning and container scanning in CI

### Phase 4: Authentication
- [ ] Managed auth provider, JWT validation in the app
- [ ] Per-user data isolation, with tests proving it

### Phase 5: Evaluation and security
- [ ] Golden question set, automated evals as a CI gate
- [ ] Prompt injection tests, rate limiting, hardening

## How I work (the manual loop)
1. Write the issue (what, why, done-when)
2. Ask Claude Code for a plan. Read it. No code yet.
3. Build on a branch
4. Write/run tests
5. Fresh session reviews the diff critically
6. I merge, deploy, check the result
7. Update CLAUDE.md if the agent got something wrong

## Learning log
Explain each rung back in my own words here. If I can't, I ask more questions before moving on.

| Date | Rung | What I built | In my own words: how it works and why |
|---|---|---|---|
| | | | |
