# Issue 5 notes: teardown and redeploy

## Step 0: inventory before teardown (read-only)
Checked 2026-10-13. gcloud 588.0.0, account nareshkadiam@gmail.com, project `docq-learning`, region `europe-west2`.

| Resource | Found | Notes |
|---|---|---|
| Cloud Run service `docq` | Yes | Revisions `docq-00001-k2t`, `docq-00002-2j5`, `docq-00003-49t`. URL `https://docq-495308482464.europe-west2.run.app`. Last deployed 2026-10-12 17:35 UTC |
| Service invoker policy | Empty | Private, no `allUsers` |
| Artifact Registry repo `docq` | Yes, about 70 MB | Images tagged `v1`, `v2`, `v3` |
| Bucket `docq-learning_cloudbuild` | Yes, location **US** | Four `source/*.tgz` uploads. `docq-build` has `roles/storage.objectViewer`; other bindings are legacy project owner/editor/viewer, not ours |
| Service account `docq-run` | Yes | Runtime |
| Service account `docq-build` | Yes | Build |
| Project role `roles/aiplatform.user` | `docq-run` | Ours |
| Project role `roles/logging.logWriter` | `docq-build` | Ours |
| `deleted:` entries in project policy | None | |
| Enabled APIs | `run`, `artifactregistry`, `cloudbuild`, `aiplatform` (ours) plus many defaults (BigQuery, Dataplex, etc.) | Free to leave enabled |

Not ours, not to be touched:
- Default compute account `495308482464-compute@developer.gserviceaccount.com` (holds `roles/editor`, a broad grant to note for the learning log)
- Cloud Build account `495308482464@cloudbuild.gserviceaccount.com` (`cloudbuild.builds.builder`)
- Google service agents (Artifact Registry, Cloud Build, Container Registry, Pub/Sub, Cloud Run)
- Owner grant for the user, the project, billing link, budget alert, Cloud Logging default storage

## Open points
1. The build bucket is in the US. Check whether a rebuild with `--region europe-west2` creates the same bucket name, since CLAUDE.md grants a role on `gs://${P}_cloudbuild`.
2. Bucket role order: the bucket exists only after the first build attempt, so the first build is expected to fail until `objectViewer` is granted.

## Teardown log (2026-10-13)
Branch `issue-5-teardown-redeploy`. Each delete was explained and approved first.

| Step | Command | Time |
|---|---|---|
| 1 | `gcloud run services delete docq` | 6 s |
| 2 | `gcloud artifacts repositories delete docq` (73.4 MB, v1-v3) | 14 s |
| 3 | `gcloud storage rm -r gs://docq-learning_cloudbuild` | 16 s |
| 4 | `remove-iam-policy-binding` x2 (`aiplatform.user` on docq-run, `logging.logWriter` on docq-build) | a few s |
| 5 | `gcloud iam service-accounts delete` x2 | a few s |

Final check: 0 services, 0 repos, no buckets, only the default compute account left, no `docq` or `deleted:` entries in the project policy, project ACTIVE, billing enabled (the billing account (ID omitted)). Budget alert not yet confirmed.

Surprises:
- The service account list still showed `docq-build` right after the delete; it was gone after ~15 s (eventual consistency). `describe` gives PERMISSION_DENIED "or it may not exist".
- `remove-iam-policy-binding` needs `--condition=None` or it prompts.
- Service `describe` shows a hash URL (`docq-y4t2rkfnxq-nw.a.run.app`); the deterministic one is `docq-495308482464.europe-west2.run.app`.

## Rebuild log (2026-10-13)
Image tag `v4`. Each step explained and approved first.

| Step | Result | Time |
|---|---|---|
| Enable 4 APIs | no-op, already on | 6.5 s |
| Create repo `docq` | ok | 9.5 s |
| Create `docq-run`, `docq-build` | ok, no keys | a few s |
| Grants: aiplatform.user (run), logWriter (build), AR writer on repo (build) | ok | a few s |
| Upload check | 22 files, 59.3 KiB, no credential files | |
| Build 1 | FAILED, 403 `storage.objects.get` for `docq-build` on the new bucket (expected) | 4 s |
| Grant `objectViewer` on `gs://docq-learning_cloudbuild`, wait 60 s | ok | |
| Build 2 | SUCCESS, `docq:v4` | 38 s build, 42.5 s command |
| Deploy private, `/ask` env vars, max 2 instances, min 0 | revision `docq-00001-xdx`, invoker policy empty | 15.3 s |

Checks:
- Anonymous `/health` and `/ask`: 403. With identity token: `/health` 200; `/ask` 200 with a real answer.
- Service URL `https://docq-495308482464.europe-west2.run.app` is identical to before; revisions restarted at `00001`.
- Roles: `docq-run` has only `roles/aiplatform.user`; `docq-build` has `logWriter` plus repo `artifactregistry.writer` and bucket `objectViewer`. No `deleted:` entries.
- Limits: maxScale 2, 1 CPU, 256Mi, min instances not set (scales to zero), image tagged `v4`.
- Logs: request metadata only (`method`, `path`, `status`, `latency_ms`, `question_len`); 0 lines contain the question or answer text.

Surprises:
- Inline JSON quoting for `curl.exe -d` gave HTTP 422 in Windows PowerShell 5.1; a body file works (CLAUDE.md updated).
- The first Cloud Run logs read right after deploy was empty; logs appeared a minute later.
- `gcloud billing budgets list` needs the Cloud Billing Budget API enabled, so the budget alert has to be checked in the console.

## Timings
- Teardown: about 1 minute of command time, plus approval pauses (stopwatch time: to fill)
- Rebuild: (to fill)
- Slower or more confusing than expected: (to fill)

## Billing
- Issue 4 test-call cost: (to fill)
- Issues 3-5 combined, checked the day after: (to fill)
- Anything still charged after teardown: (to fill)
