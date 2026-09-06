# Deployment

How to run the analyzer for other people. Everything here is about the **current stack**
(``: FastAPI backend + React frontend), which is all this branch contains; the legacy
Streamlit app is covered [at the end](#legacy-streamlit-app).

The service is **stateless**: no database, no volumes, no accounts, and no log is ever written
to disk. A submitted log lives in memory for the duration of the request. That makes
deployment simple and scaling a matter of running more replicas behind a load balancer.

## Quick start (Docker Compose)

```sh
docker compose up --build -d      # first run builds both images
# open http://localhost:8080
```

Two containers:

| Container | Image size | Idle memory | Role |
| --- | --- | --- | --- |
| `frontend` | 49.7 MB | ~24 MB | nginx 1.27: serves the built UI on port 80 (published as 8080) and proxies `/api/` to the backend |
| `backend` | 165 MB | ~40 MB | uvicorn + FastAPI on port 8000, **not published to the host** - only the frontend reaches it |

Because the browser talks to the backend through the frontend's own origin, CORS does not come
into play in this topology.

Stop with `docker compose down`. To publish on another port, change the `ports` mapping of the
`frontend` service (`"8080:80"`).

## Configuration

The backend reads these environment variables; the images set `KNOWLEDGE_DIR` and
`EXAMPLE_LOGS_DIR` already, and `.env.example` lists the rest ready to copy.

| Variable | Default | Effect |
| --- | --- | --- |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins. Only relevant when the UI is served from a different origin than the API (the dev server, or a split deployment). Set it to your real origin then. |
| `STATIC_DIR` | unset | Directory with a built frontend. If it exists, the backend serves the UI itself - see [single container](#single-container). |
| `KNOWLEDGE_DIR` | `/src/knowledge` in the image | The TOML knowledge base. Point it at a bind mount to edit texts on a running deployment. |
| `EXAMPLE_LOGS_DIR` | `/example_logs` in the image | The example logs offered on the landing page. |
| `ISSUE_URL` | this repository's issue tracker | Where the *Report issue* link in the top bar points. |
| `IMPRINT_URL` / `IMPRINT_FILE`, `PRIVACY_URL` / `PRIVACY_FILE` | unset | The operator's legal pages, linked in the lower right corner - see [below](#legal-pages-imprint-and-privacy). |
| `IMPRINT_LABEL`, `PRIVACY_LABEL` | `Impressum`, `Privacy` | Link texts of those two. |

Two limits are **not** environment variables:

* `MAX_LOG_BYTES = 20 * 1024 * 1024` in `backend/app/main.py` - larger requests get
  HTTP 413.
* `client_max_body_size 32m` and `proxy_read_timeout 120s` in `frontend/nginx.conf`.

That file also sets the caching: `/assets/` is immutable (the bundle names carry a content
hash) while `index.html` is `no-cache`. Without the second rule a redeploy keeps serving the
old app to everyone who visited before.

Raise both together if you need to accept bigger logs, and remember that any outer proxy has
its own body-size limit (nginx defaults to 1 MB, which is far too small for CP-SAT logs).

## Legal pages (imprint and privacy)

Operating a public website in Germany and most of the EU requires an imprint (Impressum,
§ 5 DDG) and a privacy statement. Those describe **you as the operator**, not this project, so
the app ships without them: with nothing configured the corner stays empty and no page claims
an imprint that does not exist. Configure them per deployment, in the `.env` next to
`docker-compose.yml` (`cp .env.example .env`).

Configured pages appear as small links pinned to the lower right corner of the window, next to
the log, so that they are always reachable without competing with the analysis. *Report issue*
is separate: it sits in the top bar and is always shown, pointing at this repository's issue
tracker unless `ISSUE_URL` says otherwise.

Two ways, per page:

```sh
# 1. Link out to pages you already have - one line each, nothing to mount.
IMPRINT_URL=https://krupke-algorithms.de/impressum
PRIVACY_URL=https://krupke-algorithms.de/datenschutz
PRIVACY_LABEL=Datenschutz

# 2. Write them as Markdown and let the app show them in a dialog. Uncomment the
#    `volumes:` block of the backend service in docker-compose.yml first.
IMPRINT_FILE=/legal/imprint.md
PRIVACY_FILE=/legal/privacy.md
```

`*_URL` wins if both are given. A file is read per request, so editing a mounted file takes
effect on the next page load without a restart; a file that is missing or empty is **logged as
a warning and its link is omitted**, because a legal link that opens an empty dialog is worse
than none. Check after a deploy:

```sh
docker compose exec backend python -m app.site   # prints the resolved configuration
curl -s http://localhost:8080/api/site           # what the frontend actually receives
```

What the analyzer itself does with personal data is short and worth stating in that privacy
text: a submitted log is parsed in memory, never written to disk and never logged, and the
service sets no cookies and stores nothing in the browser except the chosen theme.

A mounted `legal/imprint.md` is plain Markdown (headings, lists and links render); the
directory is git-ignored, because its contents are yours and not part of this repository. A
German imprint typically needs at least this - check your own case, this is not legal advice:

```markdown
## Impressum

Angaben gemäß § 5 DDG

Name / Firma
Straße und Hausnummer
PLZ Ort

**Kontakt**
E-Mail: ...
Telefon: ...

**Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV**
Name, Anschrift wie oben
```

## Topologies

### Two containers (default)

What `docker compose up` gives you. Recommended: nginx is better at serving static files and
at absorbing slow clients than uvicorn.

### Single container

The backend can serve the built UI on its own, which is convenient for platforms that run one
container per service:

```sh
cd frontend && npm ci && npm run build          # produces dist/
docker run -d -p 8000:8000 \
  -e STATIC_DIR=/static -v "$PWD/dist:/static:ro" cp-sat-log-analyzer-backend
# open http://localhost:8000
```

(`cp-sat-log-analyzer-backend` is the image name `docker compose build` produces - Compose
derives it from the directory, so a differently named checkout gives a different name. Build it
by hand with `docker build -f backend/Dockerfile -t cp-sat-log-analyzer-backend .` from the
repository root.)

Unknown paths fall back to `index.html`, so the client-side routes and deep links
(`?example=915_01`) work. In this mode nginx's body limit does not apply, but
`MAX_LOG_BYTES` still does.

### Behind your own reverse proxy

Terminate TLS outside and forward everything to the `frontend` container. Requirements:

* forward `/` **and** `/api/` to the same upstream (the UI calls `/api` on its own origin),
* allow a body of at least 32 MB (`client_max_body_size 32m` in nginx, `proxy-body-size` in an
  ingress annotation),
* allow a response that takes a few seconds and can be large (see [sizing](#sizing-and-limits)),
* publish the container port on loopback only (`127.0.0.1:8080:80`) so nothing bypasses the
  proxy.

No websockets, no sticky sessions, no shared state.

## Production checklist

```yaml
# docker-compose.prod.yml
# docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
services:
  backend:
    restart: unless-stopped
    mem_limit: 2g
    environment:
      CORS_ORIGINS: "https://logs.example.com"   # only needed for a split origin
  frontend:
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:80"
```

* **Restart policy.** The default compose file has none; add `restart: unless-stopped`.
* **Memory limit.** Give the backend at least 1 GB, 2 GB if strangers can submit logs; see
  below for why.
* **No volumes needed.** Nothing is written, so the containers can run with a read-only root
  filesystem.
* **No authentication.** The API is open by design. If the deployment should not be public,
  put it behind your proxy's auth.
* **Nothing to back up.** Redeploying from the repository restores everything.

## Sizing and limits

Measured on the benchmark corpus (`corpus/`, one process, no concurrency):

| Log | Parse + analyze | JSON response | Peak process memory |
| --- | --- | --- | --- |
| 40 KB, 8 workers, 219 solutions (typical) | 0.1 s | 0.2 MB | tens of MB |
| 7.4 MB, `enumerate_all_solutions`, 292,399 solution events (worst in the corpus) | 2 s | **114 MB** | ~0.8 GB |

Two consequences:

* The response is not bounded by the 20 MB request cap: a log whose search section is
  hundreds of thousands of events long produces a response two orders of magnitude larger than
  the log. Such a log will also strain the browser. If you expose the service publicly and
  care about worst-case load, lower `MAX_LOG_BYTES` rather than relying on the request size.
* Sizing rule of thumb: peak memory is roughly a hundred times the log size. One CPU core per
  concurrent request is enough; parsing is single-threaded and CPU-bound.

## Editing the knowledge base on a running deployment

All explanations, parameter advice and table documentation live in `knowledge/*.toml`, which
is **baked into the backend image** (the insight boxes are Python, see
[architecture.md](architecture.md)). Two ways to change a text in production:

1. **Rebuild** (`docker compose build backend && docker compose up -d backend`) - the normal
   path, keeps image and repository in sync.
2. **Bind-mount** the directory and edit in place:

   ```yaml
   backend:
     volumes:
       - ../knowledge:/knowledge:ro
     environment:
       KNOWLEDGE_DIR: /knowledge
   ```

   The loader re-reads a file when its modification time changes, so an edit is live on the
   next request - no restart. Validate an edit first with
   `cd backend && uv run python -m app.knowledge`, which fails loudly on a broken file
   instead of showing an empty text in the UI.

The example logs behave the same way through `EXAMPLE_LOGS_DIR`.

## Operating it

**Health.** `GET /api/health` returns `{"status": "ok"}`. The compose file already gives the
backend a healthcheck (every 30 s, 5 s timeout, 3 retries); point your orchestrator's probes
at the same endpoint.

**Smoke test after a deploy:**

From the repository root:

```sh
curl -sf http://localhost:8080/api/health
curl -s http://localhost:8080/api/examples | head -c 200      # 10 examples expected
curl -s -X POST http://localhost:8080/api/parse \
  -H 'Content-Type: application/json' \
  --data "$(python3 -c 'import json;print(json.dumps({"text":open("example_logs/915_01.txt").read()}))')" \
  | head -c 200
```

**Logs.** Both containers log to stdout (`docker compose logs -f backend`). The backend logs
uvicorn access lines only; log contents are never logged.

**What to rebuild after a change:**

| Changed | Rebuild |
| --- | --- |
| `knowledge/*.toml`, `example_logs/` | `backend` (or bind-mount, see above) |
| `backend/app/`, `cpsatlog/` | `backend` |
| `frontend/src/` | `frontend` |
| `frontend/nginx.conf` | `frontend` |
| `.env` (issue link, legal pages) | nothing - `docker compose up -d backend` re-creates the container with the new values |

**Rollback.** `git checkout <previous commit> && docker compose up --build -d`. There is no
migration and no state, so a rollback is complete.

**Build context.** The backend image is built from the **repository root** (see
`docker-compose.yml`), because it needs `cpsatlog`, `knowledge` and `example_logs`
next to the app. Keep that in mind when building the image by hand:
`docker build -f backend/Dockerfile .` from the root.

## Continuous integration

`.github/workflows/ci.yml` runs three independent jobs on every push and pull request, and
weekly on Friday: the parser library and the backend (`ruff check`, `ruff format --check`,
`ty`, `pytest`, plus a knowledge-base load for the backend) and the frontend (`npm run lint`,
`npm run build`). The weekly run additionally upgrades OR-Tools to its newest release before
running the parser suite, so a changed log format surfaces there first - see
[development.md](development.md) for the same commands locally.

## Legacy Streamlit app

<https://cpsat-log-analyzer.streamlit.app/> is served by Streamlit Community Cloud from `app.py`
of the **`legacy` branch**: it installs `requirements.txt` and runs `streamlit run app.py` for
you, and needs no configuration. That app is not in this branch any more, so the Streamlit
Community Cloud app must be pointed at `legacy` (Manage app -> Settings -> Branch); otherwise
its next redeploy finds no `app.py`. Its structure, features and screenshots are documented in
`docs/legacy-streamlit-app.md` on that branch.

It shares no code with `` and is feature-frozen: new work happens here.
