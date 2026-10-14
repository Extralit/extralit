## Updating Extralit

This guide covers the update process for Extralit across different deployment options: quickstart, Docker, and Kubernetes.

### General Update Notes

- Always backup your data before performing updates.
- Test updates in a development environment before applying to production.
- Check the Extralit release notes for any specific update instructions or breaking changes.
- After updating, verify that all services are functioning correctly and that data is accessible.

### Quickstart Deployment Update

1. Pull the latest Extralit image:

   ```bash
   docker pull extralit/extralit-hf-space:latest
   ```

2. Stop and remove the existing container:

   ```bash
   docker stop extralit-quickstart
   docker rm extralit-quickstart
   ```

3. Start a new container with the updated image:

   ```bash
   docker run -d --name extralit-quickstart -p 6900:6900 \
     -e EXTRALIT_AUTH_SECRET_KEY=$(openssl rand -hex 32) \
     extralit/extralit-hf-space:latest
   ```

### Docker Deployment Update

1. Update the `docker-compose.yaml` file with the latest Extralit image version.

2. Pull the updated images:

   ```bash
   docker compose pull
   ```

3. Restart the services with the new images:

   ```bash
   docker compose up -d
   ```

4. For database schema changes, run migrations:

   ```bash
   docker compose exec extralit extralit_server database migrate
   ```

<SwmMeta version="3.0.0"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
