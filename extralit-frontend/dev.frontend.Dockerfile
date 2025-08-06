ARG extralit_server_TAG=develop

FROM extralitdev/extralit-hf-space:${extralit_server_TAG}

USER root

RUN apt-get update && \
    apt-get install -y nodejs npm

USER extralit

WORKDIR /home/extralit/frontend

COPY --chown=extralit:extralit dist ./dist
COPY --chown=extralit:extralit .nuxt ./.nuxt
COPY --chown=extralit:extralit package.json ./package.json
COPY --chown=extralit:extralit package-lock.json ./package-lock.json
COPY --chown=extralit:extralit nuxt.config.ts ./nuxt.config.ts

# NOTE: Right now this Docker image is using dev.extralit.io as server.
# If we want to use a built-in server in the future to check all functionality we can modify the following Procfile
# content adding ElasticSearch and extralit-server processes.
RUN npm install && \
    echo 'frontend: cd /home/extralit/frontend && HOST=0.0.0.0 PORT=3000 npm run start\n' > /home/extralit/Procfile.frontend

WORKDIR /home/extralit/

EXPOSE 3000
EXPOSE 6900
EXPOSE 9200

CMD ["honcho", "start", "--procfile", "Procfile.frontend"]
