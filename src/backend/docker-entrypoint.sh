#!/bin/sh
set -e
# Fix portal-ssl volume ownership (Docker Desktop creates named volumes as root:root)
if [ -d /app/portal-ssl ]; then
    chown app:app /app/portal-ssl
fi
exec gosu app:app "$@"
