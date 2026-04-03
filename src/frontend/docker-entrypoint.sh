#!/bin/sh
set -e

SSL_CERT=/etc/nginx/ssl/portal.fullchain.crt
SSL_KEY=/etc/nginx/ssl/portal.key
SSL_CONF=/etc/nginx/conf.d/ssl.conf

write_ssl_conf() {
    cat > "$SSL_CONF" << 'NGINX_EOF'
server {
    listen 8443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/ssl/portal.fullchain.crt;
    ssl_certificate_key /etc/nginx/ssl/portal.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers         ECDH+AESGCM:ECDH+AES256:ECDH+AES128:!aNULL:!MD5:!DSS;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    root  /usr/share/nginx/html;
    index index.html;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options            "SAMEORIGIN" always;
    add_header X-Content-Type-Options     "nosniff" always;
    add_header Referrer-Policy            "strict-origin-when-cross-origin" always;

    location /api/ {
        proxy_pass         http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
    }

    location / {
        try_files $uri /index.html;
    }
}
NGINX_EOF
}

apply_ssl() {
    if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
        if [ ! -f "$SSL_CONF" ]; then
            write_ssl_conf
            echo "[ssl-watcher] SSL config written — reloading nginx"
            nginx -s reload 2>/dev/null || true
        fi
    else
        if [ -f "$SSL_CONF" ]; then
            rm -f "$SSL_CONF"
            echo "[ssl-watcher] SSL config removed — reloading nginx"
            nginx -s reload 2>/dev/null || true
        fi
    fi
}

# Initial apply before nginx starts
apply_ssl

# Background watcher: checks every 30 s for cert changes
( while true; do sleep 30; apply_ssl; done ) &

exec "$@"
