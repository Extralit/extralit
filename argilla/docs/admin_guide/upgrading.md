## Updating Extralit

This guide covers the update process for Extralit across different deployment options: quickstart, Docker, and Kubernetes.

### General Update Notes

- Always backup your data before performing updates.
- Test updates in a development environment before applying to production.
- Check the Extralit release notes for any specific update instructions or breaking changes.
- After updating, verify that all services are functioning correctly and that data is accessible.


### Kubernetes Deployment Update

1. Update the [extralit repository](https://github.com/extralit/extralit) code from a release version tag, e.g. `v0.2.2`

    ```bash
    git fetch origin tag v0.2.2 && git checkout tags/v0.2.2
    ```

2. Rebuild the  package, which contains the Argilla server and web interface

    First, build the `argilla-frontend` code

    ```bash
    npm install --prefix argilla-frontend
    npm run build --prefix argilla-frontend
    ```

    Finally, build the wheel containing the built argilla-frontend/dist
    
    ```bash
    cp -r argilla-frontend/dist argilla-server/src/argilla_server/static
    rm -rf argilla-server/dist && python -m build -s argilla-server/
    ```

3. Rebuild the `extralit` Python client package

   ```bash
   rm -rf argilla/dist && python -m build -s argilla/
   ```

4. If using Tilt for development:

   - Tilt will automatically detect changes and rebuild/redeploy the service.
   - Manually trigger a rebuild using the ↻ button in the Tilt web interface if needed.

5. For production updates without Tilt:

   - Push the updated Docker image to your repository:

   ```bash
   docker push {DOCKER_REPO}/argilla-server:tag
   docker push {DOCKER_REPO}/extralit-server:tag
   ```

   - Apply the updated Kubernetes configuration:

   ```bash
   kubectl apply -f examples/deployments/k8s/argilla-server-deployment.yaml -n {NAMESPACE}
   kubectl apply -f examples/deployments/k8s/extralit-deployment.yaml -n {NAMESPACE}
   ```

6. Monitor the rollout:

   ```bash
   kubectl rollout status deployment/argilla-server-deployment -n {NAMESPACE}
   ```

   &nbsp;

For database schema changes:

- Run migrations using the `argilla_server` CLI:

```bash
kubectl exec -it deployment/argilla-server-deployment -n {NAMESPACE} -- \
argilla_server database migrate
```

&nbsp;

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

<SwmMeta version="3.0.0"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
