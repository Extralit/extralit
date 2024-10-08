## Updating Extralit

This guide covers the update process for Extralit across different deployment options: quickstart, Docker, and Kubernetes.

### General Update Notes

- Always backup your data before performing updates.
- Test updates in a development environment before applying to production.
- Check the Extralit release notes for any specific update instructions or breaking changes.
- After updating, verify that all services are functioning correctly and that data is accessible.


### Kubernetes Deployment Update

1. Update the service code in the `extralit-server` repository from the `main` branch:

    ```bash
    git pull origin main
    ```

2. Rebuild the Python package and Docker image:
    ```bash
    sh scripts/build_distribution.sh
    ```

3. Update the Docker image tag in the corresponding Kubernetes YAML file or Helm chart values.

4. If using Tilt for development:
    - Tilt will automatically detect changes and rebuild/redeploy the service.
    - Manually trigger a rebuild using the ↻ button in the Tilt web interface if needed.

5. For production updates without Tilt:
    - Push the updated Docker image to your repository:
    ```bash
    docker push {DOCKER_REPO}/service-name:tag
    ```
    - Apply the updated Kubernetes configuration:
    ```bash
    kubectl apply -f path/to/updated/service-config.yaml -n {NAMESPACE}
    ```

6. Monitor the rollout:
    ```bash
    kubectl rollout status deployment/service-name -n {NAMESPACE}
    ```

7. For database schema changes:
    - Run migrations using the `argilla_server` CLI:
    ```bash
    kubectl exec -it deployment/argilla-server -n {NAMESPACE} -- \
    argilla_server database migrate
    ```

8. For frontend updates:
    - Rebuild the frontend:
    ```bash
    sh scripts/build_frontend.sh
    ```
    - Trigger a rebuild of the `argilla-server` in the Tilt web interface or reapply the Kubernetes configuration.



### Quickstart Deployment Update

1. Pull the latest Extralit image:
    ```bash
    docker pull extralit/argilla-quickstart:latest
    ```

2. Stop and remove the existing container:
    ```bash
    docker stop extralit-quickstart
    docker rm extralit-quickstart
    ```

3. Start a new container with the updated image:
    ```bash
    docker run -d --name extralit-quickstart -p 6900:6900 \
      -e ARGILLA_AUTH_SECRET_KEY=$(openssl rand -hex 32) \
      extralit/argilla-quickstart:latest
    ```

### Docker Deployment Update

1. Update the `docker-compose.yml` file with the latest Extralit image version.

2. Pull the updated images:
    ```bash
    docker-compose pull
    ```

3. Restart the services with the new images:
    ```bash
    docker-compose up -d
    ```

4. For database schema changes, run migrations:
    ```bash
    docker-compose exec argilla argilla_server database migrate
    ```
