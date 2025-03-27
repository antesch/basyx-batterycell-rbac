#!/bin/sh
set -e

echo "----------- Keycloak Entrypoint -----------"
echo "HOSTNAME: $HOSTNAME"
echo "PORT: $PORT"
echo "WEB_UI_BASE_PATH: $WEB_UI_BASE_PATH"


if [ "$HOSTNAME" = "localhost" ]; then
  HOST_PORT=":$PORT"
  SCHEME="http"
else
  HOST_PORT=""
  SCHEME="https"
fi

export HOSTNAME WEB_UI_BASE_PATH HOST_PORT SCHEME

envsubst '${HOSTNAME} ${WEB_UI_BASE_PATH} ${HOST_PORT} ${SCHEME}' \
  < /opt/keycloak/data/import/D4E-realm.template.json \
  > /tmp/D4E-realm.json

echo "--- Rendered D4E-realm.json ---"
cat /tmp/D4E-realm.json
echo "-------------------------------"

/opt/keycloak/bin/kc.sh import --file /tmp/D4E-realm.json

exec /opt/keycloak/bin/kc.sh start --optimized
