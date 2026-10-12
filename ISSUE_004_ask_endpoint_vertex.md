# Issue 4: Add an /ask endpoint that calls Gemini through Vertex AI

## What
Add `POST /ask` that takes a question, sends it to a Gemini model on Vertex AI, and returns the answer. The app authenticates to Vertex AI with IAM (the Cloud Run service account), not with an API key. Deploy it and make sure it is not open to the public.

## Why
This is rung 4 of the confidence ladder, and the first time the app has real cost and real risk. It teaches how a cloud workload gets permission to use a managed service without any stored secret (service account + IAM role + Application Default Credentials), and how to put basic limits around a paid model call.

## Before starting
- Issue 3 is merged and the service is deployed
- I am using the same project and region as before
- Model names and regional availability change often. Claude Code must check the current official Google Cloud documentation for the Gemini model name and which regions support it, and must not rely on memory. The model name must be a configuration value (environment variable), not hardcoded.

## Acceptance criteria (done when...)
- [ ] The Vertex AI API is enabled, and I know what enabling an API does
- [ ] `POST /ask` accepts JSON like `{"question": "..."}` and returns JSON with the answer
- [ ] The call uses the current Google-supported SDK for Gemini on Vertex AI, and Claude Code explains why that SDK was chosen
- [ ] Authentication uses Application Default Credentials: locally with `gcloud auth application-default login`, and on Cloud Run with the dedicated service account. **No API key and no key file exist anywhere**
- [ ] The service account is granted the narrowest role that works for calling the model (Claude Code proposes it and explains it, and it is granted to that account only, not to users or `allUsers`)
- [ ] Model name, region and limits come from environment variables, with sensible defaults
- [ ] Limits are in place: maximum question length, maximum output tokens, a request timeout, and a clear error (not a crash or stack trace) when the model call fails
- [ ] Automated tests cover the endpoint **with the model call mocked**. The tests must never call the real model
- [ ] **Public access is removed from the Cloud Run service** (it was opened in Issue 3). I confirm `/health` and `/ask` now return 403 without a token and work with `gcloud auth print-identity-token`
- [ ] Logs show that a request happened, with metadata only (status, latency, question length). **The question text and the answer are not logged**
- [ ] The Commands section and deploy notes in the repo are updated, including how to call a private service with a token
- [ ] I check billing and note the cost of my test calls

## Out of scope
Documents or retrieval (that comes later), authentication inside the app, tracing and metrics (Phase 2), Terraform, GitHub Actions, streaming responses.

## Risks and security notes
- A public endpoint that calls a paid model is an open invitation to run up a bill. That is why public access is removed in this issue. It is the main lesson here
- Do not create or download service account key files, and do not paste any credential into chat or the repo
- Application Default Credentials created locally are stored outside the repo. Confirm nothing from them is copied into the project folder or the Docker image
- User input goes straight into a prompt. Keep the prompt simple for now, and note in the README that prompt injection becomes a real concern once documents are involved (Phase 5)
- Do not log prompts or answers (CLAUDE.md rule 8)
- Keep the instance limit low and the output token limit small while testing

## Prompt to give Claude Code (plan first)
> Read CLAUDE.md and ISSUE_004_ask_endpoint_vertex.md. Do not write code or run commands yet. First check the current official Google Cloud documentation and tell me which Gemini model name, SDK and region you recommend, with a link to where you found it. Explain in plain language how the app will get permission to call Vertex AI without an API key: what Application Default Credentials are, what the service account and the IAM role do, and which exact role you propose and why it is the narrowest that works. Then give me the plan: files to change, the request and response shape, the limits you will add, how the tests will mock the model, and the ordered gcloud commands with each one explained (what it changes, whether it costs money, how to undo it). Flag any iam command and the step that removes public access. Wait for my approval, then work on a new branch and pause after each command so I can check the result.

## Review prompt (run in a fresh session after the deploy)
> Review the diff on this branch and the recorded commands as a skeptical security and cost reviewer. Check: no API keys or key files anywhere, the IAM role is the narrowest that works and is granted only to the service account, public access is really removed, input and output limits exist, prompts and answers are not logged, tests never call the real model, error handling does not leak internals, and nothing hardcoded that should be configuration. Do not make changes, just report.

## Things to try by hand (to build understanding)
- Call `/ask` with an identity token and read the answer. Then call it with no token and see the 403
- Send a question that is too long and see the error
- Temporarily remove the model permission from the service account, call `/ask`, and read the permission error in the logs. Add it back and confirm it works again. This shows exactly what the role is doing
- Find the request in Logs Explorer and confirm the question text is not there
- Look at Vertex AI usage and the billing report to see what a handful of calls cost
- Run the app locally and confirm it uses your own identity via Application Default Credentials, while on Cloud Run it uses the service account

## Stretch (optional): a first look at Secret Manager
Vertex AI needs no secret, which is the point. To still practise secrets handling, create a throwaway secret, grant the service account access to that one secret only, expose it to Cloud Run as an environment variable, and add a test that the app can see it without ever printing it. Then delete the secret. Do not use a real credential for this.

## Learning-log note (write after, in my own words)
- How does the app prove who it is to Vertex AI when there is no API key?
- What is the difference between my identity locally and the service account on Cloud Run?
- Why did I remove public access, and what could have happened if I had not?
- What does each limit (length, output tokens, timeout, instance count) protect against?
- What did this cost, and what would make it cost more?