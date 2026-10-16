#!/usr/bin/env bash
# Run from the server's checkout. Keeps existing volumes and configuration.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
branch="$(git branch --show-current)"
case "$branch" in
  main|master) ;;
  *) echo "Switch this checkout to main or master before deploying." >&2; exit 1 ;;
esac
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Tracked files have local changes. Commit or preserve them before updating." >&2
  exit 1
fi
if command -v docker >/dev/null 2>&1; then
  engine=docker
elif command -v podman >/dev/null 2>&1; then
  engine=podman
else
  echo "Docker Compose or Podman Compose is required on the server." >&2
  exit 1
fi
"$engine" compose version >/dev/null
git fetch origin "$branch"
git merge --ff-only "origin/$branch"
export BUILD_SHA="$(git rev-parse --short HEAD)"
"$engine" compose up -d --build backend worker frontend
printf '\nUpdated %s at %s. Check the footer for Interface 2.2.0.\n' "$branch" "$BUILD_SHA"
printf 'Verify frontend build: curl -fsS http://localhost:8080/release.json\n'
