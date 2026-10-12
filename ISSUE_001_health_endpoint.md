# Issue 1: Tiny web app with a /health endpoint

## What
Create a minimal FastAPI app with one endpoint, `GET /health`, that returns `{"status": "ok"}`. Run it locally.

## Why
This is rung 1 of the confidence ladder. The app is trivial on purpose, so I can focus on the process: issue, plan, branch, tests, review, merge.

## Acceptance criteria (done when...)
- [ ] `GET /health` returns HTTP 200 and `{"status": "ok"}`
- [ ] One automated test covers the endpoint
- [ ] The README or CLAUDE.md Commands section says exactly how to run the app and the test
- [ ] Dependencies are listed in a requirements file with pinned versions
- [ ] A `.gitignore` is in place (no virtual environment or secrets committed)

## Out of scope
Docker, GCP, any LLM calls, authentication.

## Risks and security notes
None expected. No secrets involved. Confirm no `.env` file is committed.

## Prompt to give Claude Code (plan first)
> Read CLAUDE.md and ISSUE_001. Do not write code yet. Explain in plain language what you plan to create, what each file is for, and how I will run and test it. List any dependencies and why they are needed. Wait for my approval.

## Review prompt (run in a fresh session after the build)
> Review the diff on this branch critically as a skeptical senior engineer. Look for bugs, missing tests, security problems, and anything unclear. Do not make changes, just report.

## Learning-log note (write after, in my own words)
- What does the app do when I call /health?
- What is FastAPI doing for me?
- Why is there a test for something this small?
