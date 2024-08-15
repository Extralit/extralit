# Create k3d cluster for local development with ctlptl and Tilt
ctlptl create registry ctlptl-registry --port=5005
ctlptl apply -f examples/deployments/k8s/k3d/k3d-config.yaml

# Clean up disk space
docker image prune -af

# Set up the development environment
git remote add upstream https://github.com/argilla-io/argilla
