# Issue 6: Structured logs (metadata only)

## What
Change the one request log line from plain text (`request method=POST path=/ask status=200 ...`) to one JSON object per line, in the shape Cloud Logging understands: a `severity`, a `message`, and the metadata as separate fields. Add the failure reason (a short code, never the exception text) and a trace id taken from the Cloud Run request header so each app log can be matched to the platform's own request log. Deploy it privately and read the result in Logs Explorer.

## Why
First step of Phase 2 (observability). Plain text can only be searched as text. JSON lets Cloud Logging filter and count by field (`jsonPayload.status>=500`, `severity=ERROR`, `jsonPayload.latency_ms>2000`) and is the base that traces and metrics (next issues) build on. It also teaches what Cloud Run does with stdout, and how a log line is tied to one request.

## Before starting
- PR #3 (Issue 5) is merged; `main` is up to date; this work is on a new branch `issue-6-structured-logs`
- The service can be rebuilt from CLAUDE.md (Issue 5), so the deploy at the end uses the same commands with a new tag (`v5`)
- Decision made: **metadata only**. No question, no answer, no prompt text, no exception message in any log (CLAUDE.md rule 8). LLM content logging is decided later, in the LLM tracing issue

## Acceptance criteria (done when...)
**Code**
- [ ] Each request produces exactly one app log line, and it is valid JSON on one line
- [ ] Fields: `severity`, `message` (fixed text `request`), `method`, `path`, `status`, `latency_ms`, `question_len` (omitted or null when there is none)
- [ ] `severity` follows the status: `INFO` below 400, `WARNING` for 4xx, `ERROR` for 5xx
- [ ] Failures carry an `error` field with the short code the API already returns (`model_timeout`, `model_unavailable`, `internal_error`, `question_empty`, `question_too_long`, `invalid_request`); for an unexpected exception also `exception_type` (the class name only, never the message, which can echo user input)
- [ ] If the request has an `X-Cloud-Trace-Context` header, the log carries `logging.googleapis.com/trace` as `projects/<project-id>/traces/<trace-id>` (project id from `GOOGLE_CLOUD_PROJECT`); no header means no field
- [ ] The question and the answer never appear in any log line, including on error paths (a test proves it, extending the existing one)
- [ ] No new dependency: standard library `logging` and `json` only
- [ ] Tests pass; they check the JSON shape, the severity mapping, the error codes, the trace field with and without the header, and the no-content rule

**Deploy and verify (private, tag `v5`)**
- [ ] Build, deploy and call using only the commands in CLAUDE.md (fix CLAUDE.md if a step is wrong); the service stays private
- [ ] In Logs Explorer, a successful `/ask` shows as a structured entry: fields are expandable under `jsonPayload`, severity icon is correct
- [ ] A query by field works, for example `resource.type="cloud_run_revision" jsonPayload.path="/ask" jsonPayload.status>=400`
- [ ] A 422 (empty question) shows with severity `WARNING` and `error=question_empty`
- [ ] The app log and Cloud Run's own request log for the same call share the same trace id (find both with one `trace=` filter)
- [ ] A search for the question text in the logs finds nothing
- [ ] `docq-run` still has exactly one project role (`roles/aiplatform.user`); no GCP resource or IAM change in this issue
- [ ] CLAUDE.md Commands has the log query examples; README Phase 2 "Structured logs" box is ticked; a Lessons line is added if the agent got anything wrong

## Out of scope
OpenTelemetry and spans, metrics, log-based metrics, dashboards and alerts, logging prompts or answers, request ids beyond the Cloud Trace header, changing log retention or sinks, error reporting service, any app behaviour change.

## Risks and security notes
- **Data exposure:** the main risk. Do not put `str(exc)`, request bodies or model responses in logs. Exception text from the Google client or from validation can repeat the question
- **Cost:** none expected; logs stay far below the free allotment (first 50 GiB a month per project). No new resources
- **Permissions:** none new. Cloud Run writes stdout to Cloud Logging without extra roles
- **Header trust:** `X-Cloud-Trace-Context` is set by the Cloud Run front end but is only a string to the app. Parse defensively (ignore malformed values) and never use it for anything except labelling logs
- **Project id:** if `GOOGLE_CLOUD_PROJECT` is unset (local run), skip the trace field instead of failing
- **Deploy:** private only; no `--allow-unauthenticated`; no key files

## Plan (filled in after asking Claude Code for a plan, before any code)
- GCP resources created or changed: none. A new Cloud Run revision from image `docq:v5` (the repo, bucket and accounts already exist)
- Files expected to change: `app/main.py` (JSON formatter, middleware, error codes via `request.state`), possibly a small `app/logs.py`, `tests/test_ask.py` and a new `tests/test_logging.py`, `CLAUDE.md`, `README.md`
- Decision and tradeoffs: write JSON by hand with the standard library (no new dependency, easy to read) instead of a logging package; trace correlation uses the Cloud Run header now and will be replaced by OpenTelemetry's context in the traces issue; Uvicorn's own access lines stay as plain text for now (noted, not fixed)

## Prompt to give Claude Code (plan first)
> Read CLAUDE.md and ISSUE_006_structured_logs.md. Do not write code yet. Explain in plain language what Cloud Run does with a line printed to stdout, and when it is treated as JSON versus text, and what `severity` and `logging.googleapis.com/trace` do. Then list the files you will change, the exact JSON fields, the severity mapping, how you will make sure the question, answer and exception text never reach a log, and the tests you will write. Note any new dependency (none expected) or GCP change (none expected). Wait for my approval, work on the branch, and pause after each cloud command.

## Review prompt (fresh session, after the change)
> Review the diff on this branch as a skeptical engineer. Check: can the question, the answer or an exception message reach a log on any path (validation error, model error, unexpected error, timeout)? Is every log line valid single-line JSON, including when the path or header contains quotes or newlines? Is the trace header parsed safely? Do the severity and error fields match the status? Do the tests prove the no-content rule rather than assume it? Is any dependency, resource or permission added that should not be? Do not make changes, just report.

## Things to try by hand (to build understanding)
- Before the change, open Logs Explorer and look at an old text line (only `textPayload`); after, compare with `jsonPayload`
- Filter by field: `jsonPayload.latency_ms>2000`, then `severity>=WARNING`
- Make two calls (one good, one empty question) and find both by `jsonPayload.status`
- Take one call's trace id and filter `trace="projects/docq-learning/traces/<id>"`: you should see the Cloud Run request entry and your app entry together
- Print a line that is not JSON (locally) and see how Cloud Logging would show it as plain text

## Learning-log note (write after, in my own words)
- What does Cloud Run do with a line printed to stdout, and what changes when that line is JSON?
- Why log the exception class name but not its message?
- What does the trace id let me do that two separate logs cannot?
- Which of the three signals (logs, metrics, traces) answers "why was this one request slow"?
