# Redis + Docker Commands Reference — Phase 9 (Rate Limiting & Semantic Caching)

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
docker exec -it redis-stack redis-cli FT.INFO semantic_cache_idx
```

Shows the full schema and stats for a specific index.

```bash
docker exec -it redis-stack redis-cli FT.DROPINDEX semantic_cache_idx
```

Deletes an index. Use when you need to recreate an index from scratch (e.g. after a schema change).

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
FT.INFO semantic_cache_idx
FT.DROPINDEX semantic_cache_idx
```

## Current pending step (schema rename cleanup)

After renaming `query_text`/`answer_text` fields to `query`/`answer` in `semantic_cache.py`, the old index and test entry (created under the old field names) need to be cleared before re-testing:

```bash
docker exec -it redis-stack redis-cli FT.DROPINDEX semantic_cache_idx
docker exec -it redis-stack redis-cli KEYS cache:*
docker exec -it redis-stack redis-cli DEL cache:<paste-the-key-from-above>
```

Then rebuild fresh:

```bash
python -m src.llm.semantic_cache
```
