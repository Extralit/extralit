
# version_settings() enforces a minimum Tilt version
# https://docs.tilt.dev/api.html#api.version_settings
version_settings(constraint='>=0.23.4')

# Allow deployment on prod K8s context
allow_k8s_contexts(k8s_context())

# Read the ENV environment variable
ENV = str(local('echo $ENV')).strip()
DOCKER_REPO = str(local('echo $DOCKER_REPO')).strip()
if not DOCKER_REPO:
    DOCKER_REPO = 'localhost:5005'
    print('DOCKER_REPO not set, using default: {DOCKER_REPO}'.format(DOCKER_REPO=DOCKER_REPO))

# Check if ENV is set to 'dev' for local development
if 'kind' in k8s_context():
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
    deps=['./k8s/helm/elasticsearch-helm.yaml', 'elastic'],
    port_forwards=['9200'],
    labels=['elasticsearch']
)


# argilla-server is the web backend (FastAPI + SQL database)
docker_build(
    "{DOCKER_REPO}/itnrecal-argilla-server".format(DOCKER_REPO=DOCKER_REPO),
    context='.',
    build_args={'ENV': ENV},
    dockerfile='./docker/api.dockerfile',
    only=['./src', './dist', './docker/scripts', './setup.py', './pyproject.toml', './requirements.txt'],
    ignore=['./frontend', '**/__pycache__'],
    live_update=[
        # Sync the source code to the container
        sync('./src/', '/home/argilla/src/'),
        sync('./docker/scripts/start_argilla_server.sh', '/home/argilla/'),
        # Restart the server to pick up code changes
        run('/bin/bash start_argilla_server.sh', trigger='./docker/scripts/start_argilla_server.sh'),
        run('python -m argilla server database migrate', trigger='./src/argilla/server/alembic/versions')
    ]
)
argilla_server_k8s_yaml = read_yaml_stream('./k8s/argilla-server-deployment.yaml')
for o in argilla_server_k8s_yaml:
    for container in o['spec']['template']['spec']['containers']:
        if container['name'] == 'argilla-server':
            container['image'] = "{DOCKER_REPO}/itnrecal-argilla-server".format(DOCKER_REPO=DOCKER_REPO)

k8s_yaml([
    encode_yaml_stream(argilla_server_k8s_yaml), 
    './k8s/argilla-server-service.yaml', 
    './k8s/argilla-server-ingress.yaml'
    ])
k8s_resource(
  'argilla-server-deployment',
  resource_deps=['main-db', 'elasticsearch'],
  port_forwards=['6900'],
  labels=['argilla-server'],
)

# PostgreSQL is the database for argilla-server
helm_resource(
    name='main-db', 
    chart='bitnami/postgresql', 
    flags=[
        '--version=13.2.0',
        '--values=./k8s/helm/postgres-helm.yaml'],
    deps=['./k8s/helm/postgres-helm.yaml'],
    port_forwards=['5432'],
    labels=['argilla-server']
)

# argilla-frontend is the web interface (Vue.js + Nuxt)
docker_build(
    '{DOCKER_REPO}/itnrecal-argilla-frontend'.format(DOCKER_REPO=DOCKER_REPO),
    context='.',
    build_args={'ENV': ENV},
    dockerfile='./docker/web.dockerfile',
    only=['./frontend/', './scripts/', './docs/'],
    ignore=['./frontend/.nuxt/', './frontend/node_modules/', './frontend/package-lock.json', '**/__pycache__'],
    live_update=[
        fall_back_on('./frontend/nuxt.config.ts'),
        # Sync the frontend directory to the container
        sync('./frontend/', '/home/argilla/frontend/'),
        sync('./docs/', '/home/argilla/docs/'),
        run('npm install', trigger=['./frontend/package.json'])
    ]
)

argilla_frontend_k8s_yaml = read_yaml_stream('./k8s/argilla-frontend-deployment.yaml')
for o in argilla_frontend_k8s_yaml:
    for container in o['spec']['template']['spec']['containers']:
        if container['name'] == 'argilla-frontend':
            container['image'] = "{DOCKER_REPO}/itnrecal-argilla-frontend".format(DOCKER_REPO=DOCKER_REPO)

k8s_yaml(
    encode_yaml_stream(argilla_frontend_k8s_yaml)
    )
k8s_resource(
  'argilla-frontend-deployment',
  resource_deps=['argilla-server-deployment'],
  port_forwards='3000:3000',
  labels=['argilla-frontend'],
)


