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
  `$P='docq-learning'; $R='europe-west2'; $IMG="$R-docker.pkg.dev/$P/docq/docq"; $T='v4'` (bump `$T` on every build: reusing a tag silently overwrites the image; never deploy only `latest`)
  - Prerequisites: `gcloud --version` (>= 500), `gcloud auth list` (your account is active), `gcloud config get-value project` (equals `$P`). Your user needs Owner (or `iam.serviceAccountUser` on `docq-run` and `docq-build`) to deploy and build as those accounts. After every IAM grant wait 1-2 minutes before retesting
  - Enable APIs (once): `gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com --project $P`
  - Artifact Registry repo (once): `gcloud artifacts repositories create docq --repository-format=docker --location=$R --project $P`
  - Service accounts, no keys (once): `gcloud iam service-accounts create docq-run --project $P` (runtime, NO roles) and `gcloud iam service-accounts create docq-build --project $P` (build)
  - Build account roles (once): `roles/artifactregistry.writer` on the docq repo (`gcloud artifacts repositories add-iam-policy-binding docq --location=$R --project $P --member="serviceAccount:docq-build@$P.iam.gserviceaccount.com" --role=roles/artifactregistry.writer`), `roles/logging.logWriter` on the project (`gcloud projects add-iam-policy-binding $P --member="serviceAccount:docq-build@$P.iam.gserviceaccount.com" --role=roles/logging.logWriter --condition=None`), `roles/storage.objectViewer` on `gs://${P}_cloudbuild` (`gcloud storage buckets add-iam-policy-binding gs://${P}_cloudbuild --member="serviceAccount:docq-build@$P.iam.gserviceaccount.com" --role=roles/storage.objectViewer`). Order trap: the bucket is created by the first `builds submit` upload, so on a fresh project the first build fails at the source step; then grant this role, wait, and run the build again (verified in Issue 5: `--region` does not change the bucket name, and it is in the US)
  - Runtime account role, once, before the first deploy (Issue 4): `gcloud projects add-iam-policy-binding $P --member="serviceAccount:docq-run@$P.iam.gserviceaccount.com" --role=roles/aiplatform.user --condition=None` (ONLY this role; undo: `remove-iam-policy-binding`). The Vertex AI API is enabled in the "Enable APIs" bullet above
  - Build: `gcloud builds submit . --project $P --region $R --config cloudbuild.yaml --substitutions="_IMAGE=${IMG}:$T" --service-account="projects/$P/serviceAccounts/docq-build@$P.iam.gserviceaccount.com"`
  - Deploy (private, complete, includes the `/ask` settings; do the runtime account role above first): `gcloud run deploy docq --image="${IMG}:$T" --region=$R --project=$P --service-account="docq-run@$P.iam.gserviceaccount.com" --no-allow-unauthenticated --min-instances=0 --max-instances=2 --cpu=1 --memory=256Mi --port=8080 --set-env-vars="GOOGLE_CLOUD_PROJECT=$P,GEMINI_MODEL=gemini-3.5-flash-lite,GEMINI_LOCATION=eu,MAX_QUESTION_CHARS=1000,MAX_OUTPUT_TOKENS=256,MODEL_TIMEOUT_SECONDS=20"`
  - Call while private: `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" <service-url>/health` (no token gives 403)
  - Never make the service public: `/ask` calls a paid model, so `allUsers` must never get `roles/run.invoker`
  - Remove public access (the service must stay private once `/ask` exists; IAM change, can take ~100 s to take effect, check both service URLs): `gcloud run services remove-iam-policy-binding docq --region=$R --project=$P --member=allUsers --role=roles/run.invoker`
  - After a manual traffic pin, send traffic to the new revision with `gcloud run services update-traffic docq --region=$R --project=$P --to-latest`
  - Local ADC (your own login, stored outside the repo in `%APPDATA%\gcloud`): `gcloud auth application-default login`, then `gcloud auth application-default set-quota-project $P`. Revoke with `gcloud auth application-default revoke`. Never copy the ADC file into the repo
  - Run `/ask` locally with real Gemini (costs a fraction of a cent): `$env:GOOGLE_CLOUD_PROJECT=$P` then `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`. Tests never call the real model
  - Call a private service with a token: `$t = gcloud auth print-identity-token; curl.exe -X POST <service-url>/ask -H "Authorization: Bearer $t" -H "Content-Type: application/json" -d '{\"question\":\"What is Cloud Run?\"}'` (without the token: 403). Do not paste the token into chat or files. Inline `-d '{\"question\":...}'` quoting gave a 422 in Windows PowerShell 5.1; the reliable form writes the body to a file first: `[IO.File]::WriteAllText("$env:TEMP\q.json", '{"question":"What is Cloud Run?"}')` and then `--data-binary "@$env:TEMP\q.json"`
  - Before any `gcloud builds submit .`, list what will be uploaded: `gcloud meta list-files-for-upload .` (no credential, `.env` or key files)
  - Logs: `gcloud run services logs read docq --region=$R --project=$P --limit=20`
  - Revisions: `gcloud run revisions list --service=docq --region=$R --project=$P`
  - Roll back traffic: `gcloud run services update-traffic docq --region=$R --project=$P --to-revisions=<revision-name>=100` (forward again: `--to-latest`)

