#!/bin/sh
set -e

# Sicherstellen, dass Variablen gesetzt sind
: "${HOSTNAME:?HOSTNAME not set}"
: "${WEB_UI_BASE_PATH:?WEB_UI_BASE_PATH not set}"

echo "HOSTNAME is: $HOSTNAME"
echo "WEB_UI_BASE_PATH is: $WEB_UI_BASE_PATH"

# Generieren
envsubst '${HOSTNAME} ${WEB_UI_BASE_PATH}' < /opt/keycloak/data/import/D4E-realm.template.json > /tmp/D4E-realm.json

# Debug-Ausgabe
echo "--- Rendered D4E-realm.json ---"
cat /tmp/D4E-realm.json
echo "-------------------------------"

# Import
/opt/keycloak/bin/kc.sh import --file /tmp/D4E-realm.json

# Start Keycloak
exec /opt/keycloak/bin/kc.sh start --optimized
