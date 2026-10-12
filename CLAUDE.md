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
- Deploy to Cloud Run (PowerShell; needs gcloud >= 500, older versions fail on Artifact Registry). Set variables first:
  `$P='<project-id>'; $R='europe-west2'; $IMG="$R-docker.pkg.dev/$P/docq/docq"; $T='v1'`
  - Enable APIs (once): `gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project $P`
  - Artifact Registry repo (once): `gcloud artifacts repositories create docq --repository-format=docker --location=$R --project $P`
  - Service accounts, no keys (once): `gcloud iam service-accounts create docq-run --project $P` (runtime, NO roles) and `gcloud iam service-accounts create docq-build --project $P` (build)
  - Build account roles (once): `roles/artifactregistry.writer` on the docq repo (`gcloud artifacts repositories add-iam-policy-binding docq --location=$R --project $P --member="serviceAccount:docq-build@$P.iam.gserviceaccount.com" --role=roles/artifactregistry.writer`), `roles/logging.logWriter` on the project (`gcloud projects add-iam-policy-binding $P ...`), `roles/storage.objectViewer` on `gs://${P}_cloudbuild` (`gcloud storage buckets add-iam-policy-binding ...`; the bucket exists after the first build attempt)
  - Build: `gcloud builds submit . --project $P --region $R --config cloudbuild.yaml --substitutions="_IMAGE=${IMG}:$T" --service-account="projects/$P/serviceAccounts/docq-build@$P.iam.gserviceaccount.com"`
  - Deploy (private): `gcloud run deploy docq --image="${IMG}:$T" --region=$R --project=$P --service-account="docq-run@$P.iam.gserviceaccount.com" --no-allow-unauthenticated --min-instances=0 --max-instances=2 --cpu=1 --memory=256Mi --port=8080`
  - Call while private: `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" <service-url>/health` (no token gives 403)
  - Make public (deliberate, IAM change; undo with `remove-iam-policy-binding`): `gcloud run services add-iam-policy-binding docq --region=$R --project=$P --member=allUsers --role=roles/run.invoker`
  - Logs: `gcloud run services logs read docq --region=$R --project=$P --limit=20`
  - Revisions: `gcloud run revisions list --service=docq --region=$R --project=$P`
  - Roll back traffic: `gcloud run services update-traffic docq --region=$R --project=$P --to-revisions=<revision-name>=100` (forward again: `--to-latest`)

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
- gcloud 363 (2021) fails on `artifacts repositories create` ("Maven config is not supported"); check `gcloud --version` and update before GCP work.
- A Cloud Build run with a custom service account needs `options.logging: CLOUD_LOGGING_ONLY` (see cloudbuild.yaml); `--tag` alone is rejected.
- Do not run `gcloud beta` commands in non-interactive mode; it tries to install components in a new window.
