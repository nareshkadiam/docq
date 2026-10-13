# Issue 5: Tear down everything, then redeploy from scratch

## What
Delete every cloud resource created for DocQ in Issues 3 and 4 (but keep the GCP project, billing link and budget alert). Prove nothing is left running or billing. Then rebuild the whole thing using only the commands recorded in CLAUDE.md, and fix any command that turns out to be missing, wrong or in the wrong order. End state: `/ask` works again on a private service, and the written commands are proven to be complete.

## Why
This is rung 5 of the confidence ladder, the last rung of Phase 1. Two skills matter before Terraform and CI/CD automate things: knowing exactly what exists (and what costs money), and being able to recreate it without guessing. If the written commands cannot rebuild the system, they are not documentation, they are hope. Cleaning up properly is also the habit that stops forgotten resources from billing for months.

## Before starting
- Issue 4 is merged and deployed (`/ask` works with an identity token)
- Working copy is on an up-to-date `main`, and the work is done on a new branch
- Same project (`docq-learning`) and region (`europe-west2`); the Gemini location stays `eu`
- Billing check from Issue 4 done (note the cost of the test calls), so this issue's cost is measured separately
- The permission checker may block some `iam` or `delete` commands. If so, I can run them myself by typing `!` before the command, then tell Claude Code to continue

## What exists today (inventory, verified before writing this issue)
Claude Code must re-check this list with fresh `list` commands before deleting anything, because things may have changed.

| Resource | Name | Created in |
|---|---|---|
| Cloud Run service | `docq` (all revisions) | Issues 3-4 |
| Artifact Registry repository | `docq` in `europe-west2` (images `v1`, `v2`, `v3`) | Issue 3 |
| Service account (runtime) | `docq-run` | Issue 3 |
| Service account (build) | `docq-build` | Issue 3 |
| Project role | `roles/aiplatform.user` on `docq-run` | Issue 4 |
| Project role | `roles/logging.logWriter` on `docq-build` | Issue 3 |
| Repo role | `roles/artifactregistry.writer` on `docq-build` (goes away with the repo) | Issue 3 |
| Bucket role | `roles/storage.objectViewer` on `docq-build` (goes away with the bucket) | Issue 3 |
| Cloud Storage bucket | `docq-learning_cloudbuild` (build source uploads) | Issue 3 |
| Enabled APIs | Cloud Run, Artifact Registry, Cloud Build, Vertex AI (and helpers) | Issues 3-4 |
| Local only | Application Default Credentials (my login), under `%APPDATA%\gcloud` | Issue 4 |

Not ours and not to be touched: the default compute service account (`<project-number>-compute@...`), the project itself, the billing link, the budget alert, Cloud Logging's default log storage.

## Acceptance criteria (done when...)
**Teardown**
- [ ] Before deleting anything, the inventory above is re-checked with `list` commands and saved in the issue notes
- [ ] Claude Code explains the order of deletion and why (for example, the service before the images, the images before the repository, access grants before the accounts that hold them)
- [ ] Each delete command is shown with the exact resource name and a `describe` or `list` of that one resource first. No wildcards, no deleting the project
- [ ] The Cloud Run service, Artifact Registry repository, build bucket, both service accounts, and every role binding that belonged to them are gone
- [ ] No leftover `deleted:serviceAccount:...` entries remain in the project IAM policy (deleting an account does not remove the grants it held)
- [ ] A final set of `list` commands shows none of the resources above, and I note anything that remains and why (for example enabled APIs, which are free, or the default compute account, which is not ours)
- [ ] The project, billing link and budget alert still exist
- [ ] I understand why `https://<service>-<project-number>.<region>.run.app` should come back as the same URL after the redeploy, and I check whether it does

**Redeploy from scratch**
- [ ] The rebuild uses only the commands recorded in CLAUDE.md. Any step that fails, is missing or is in the wrong order is fixed **in CLAUDE.md**, not worked around silently
- [ ] The commands are read in a fresh session by Claude Code, which must say if anything is unclear before running it
- [ ] The new service is **never public**: anonymous `/health` and `/ask` return 403, and an identity token returns the right answers
- [ ] The service account `docq-run` ends with exactly one project role (`roles/aiplatform.user`) and `docq-build` with the roles it needs, nothing more
- [ ] The service is limited to 2 instances and scales to zero, and the image is tagged with a version, not only `latest`
- [ ] The logs show a request with metadata only; the question and answer are not logged
- [ ] CLAUDE.md has a **Teardown** section with the verified commands, in order, plus a **Rebuild checklist** that matches what actually worked
- [ ] I write down how long the teardown and the rebuild each took, and what was slower or more confusing than expected
- [ ] I check billing the next day and note the cost of Issues 3-5 combined and what, if anything, was still charged after teardown

