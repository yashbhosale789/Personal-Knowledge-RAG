# Redis + Docker Commands Reference — Rate Limiting & Semantic Caching

Local and production both run Redis Stack (`redis/redis-stack`); only the way you reach the container differs:

| | Local (dev) | Production (EC2) |
| --- | --- | --- |
| Started by | `docker run --name redis-stack ...` | Docker Compose, service `redis` |
| Container name | `redis-stack` | `<project>-redis-1` (no `container_name` is set) |
| Command prefix | `docker exec -it redis-stack redis-cli` | `docker compose -f docker-compose.prod.yml exec redis redis-cli` |

The local sections below use the local prefix; see *Production* at the end for the EC2 equivalents.

Current semantic-cache index: `semantic_cache_idx_v2` (Phase 13.2 added a `namespace` tag; see *Production*).

# Local (dev)

## Container setup (one-time only)

```bash
docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

Creates and starts the Redis Stack container. Only run this once — running it again will fail because a container named `redis-stack` already exists.

## Container lifecycle

```bash
docker ps
```

Lists running containers. Confirm `redis-stack` shows status `Up`.

```bash
docker ps -a
```

Lists all containers, including stopped ones — use this if `docker ps` doesn't show `redis-stack` at all.

```bash
docker start redis-stack
```

Starts an already-created-but-stopped container. Use this (not `docker run`) if the container exists but isn't running.

```bash
docker exec -it redis-stack redis-cli ping
```

One-off health check — should return `PONG`.

## Entering the interactive CLI

```bash
docker exec -it redis-stack redis-cli
```

Drops you into the interactive `redis-cli` prompt inside the container. Use this for any multi-step inspection session.

## One-liner CLI commands (run from outside, without entering the interactive prompt)

Pattern: `docker exec -it redis-stack redis-cli <command>`

```bash
docker exec -it redis-stack redis-cli FT._LIST
```

Lists all RediSearch indexes that currently exist.

```bash
docker exec -it redis-stack redis-cli FT.INFO semantic_cache_idx_v2
```

Shows the full schema and stats for a specific index.

```bash
docker exec -it redis-stack redis-cli FT.DROPINDEX semantic_cache_idx_v2
```

Deletes the index only; the `cache:*` entries stay (adding `DD` deletes them too). Use when you need to recreate an index from scratch (e.g. after a schema change).

```bash
docker exec -it redis-stack redis-cli DEL cache:<key>
```

Deletes a specific cache entry by its full key.

## Commands used inside the interactive `redis-cli` prompt

### Rate limiter keys

```bash
KEYS ratelimit:*
GET ratelimit:<key>
TTL ratelimit:<key>
```

### Semantic cache keys

```bash
KEYS cache:*
HGETALL cache:<key>
TTL cache:<key>
```

### RediSearch index inspection

```bash
FT._LIST
FT.INFO semantic_cache_idx_v2
FT.DROPINDEX semantic_cache_idx_v2
```

Cache keys are `cache:<sha256(namespace|query)>`. The namespace is a hash of `config.PROMPT_VERSION` plus the answering and citation-verifier models, so a prompt or model change makes old entries miss; they expire by TTL (24 h).

# Production (EC2)

SSH to the instance, then work from the deploy directory (`APP_DIR` in `deploy/deploy.sh`):

```bash
cd /home/ubuntu/rag
export IMAGE_TAG="$(cat .image_tag)"
docker ps --format '{{.Names}}  {{.Image}}  {{.Status}}'
```

`docker-compose.prod.yml` requires `IMAGE_TAG` (`${IMAGE_TAG:?set IMAGE_TAG}`), and only `deploy/deploy.sh` exports it. Without the `export`, every `docker compose -f docker-compose.prod.yml ...` command fails with `required variable IMAGE_TAG is missing a value`. Take the value from `.image_tag` (the running deploy), never a made-up tag: a later `up` would otherwise swap the app image. The export lasts for the current SSH session only.

`docker ps` confirms the Redis container is up and shows its real name (needed only for the `docker exec` form).

Pattern: `docker compose -f docker-compose.prod.yml exec redis redis-cli <command>`

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
docker compose -f docker-compose.prod.yml exec redis redis-cli FT._LIST
docker compose -f docker-compose.prod.yml exec redis redis-cli FT.INFO semantic_cache_idx_v2
docker compose -f docker-compose.prod.yml exec redis redis-cli DBSIZE
```

Health check (`PONG`), list indexes, inspect the cache index, count keys.

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli
```

Interactive prompt; the commands under *Commands used inside the interactive `redis-cli` prompt* work unchanged. Prefer `SCAN 0 MATCH cache:* COUNT 100` over `KEYS cache:*` here: `KEYS` blocks Redis while it walks every key.

Equivalent without Compose: `docker exec -it <name-from-docker-ps> redis-cli <command>`.

## One-time cleanup after the Phase 13.2 deploy

**Done 2026-10-26** on production after deploy `49eb33f`; `FT._LIST` now shows only `semantic_cache_idx_v2`. Kept for reference.

Phase 13.2 replaced `semantic_cache_idx` with `semantic_cache_idx_v2`. The app creates the new index at startup; the old one is left behind. **After** the 13.2 deploy is live (dropping it earlier makes the running old app miss every lookup):

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli FT._LIST
# expect: semantic_cache_idx and semantic_cache_idx_v2
docker compose -f docker-compose.prod.yml exec redis redis-cli FT.DROPINDEX semantic_cache_idx
# expect: OK
docker compose -f docker-compose.prod.yml exec redis redis-cli FT._LIST
# expect: semantic_cache_idx_v2 only
```

**Do not add `DD`.** Both indexes cover the same `cache:` prefix, so `FT.DROPINDEX semantic_cache_idx DD` would also delete the entries the v2 index serves. The pre-13.2 entries have no `namespace` tag, are never matched by v2 lookups, and expire within 24 h on their own.
