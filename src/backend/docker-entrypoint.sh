#!/bin/sh
set -e

# Fix portal-ssl volume ownership (Docker Desktop creates named volumes as root:root)
if [ -d /app/portal-ssl ]; then
    chown app:app /app/portal-ssl
fi

# ── Auto-generate APP_MASTER_KEY if missing or placeholder ───────────────────
# The key is persisted to a named volume so it survives container restarts.
# Anyone pulling this repo from scratch gets a secure key automatically.
_KEY_FILE="/app/data/.master_key"
_is_placeholder() {
    case "$APP_MASTER_KEY" in
        generate_with__*|""|CHANGE_ME*) return 0 ;;
        *) return 1 ;;
    esac
}

if _is_placeholder; then
    mkdir -p /app/data
    chown app:app /app/data
    if [ -f "$_KEY_FILE" ]; then
        APP_MASTER_KEY=$(cat "$_KEY_FILE")
        echo "[startup] Loaded APP_MASTER_KEY from persisted volume."
    else
        APP_MASTER_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
        echo "$APP_MASTER_KEY" > "$_KEY_FILE"
        chmod 600 "$_KEY_FILE"
        chown app:app "$_KEY_FILE"
        echo "[startup] Generated new APP_MASTER_KEY and saved to volume."
    fi
    export APP_MASTER_KEY
fi
# ─────────────────────────────────────────────────────────────────────────────

exec gosu app:app "$@"
