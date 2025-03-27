#!/bin/sh
set -e

echo "----------- Keycloak Entrypoint -----------"
echo "HOSTNAME: $HOSTNAME"
echo "PORT: $PORT"
echo "WEB_UI_BASE_PATH: $WEB_UI_BASE_PATH"

# Default-Port setzen, nur wenn leer
if [ -z "$PORT" ]; then
  echo "PORT not set – assuming default 80 (no HOST_PORT suffix)"
  HOST_PORT=""
else
  HOST_PORT=":$PORT"
fi

echo "HOST_PORT: $HOST_PORT"

export HOSTNAME HOST_PORT WEB_UI_BASE_PATH

# Template rendern
envsubst '${HOSTNAME} ${HOST_PORT} ${WEB_UI_BASE_PATH}' \
  < /opt/keycloak/data/import/D4E-realm.template.json \
  > /tmp/D4E-realm.json

echo "--- Rendered D4E-realm.json ---"
cat /tmp/D4E-realm.json
echo "-------------------------------"

# Realm importieren
/opt/keycloak/bin/kc.sh import --file /tmp/D4E-realm.json

# Keycloak starten
exec /opt/keycloak/bin/kc.sh start --optimized