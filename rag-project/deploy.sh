#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/home/ubuntu/rag
COMPOSE="docker compose -f docker-compose.prod.yml"
IMAGE_REPO=ghcr.io/yashbhosale789/personal-knowledge-rag
# Shipped in the image at /app and copied out on deploy, so the server matches the deployed commit.
SYNCED=(deploy.sh docker-compose.prod.yml Caddyfile prometheus.yml)
CHANGED=()

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

# Images built before config shipped in the image carry none of these files; missing ones are skipped.
sync_files() {
  local cid f
  cid="$(docker create "$IMAGE_REPO:$1")" || return 1
  for f in "${SYNCED[@]}"; do
    docker cp "$cid:/app/$f" "$f.new" 2>/dev/null || continue
    if cmp -s "$f" "$f.new"; then rm -f "$f.new"; continue; fi
    cp -p "$f" "$f.prev" 2>/dev/null || true
    chmod --reference="$f" "$f.new" 2>/dev/null || chmod 644 "$f.new"
    mv "$f.new" "$f"  # mv, not cp: this running script keeps reading its old inode
    CHANGED+=("$f")
    echo "updated $f"
  done
  docker rm "$cid" >/dev/null
}

restore_files() {
  local f
  for f in "${CHANGED[@]}"; do
    if [[ -f "$f.prev" ]]; then mv "$f.prev" "$f"; echo "restored $f"; fi
  done
}

# shortcut: compose edits to services other than app apply on their next manual `up`, not here; automate if those change often.
restart_changed() {
  local f
  for f in "${CHANGED[@]}"; do
    case "$f" in
      Caddyfile) $COMPOSE restart caddy || echo "caddy restart failed" >&2 ;;
      prometheus.yml) $COMPOSE restart prometheus || echo "prometheus restart failed" >&2 ;;
    esac
  done
}

deploy() {
  export IMAGE_TAG="$1"
  $COMPOSE up -d app || return 1
  wait_healthy
}

for img in $(docker images --format '{{.Repository}}:{{.Tag}}' "$IMAGE_REPO"); do
  case "$img" in *":$PREV"|*":$NEW") ;; *) docker rmi "$img" || true ;; esac
done
docker image prune -f >/dev/null
FREE_KB="$(df --output=avail -k / | tail -1 | tr -d ' ')"
# a pull stores the ~4 GB image twice (compressed + unpacked); below this it fills the disk and crashes the SSM agent
(( FREE_KB > 6000000 )) || { echo "only $((FREE_KB / 1024)) MB free on /; aborting before pull" >&2; exit 1; }

echo "deploying $NEW (previous: ${PREV:-none})"
export IMAGE_TAG="$NEW"
$COMPOSE pull --quiet app || { echo "pull failed; nothing changed" >&2; exit 1; }
sync_files "$NEW" || echo "config sync failed (non-fatal); keeping current files" >&2

if deploy "$NEW"; then
  echo "$NEW" > .image_tag
  restart_changed
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
  restore_files
  if [[ -n "$PREV" ]]; then deploy "$PREV" || echo "rollback also failed" >&2; fi
  exit 1
fi