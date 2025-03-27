#!/bin/sh
set -e

# Generate final nginx.conf from template
envsubst '${HOSTNAME} ${PORT}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/nginx.conf

# Optional: print generated config for debugging
echo "Generated nginx.conf:"
cat /etc/nginx/nginx.conf

# Start nginx
exec nginx -g 'daemon off;'