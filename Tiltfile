
# version_settings() enforces a minimum Tilt version
# https://docs.tilt.dev/api.html#api.version_settings
version_settings(constraint='>=0.23.4')

# Read the ENV environment variable
ENV = str(local('echo $ENV')).strip()

# Check if ENV is set to 'dev' for local development
if ENV == 'dev':
    # Storage policy
    k8s_yaml('./k8s/kind/tilt-local-dev-kind-storage-policy.yaml')

# Installing elastic/elasticsearch Helm
load('ext://helm_resource', 'helm_resource', 'helm_repo')
helm_repo('elastic', 'https://helm.elastic.co', labels=['elasticsearch'])
helm_resource(
    name='elasticsearch', 
    chart='elastic/elasticsearch', 
    flags=[
        '--version=8.5.1',
        '--values=./k8s/helm/elasticsearch-helm.yaml'],
    deps=['./k8s/helm/elasticsearch-helm.yaml'],
    port_forwards=['9200'],
    labels=['elasticsearch']
    )


# argilla-server is the backend (FastAPI + SQL)
docker_build(
    'itnrecal-argilla-hf',
    '.',
    dockerfile='docker/api.dockerfile',
    build_args={'ENV': ENV},
    ignore=['./src/argilla/__pycache__', './frontend', './docs', './build', './k8s', './scripts', './dist'],
    live_update=[
        # Sync the source code to the container
        sync('./src/', '/home/argilla/src'),
        sync('./docker/scripts/start_argilla_server.sh', '/home/argilla/'),
        # Restart the server to pick up code changes
        run('/bin/bash start_argilla_server.sh', trigger='./docker/scripts/start_argilla_server.sh')
    ]
)

k8s_yaml(['./k8s/argilla-server-deployment.yaml', './k8s/argilla-server-service.yaml', './k8s/argilla-server-ingress.yaml'])
k8s_resource(
  'argilla-server-deployment',
  port_forwards=['6900'],
  labels=['argilla-server'],
)