## Rebuild checklist (verified by the Issue 5 rebuild on 2026-10-13: first build fails with a 403 on the source tarball, `objectViewer` plus ~1 min fixes it; bucket stays `gs://${P}_cloudbuild` in the US even with `--region`; URL and `00001` revision numbering as expected)
Order matters. Variables and prerequisites first (see Deploy above). Never use `--allow-unauthenticated` or the public IAM binding.
Set `$P`, `$R`, `$IMG`, `$T` first (Deploy section). Each step uses the exact command in the Deploy section above:
1. Enable APIs: `gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com --project $P`
2. Create the Artifact Registry repo `docq` (Deploy: "Artifact Registry repo")
3. Create service accounts `docq-run` and `docq-build`, no keys (Deploy: "Service accounts")
4. Grants: `docq-run` ONLY `roles/aiplatform.user` (Deploy: "Runtime account role"); `docq-build` `roles/logging.logWriter` on the project (with `--condition=None`) and `roles/artifactregistry.writer` on the repo (Deploy: "Build account roles")
5. `gcloud meta list-files-for-upload .` and confirm no credential, `.env` or key file
6. Build with tag `$T`. On a fresh project this first build fails at the source upload (bucket `gs://${P}_cloudbuild` is created but `docq-build` cannot read it)
7. Grant `docq-build` `roles/storage.objectViewer` on that bucket (Deploy: "Build account roles"), wait 1-2 minutes, run the same build again
8. Deploy (private, complete command in the Deploy section)
9. Anonymous check, both must print 403: `curl.exe -s -o NUL -w "%{http_code}" <url>/health` and the same for a POST to `/ask`. With a token, `/health` and `/ask` answer (see "Call a private service with a token"). The service URL is `https://docq-<project-number>.europe-west2.run.app` as before
10. Checks: roles `gcloud projects get-iam-policy $P --flatten="bindings[].members" --filter="bindings.members:docq-run@" --format="value(bindings.role)"` prints only `roles/aiplatform.user`; invoker policy `gcloud run services get-iam-policy docq --region=$R --project=$P` has no members; scaling and identity `gcloud run services describe docq --region=$R --project=$P --format="yaml(spec.template.metadata.annotations,spec.template.spec.serviceAccountName)"` shows maxScale 2 and `docq-run`; logs (Deploy: "Logs") show request metadata only, no question or answer text

## Teardown (commands verified in the Issue 5 run on 2026-10-13; whole teardown took about a minute of command time)
Dangerous and mostly irreversible. Describe or list each resource first, delete one named resource at a time, pause after each. Never delete the project, billing link, budget alert or the default compute account.
Order: service, then images and repo, then bucket, then role bindings, then service accounts (so no `deleted:serviceAccount:` entries are left in the project policy).
0. Read-only first: `gcloud run services list`, `gcloud artifacts repositories list`, `gcloud storage buckets list`, `gcloud iam service-accounts list`, `gcloud projects get-iam-policy $P` (save the result in the issue notes)
1. `gcloud run services delete docq --region=$R --project=$P --quiet` (~6 s)
2. `gcloud artifacts repositories delete docq --location=$R --project=$P --quiet` (removes all images and the repo-level writer binding; ~14 s)
3. `gcloud storage rm -r gs://${P}_cloudbuild --project $P` (removes the bucket, its objects and its objectViewer binding; ~16 s)
4. `gcloud projects remove-iam-policy-binding $P --member="serviceAccount:docq-run@$P.iam.gserviceaccount.com" --role=roles/aiplatform.user --condition=None`; same with `docq-build@...` and `roles/logging.logWriter` (`--condition=None` avoids an interactive prompt)
4b. Discover any other grants before deleting the accounts (must print nothing): `gcloud projects get-iam-policy $P --flatten="bindings[].members" --filter="bindings.members:docq-" --format="table(bindings.role,bindings.members)"`. Remove anything it lists the same way as step 4
5. `gcloud iam service-accounts delete docq-run@$P.iam.gserviceaccount.com --project $P --quiet`; same for `docq-build@...`. The account list can show a deleted account for a few seconds; wait and list again (`describe` then says PERMISSION_DENIED / not found)
6. Verify empty: `gcloud run services list`, `gcloud artifacts repositories list`, `gcloud storage buckets list`, `gcloud iam service-accounts list` (only the compute account remains), `gcloud run jobs list --region=$R --project $P`, `gcloud secrets list --project $P`, and the same policy filter as 4b with `bindings.members:docq-` OR `bindings.members:deleted:` printing nothing. Next day: open the Billing report and note what, if anything, was still charged
Set `$P` and `$R` first (Deploy section).
Left on purpose: enabled APIs (free), project, billing link, budget alert, default compute account, Cloud Logging default storage, local ADC login.

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
- Gemini region: Google's locations page listed `europe-west2` for `gemini-3.5-flash-lite`, but the real call returned 404 there; the model card (global, `us`, `eu`) was right. Use `GEMINI_LOCATION=eu`. Always do one real test call before trusting a docs page on model availability.
- An `application_default_credentials.json` copy (refresh token) appeared in the repo root during Issue 4 and was deleted by the user; `.gitignore` and `.dockerignore` now exclude it. `gcloud builds submit .` uploads the whole folder, so check `gcloud meta list-files-for-upload .` first.
- After a manual `update-traffic --to-revisions=...` pin, new deploys get 0% traffic until `--to-latest` is run.
