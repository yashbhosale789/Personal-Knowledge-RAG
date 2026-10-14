#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/home/ubuntu/rag
COMPOSE="docker compose -f docker-compose.prod.yml"
IMAGE_REPO=ghcr.io/yashbhosale789/personal-knowledge-rag

NEW="${1:-}"
[[ "$NEW" =~ ^[0-9a-f]{40}$ ]] || { echo "usage: deploy.sh <40-char commit sha>" >&2; exit 2; }

exec 9>/tmp/rag-deploy.lock
flock -n 9 || { echo "another deploy is running" >&2; exit 1; }

cd "$APP_DIR"
PREV="$(cat .image_tag 2>/dev/null || true)"

wait_healthy() {
  local cid status
  for _ in $(seq 1 84); do
    cid="$($COMPOSE ps -q app)"
    status="$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo missing)"
    [[ "$status" == healthy ]] && return 0
    [[ "$status" == unhealthy ]] && return 1
    sleep 5
  done
  return 1
}

deploy() {
  export IMAGE_TAG="$1"
  $COMPOSE up -d app || return 1
  wait_healthy
}

echo "deploying $NEW (previous: ${PREV:-none})"
export IMAGE_TAG="$NEW"
$COMPOSE pull --quiet app || { echo "pull failed; nothing changed" >&2; exit 1; }

if deploy "$NEW"; then
  echo "$NEW" > .image_tag
  if [[ -n "$PREV" && "$PREV" != "$NEW" ]]; then echo "$PREV" > .prev_image_tag; fi
  KEEP="$(cat .prev_image_tag 2>/dev/null || true)"
  for img in $(docker images --format '{{.Repository}}:{{.Tag}}' "$IMAGE_REPO"); do
    case "$img" in *":$NEW"|*":$KEEP") ;; *) docker rmi "$img" || true ;; esac
  done
  docker image prune -f >/dev/null
  $COMPOSE exec -T redis redis-cli EVAL "for _, k in ipairs(redis.call('KEYS', 'cache:*')) do redis.call('DEL', k) end return 1" 0 >/dev/null || echo "cache flush failed (non-fatal)" >&2
  $COMPOSE exec -T app python - <<'PY' || echo "warm-up failed (non-fatal)" >&2
import json, os, time, urllib.request
t = time.time()
req = urllib.request.Request(
    "http://localhost:8000/query",
    data=json.dumps({"query": "How do I change a tyre?"}).encode(),
    headers={"Authorization": "Bearer " + os.environ["API_KEY"], "Content-Type": "application/json"},
)
print("warm-up", urllib.request.urlopen(req, timeout=300).status, round(time.time() - t, 1), "s")
PY
  echo "deployed $NEW"
else
  echo "new version unhealthy; rolling back to ${PREV:-none}" >&2
  $COMPOSE logs --tail 40 app >&2 || true
  if [[ -n "$PREV" ]]; then deploy "$PREV" || echo "rollback also failed" >&2; fi
  exit 1
fi