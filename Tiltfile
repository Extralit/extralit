
# version_settings() enforces a minimum Tilt version
# https://docs.tilt.dev/api.html#api.version_settings
version_settings(constraint='>=0.23.4')

# Read the ENV environment variable
# env = read_local('echo $ENV')

# Check if ENV is set to 'dev' for local development
# if env.strip() == 'dev':
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
custom_build(
    'itnrecal-argilla-hf',
    'python setup.py bdist_wheel && docker build -t $EXPECTED_REF -f docker/Dockerfile .',
    deps=['./src/argilla', './dist/'],
    ignore=['./frontend', './docs', './build', './k8s', './scripts', './dist'],
    live_update=[
        # Sync the built wheels to the container
        sync('./dist/', '/home/argilla/dist/'),
        # Install the updated wheels
        run('pip install --upgrade /home/argilla/dist/*.whl'),
        # Restart server to pick up the new code
        # run('pkill -HUP uvicorn && start_argilla_server.sh')
    ]
)

k8s_yaml(['./k8s/argilla-server-deployment.yaml', './k8s/argilla-server-service.yaml', './k8s/argilla-server-ingress.yaml'])
k8s_resource(
  'argilla-server-deployment',
  port_forwards=['6900'],
  labels=['argilla-server'],
)