## Out of scope
Deleting the GCP project, changing the budget, Terraform (automating this is later), GitHub Actions, Workload Identity Federation, tracing and metrics, retrieval and documents. Disabling APIs is optional; leaving them enabled costs nothing.

## Risks and security notes
- Deleting is the dangerous part of this issue. Claude Code must explain each `delete` first (CLAUDE.md rule), name the exact resource, and pause so I can check
- Do not delete the project: it would also remove the budget alert and make Issue 5's "redeploy" mean something different (a project and billing setup, not a rebuild)
- Never leave the rebuilt service public, even briefly. Keep it private from its first deploy, and call it with a token
- Do not create or download service account key files during the rebuild; do not paste tokens into chat or files
- Before `gcloud builds submit .`, list what will be uploaded (`gcloud meta list-files-for-upload .`) and confirm no credential file is in the repo folder (a copy of the local login credentials appeared there once in Issue 4)
- IAM changes can take a minute or two to apply; remember to wait and test again before assuming a command failed
- The Cloud Build source bucket is created automatically by the first build. Deleting it now is fine; the rebuild recreates it, but the build account needs its read role again, so the role order in CLAUDE.md matters

## Prompt to give Claude Code (plan first)
> Read CLAUDE.md and ISSUE_005_teardown_redeploy.md. Do not run any commands yet. First explain in plain language why deletion order matters and what is left behind when you delete a service account that still has IAM grants. Then give me the full ordered teardown list: for each command say what it deletes (exact resource name), whether it can be undone, whether it affects cost, and the `list` or `describe` command that shows the resource first. Flag every `iam` and `delete` command. After teardown give me the verification commands that prove nothing billable is left. Then read the Deploy commands in CLAUDE.md as if you had never seen this project, tell me anything that is missing, wrong, ambiguous or in the wrong order, and propose the fixes to CLAUDE.md before I approve the rebuild. Wait for my approval, work on a new branch, and pause after each command so I can check the result.

## Review prompt (run in a fresh session after the rebuild)
> Review the diff on this branch and the commands recorded in CLAUDE.md as a skeptical cloud engineer who has to rebuild this system tomorrow without help. Check: is the teardown order safe and complete, would anything keep billing after it, are stale IAM entries cleaned up, does the rebuild checklist match what really worked, is any command still missing or ordered wrong, is the service private from its first deploy, are the service accounts least-privilege, and is any credential or key file anywhere. Do not make changes, just report.

## Things to try by hand (to build understanding)
- Before teardown, open the Billing reports and the Cloud Run, Artifact Registry and Storage pages in the console. After teardown, open them again and compare
- In the console IAM page, look for rows that say "Deleted service account" right after the accounts are removed, then understand why they are harmless but untidy
- After redeploying, check that the service URL is the same as before, and that revision names start again at `00001`
- Break the rebuild on purpose once (for example, skip the `aiplatform.user` role), call `/ask`, and find the permission error in the logs
- Time the rebuild with a stopwatch, then think about which steps a script could do for you
- Try calling the deleted service's URL before and after the rebuild to see what the 404 or 403 looks like

## Stretch (optional): a first script
Turn the verified rebuild commands into one PowerShell script (`scripts/rebuild.ps1`) that takes the project ID and region as parameters, stops at the first error, and never makes the service public. Review it line by line. This is the stepping stone to Terraform.

## Learning-log note (write after, in my own words)
- Why does the order of deletion matter, and what is left behind when a service account is deleted?
- Which resources cost money while idle, and which cost nothing until used?
- What was missing or wrong in my written commands, and how did the rebuild show it?
- Why should the project, billing link and budget alert survive a teardown?
- What did Issues 3-5 cost in total, and what would make it cost more?
