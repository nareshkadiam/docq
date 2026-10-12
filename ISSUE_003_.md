# Issue 3: Deploy the container to Cloud Run by hand

## What
Deploy the existing Docker image to Cloud Run in my own GCP project using `gcloud` commands that I run myself (with Claude Code explaining each one). End state: `/health` answers over a public HTTPS URL, and I understand every resource that was created.

## Why
This is rung 3 of the confidence ladder. Deploying by hand first means that when Terraform and GitHub Actions automate it later, I know exactly what they are doing. This issue also introduces core GCP ideas: projects, regions, APIs, Artifact Registry, Cloud Build, service accounts, IAM, revisions and logs.

## Before starting
- Phase 0 is finished: dedicated GCP project, billing linked, budget alerts set, MFA on, gcloud installed and logged in
- `gcloud config get-value project` prints my docq project ID
- Region chosen for everything: `europe-west2` (London). Use the same region throughout.

## Acceptance criteria (done when...)
- [ ] Only the APIs needed are enabled (expected: Cloud Run, Artifact Registry, Cloud Build) and I know why each is needed
- [ ] An Artifact Registry repository exists in `europe-west2` holding the image
- [ ] The image is built (via Cloud Build, or pushed from my machine) and tagged with a specific version, not only `latest`
- [ ] The Cloud Run service uses a **dedicated service account with no project roles**, not the default compute service account
- [ ] The service has a low limit on instances (for example max 2) and scales to zero when idle
- [ ] First deploy requires authentication. I confirm an unauthenticated request gets HTTP 403, then succeed by calling it with my own identity token
- [ ] After that, access is opened to the public on purpose, so `/health` works in a browser. Claude Code explains the IAM change before I approve it
- [ ] I can read the service's logs, both with `gcloud` and in the console Logs Explorer
- [ ] I deploy a second revision (a small visible change), see both revisions listed, and roll traffic back to the first
- [ ] Every command used is saved in the Commands section of CLAUDE.md (or a `docs/deploy.md`), with variables for project ID and region instead of hardcoded values
- [ ] I check the billing dashboard afterwards and note what, if anything, was charged

## Out of scope
LLM calls, Secret Manager, Terraform, GitHub Actions, custom domains, authentication in the app, tearing down (that is Issue 5).

## Risks and security notes
- Never use `Owner` or `Editor` roles for anything created here. Claude Code must explain every `iam` command and the exact role it grants before I approve it
- `--allow-unauthenticated` makes the service public. It is acceptable only because `/health` returns nothing sensitive, and it must be a deliberate, explained step
- Do not put the project ID or any credential in files that go public if the repo ever becomes public. The project ID alone is not secret, but do not commit service account key files. No key files should be created at all
- Keep the instance limit low so a mistake or a bot cannot run up a large bill
- Verify the billing budget alert exists before deploying

## Prompt to give Claude Code (plan first)
> Read CLAUDE.md and ISSUE_003_cloud_run_deploy.md. Do not run any commands yet. Explain in plain language what Cloud Run, Artifact Registry, Cloud Build, a service account and a revision are. Then give me the full ordered list of gcloud commands you propose, with each one explained: what it does, what GCP resources it creates or changes, whether it can cost money, and how to undo it. Flag any command involving iam, authentication or public access. Do not use the default compute service account and do not create key files. Wait for my approval, and then run the commands one step at a time, pausing after each so I can check the result.

## Review prompt (run in a fresh session after the deploy)
> Review the work on this branch and the commands recorded in CLAUDE.md as a skeptical cloud security engineer. Check: least-privilege IAM, whether the service account has more access than needed, whether anything is public that should not be, instance and cost limits, hardcoded values, and any secrets or key files. Also review the commands for repeatability. Do not make changes, just report.

## Things to try by hand (to build understanding)
- Call the service with no token and watch the 403, then with `gcloud auth print-identity-token`
- In the console, open the service and find its URL, revisions, logs, metrics and the service account it runs as
- Look at the IAM page and find the new service account. Confirm it has no roles on the project
- Open the Artifact Registry repository and find the image and its tag
- Deploy a second revision with a visible change, then move traffic back to the first revision
- Trigger a request, then find that exact request in the logs

## Learning-log note (write after, in my own words)
- What is a revision, and why does Cloud Run keep old ones?
- Why did the first call get a 403, and what changed when I opened access?
- Why a dedicated service account with no roles, instead of the default?
- Where do the logs come from, and how would I find one request?
- What did this cost, and what would make it cost more?