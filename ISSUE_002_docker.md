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
- run docker conatiner image `docker run --rm -p 8080:8080 docq:local`, then in another window  `docker ps`
- Run the container, call `/health`, then run `docker ps` to see it
- Stop it with `docker stop <container-id>`, and see that the app is gone
- Run it with a different port: `-e PORT=9000` and map the port accordingly
- Inside the running container, run `whoami` (via `docker exec`) and confirm it is not root

## Learning-log note (write after, in my own words)
- What is the difference between an image and a container? -- An image is the packaged, read-only software with all its dependencies (a template). A container is a running instance of that image. Nothing gets installed when it starts; it just runs what is already in the image. I can start many containers from one image.
- Why does the app need to listen on 0.0.0.0 and on $PORT? -- Inside a container, "localhost" (127.0.0.1) means only the container itself, so my browser's request, which arrives through the `-p` port mapping, would never reach the app. 0.0.0.0 means "listen on all network interfaces", which lets the mapped traffic in. $PORT is because Cloud Run decides which port the app must use and passes it in as an environment variable. The app reads PORT and falls back to 8080 when it is not set.
- What does .dockerignore protect me from? -- It is a list of files and folders that are NOT copied into the image: .git, .venv, .env files, caches. It keeps secrets out of the image (anyone with the image could read them), and keeps the image small and builds fast. It is not about dependencies; those are installed from requirements.txt.
- Why is running as non-root better? -- If someone exploits a bug in the app, they only get the limited permissions of that user. They cannot change system files, install tools or do much damage inside the container, and it is harder to escape to the host. It limits the blast radius.