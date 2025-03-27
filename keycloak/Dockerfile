FROM maven:3-eclipse-temurin-17 AS build

# Proxy config from Compose/.env
ARG HTTP_PROXY
ARG HTTPS_PROXY

ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}

WORKDIR /workspace

COPY ./initializer/pom.xml /workspace/pom.xml
COPY ./initializer/src /workspace/src
COPY ./realm/D4E-realm.template.json /workspace/D4E-realm.template.json
COPY settings.template.xml /workspace/settings.template.xml

# test snippet
RUN echo "Proxy = $http_proxy" && curl -I https://repo.maven.apache.org

RUN apt-get update && apt-get install -y gettext

# Extract proxy host/port and build settings.xml dynamically
RUN export PROXY_HOST=$(echo $http_proxy | cut -d/ -f3 | cut -d: -f1) && \
    export PROXY_PORT=$(echo $http_proxy | rev | cut -d: -f1 | rev) && \
    echo "Using proxy $PROXY_HOST:$PROXY_PORT" && \
    mkdir -p /root/.m2 && \
    envsubst '${PROXY_HOST} ${PROXY_PORT}' < /workspace/settings.template.xml > /root/.m2/settings.xml

# debug
RUN echo "--- Effective settings.xml ---" && cat /root/.m2/settings.xml && echo "---------------------------"

RUN mvn install

# ---- STAGE 2: Final Keycloak Runtime Image ----
FROM keycloak/keycloak:24.0.4

# Copy the built Keycloak provider JAR
COPY --from=build /workspace/target/org.eclipse.digitaltwin.basyx.v3.clients-keycloak-issuer-initializer.jar /opt/keycloak/providers/issuer-initializer.jar

# Copy the realm import template
COPY --from=build /workspace/D4E-realm.template.json /opt/keycloak/data/import/D4E-realm.template.json

# Copy envsubst from build stage into runtime container
COPY --from=build /usr/bin/envsubst /usr/local/bin/envsubst

# Copy the entrypoint script (must be executable on host)
COPY entrypoint.sh /opt/scripts/entrypoint.sh

# Start with the custom entrypoint
ENTRYPOINT ["sh", "/opt/scripts/entrypoint.sh"]
