# Local Compose Runtime Contract

## Scenario: Docker Desktop Full-Stack Startup

### 1. Scope / Trigger

- Trigger: a personal user starts the default `stockmarket` Compose project
  from the CLI or Docker Desktop and expects the web application to be usable.
- Scope: `docker-compose.yml`, default service ports, container health ordering,
  restart behavior, and local runbook commands.
- Non-goals: production deployment, TLS, remote hosting, secrets distribution,
  or changes to the isolated `stock-acceptance` project.

### 2. Signatures

- Full-stack command: `docker compose up -d --build`.
- Default services: `db`, `redis`, `api`, `worker`, `beat`, and `web`.
- Host endpoints: `GET http://127.0.0.1:8000/health` and
  `GET http://127.0.0.1:3000/zh`.
- Web environment: `API_BASE_URL=http://api:8000` and
  `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`.

### 3. Contracts

- The default Compose file includes a web service built from the repository's
  web Dockerfile, binds Next.js to `0.0.0.0:3000`, and publishes host port 3000.
- PostgreSQL and Redis health gate API startup. API `/health` gates worker,
  Beat, and web startup.
- Every default service uses `restart: unless-stopped`, so an explicitly
  stopped service stays stopped while Docker Desktop restarts active services.
- Server-rendered web requests use the Compose hostname `api`; browser requests
  use the host-published API address.
- `docker-compose.acceptance.yml` remains a separate project with its existing
  13000/18000/55432/56379 host ports.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Default Compose config resolves | Six required services and 3000/8000 ports |
| Database or Redis unhealthy | API waits instead of starting migrations early |
| API unhealthy | Web, worker, and Beat wait |
| Web container restarts | `/zh` recovers on host port 3000 |
| Acceptance config resolves | Existing isolated ports/project remain unchanged |
| Host-side development selected | `docker compose up -d db redis` remains valid |

### 5. Good / Base / Bad Cases

- Good: one build creates all six containers; Docker Desktop restarts the
  project and `/zh` returns HTTP 200 without a host-side `npm run dev:web`.
- Base: a developer starts only `db redis` and runs API/Web on the host.
- Bad: default Compose omits `web`, maps only acceptance port 13000, points SSR
  at host loopback from inside the container, or starts web before API health.

### 6. Tests Required

- `docker compose config --quiet` succeeds and `config --services` includes all
  six services.
- The resolved default model publishes web 3000 and API 8000 with the documented
  environment and healthy dependency conditions.
- The isolated acceptance model still passes `config --quiet`.
- Runtime smoke builds/starts the default stack, asserts API and localized web
  HTTP 200, restarts web, and asserts the page recovers.

### 7. Wrong vs Correct

#### Wrong

```yaml
services:
  db: {}
  redis: {}
  api: {}
```

#### Correct

```yaml
web:
  ports: ["3000:3000"]
  environment:
    API_BASE_URL: http://api:8000
  depends_on:
    api:
      condition: service_healthy
```
