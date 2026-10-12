# Issue 2: Run the app in a Docker container

## What
Package the existing FastAPI app into a Docker image and run it as a container on my own computer. `GET /health` must work from my browser while the container is running.

## Why
This is rung 2 of the confidence ladder. Cloud Run runs containers, so understanding what a Dockerfile, an image and a container are is the foundation for deploying in Issue 3. Doing it locally first means any problem is easy to see and cheap to fix.

## Before starting
Docker must be installed and running on my computer (Docker Desktop on Mac/Windows, or Docker Engine on Linux). Check with `docker --version` and `docker run hello-world`. If this fails, fix it first. It is not part of this issue.

## Acceptance criteria (done when...)
- [ ] A `Dockerfile` builds an image with no errors
- [ ] A `.dockerignore` keeps unneeded and sensitive files out of the image (git folder, virtual environment, `.env` files, caches)
- [ ] The base image is a specific, pinned version tag (not `latest`)
- [ ] The app listens on the port given by the `PORT` environment variable, defaulting to 8080 (Cloud Run requires this)
- [ ] The app listens on `0.0.0.0` inside the container (not only localhost)
- [ ] The container runs as a non-root user
- [ ] `docker run` with a port mapping makes `/health` return `{"status": "ok"}` in my browser
- [ ] The existing test still passes
- [ ] The Commands section in CLAUDE.md includes the build and run commands

## Out of scope
GCP, Artifact Registry, Cloud Run, any LLM calls, docker-compose, authentication.

## Risks and security notes
- No secrets may be copied into the image (check `.dockerignore`, and that no `COPY . .` pulls in a `.env`)
- Non-root user is required, as a basic container hardening habit
- Pin versions so builds are repeatable
- Ask Claude Code to explain every line of the Dockerfile in the plan

## Prompt to give Claude Code (plan first)
> Read CLAUDE.md and ISSUE_002_docker.md. Do not write code yet. Explain in plain language what a Dockerfile, an image and a container are, then describe the Dockerfile and .dockerignore you plan to create, line by line, and why each line is there. Tell me how the PORT variable will work, how I will build and run it, and what I should see if it works. List anything that could go wrong. Wait for my approval and work on a new branch.

## Review prompt (run in a fresh session after the build)
> Review the diff on this branch critically as a skeptical senior engineer focused on container security and repeatability. Check: pinned versions, non-root user, secrets or unwanted files that could end up in the image, port handling, image size, and anything unclear. Do not make changes, just report.

## Things to try by hand (to build understanding)
- Build the image, then run `docker images` and note its size
- Run the container, call `/health`, then run `docker ps` to see it
- Stop it with `docker stop <container-id>`, and see that the app is gone
- Run it with a different port: `-e PORT=9000` and map the port accordingly
- Inside the running container, run `whoami` (via `docker exec`) and confirm it is not root

## Learning-log note (write after, in my own words)
- What is the difference between an image and a container?
- Why does the app need to listen on 0.0.0.0 and on $PORT?
- What does .dockerignore protect me from?
- Why is running as non-root better?