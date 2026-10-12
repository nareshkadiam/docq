# CLAUDE.md: rulebook for this repo

## What this project is
DocQ is a small document Q&A app on GCP. It is a learning project. The goals are understanding deployment, observability, tracing, CI/CD, authentication, evaluation and security. Clarity beats cleverness. Keep the app simple.

## About the person working with you
They are learning cloud and AI operations and do not want to write most of the code, but they want to understand all of it. So:
- Before writing code, explain the plan in plain language and list which GCP resources will be created or changed. Wait for approval.
- Before running any command involving `delete`, `iam`, `--allow-unauthenticated`, billing or project-level changes, explain what it does and why.
- After finishing a task, summarize what changed and why in a few sentences, so it can go in the learning log.
- Prefer boring, well-known tools over novel ones. Explain tradeoffs when there is a real choice.

## Stack
- Python 3.12, FastAPI
- Docker, deployed to Cloud Run
- Gemini via Vertex AI (authenticate with IAM, never an API key)
- Postgres + pgvector via Cloud SQL (later phase)
- OpenTelemetry for traces/metrics/logs
- Terraform and GitHub Actions (later phases)

## Commands
(Fill these in as they are created, and keep them accurate.)
- One-time setup (PowerShell, from repo root): `uv venv --python 3.12 .venv` then `uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt`
  (without uv: `python -m venv .venv`, `.venv\Scripts\Activate.ps1`, `pip install -r requirements-dev.txt`)
- Run locally: `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`, then open http://127.0.0.1:8000/health
- Run tests: `.venv\Scripts\python.exe -m pytest`
- Lint: TBD
- Build image: `docker build -t docq:local .`
- Run container: `docker run --rm -p 8080:8080 docq:local`, then open http://localhost:8080/health (custom port: `docker run --rm -e PORT=9000 -p 9000:9000 docq:local`)
  (on Windows, if `docker` is not found, add `C:\Program Files\Docker\Docker\resources\bin` to PATH)
- Deploy: TBD

## Rules (never break these)
1. **No secrets in the repo, logs, or chat.** Use Secret Manager or environment variables loaded at runtime. Never commit `.env` files.
2. **Least privilege.** Never grant `Owner` or `Editor`. Propose the narrowest role that works and explain it.
3. **No production credentials** in the agent's environment.
4. **Small changes.** One issue, one branch, one small PR.
5. **Tests with every change.** If something is hard to test, say so instead of skipping.
6. **Never push to main directly.** Work on a branch and open a PR.
7. **Never deploy to production without explicit approval** in the conversation.
8. **Never log full prompts, documents, or personal data** unless the issue explicitly requires it. Say so when it does.
9. **Pin dependencies** and mention any new dependency and why it is needed.

## Definition of done
- Acceptance criteria in the issue are met
- Tests pass and lint is clean
- Commands section above is up to date
- A short plain-language explanation is ready for the learning log
- Any new risk or assumption is written down

## Lessons learned (add a line whenever the agent gets something wrong)
- (empty for now)
