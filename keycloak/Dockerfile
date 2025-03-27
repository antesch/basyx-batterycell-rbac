# ---- STAGE 1: Maven Build ----
    FROM maven:3-eclipse-temurin-17 AS build

    # Build ARGs (werden zur Build-Zeit gesetzt)
    ARG HTTP_PROXY
    ARG HTTPS_PROXY
    
    # Explizit zur Umgebung machen – damit RUN darauf zugreifen kann
    ENV http_proxy=${HTTP_PROXY}
    ENV https_proxy=${HTTPS_PROXY}
    
    WORKDIR /workspace
    
    COPY ./initializer/pom.xml /workspace/pom.xml
    COPY ./initializer/src /workspace/src
    COPY ./realm/D4E-realm.template.json /workspace/D4E-realm.template.json
    COPY settings.template.xml /workspace/settings.template.xml
    
    # Install gettext (für envsubst) und ggf. generate settings.xml
    RUN apt-get update && apt-get install -y gettext
    
    # Nur settings.xml erzeugen, wenn Proxy gesetzt ist
    RUN if [ -n "$HTTP_PROXY" ]; then \
          echo "Using proxy: $HTTP_PROXY"; \
          export PROXY_HOST=$(echo "$HTTP_PROXY" | cut -d/ -f3 | cut -d: -f1); \
          export PROXY_PORT=$(echo "$HTTP_PROXY" | rev | cut -d: -f1 | rev); \
          mkdir -p /root/.m2 && \
          envsubst '${PROXY_HOST} ${PROXY_PORT}' < /workspace/settings.template.xml > /root/.m2/settings.xml; \
        else \
          echo "No proxy configured – skipping settings.xml"; \
        fi
    
    RUN echo "--- Effective settings.xml ---" && cat /root/.m2/settings.xml || echo "No settings.xml present"
    
    # Maven install mit oder ohne settings.xml
    RUN if [ -f /root/.m2/settings.xml ]; then \
          mvn --settings /root/.m2/settings.xml install; \
        else \
          mvn install; \
        fi
    
    # ---- STAGE 2: Final Keycloak Container ----
    FROM keycloak/keycloak:24.0.4
    
    # Kopiere die gebaute JAR und Realm-Template
    COPY --from=build /workspace/target/org.eclipse.digitaltwin.basyx.v3.clients-keycloak-issuer-initializer.jar /opt/keycloak/providers/issuer-initializer.jar
    COPY --from=build /workspace/D4E-realm.template.json /opt/keycloak/data/import/D4E-realm.template.json
    
    # Kopiere envsubst von Stage 1 (optional)
    COPY --from=build /usr/bin/envsubst /usr/local/bin/envsubst
    
    # Dein entrypoint-Skript
    COPY entrypoint.sh /opt/scripts/entrypoint.sh
    
    ENTRYPOINT ["/opt/scripts/entrypoint.sh"]
    