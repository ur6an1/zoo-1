#!/usr/bin/env bash
# Sync production working tree with GitHub and preserve server-side changes as commits.
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/zoo_bot}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"
LOCK_FILE="/tmp/zoo_bot_git_sync.lock"

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "$(date -Is) sync skipped: lock is busy"
  exit 0
fi

cd "${PROJECT_DIR}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "$(date -Is) sync failed: not a git repository"
  exit 1
fi

# Commit any non-ignored production changes before pulling, so history is never lost.
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "chore(server): snapshot $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  fi
fi

git fetch "${REMOTE}" "${BRANCH}" --prune

git pull --rebase --autostash "${REMOTE}" "${BRANCH}"
git push "${REMOTE}" "${BRANCH}"

echo "$(date -Is) sync ok: $(git rev-parse --short HEAD)"
