
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
    deps=['./k8s/helm/elasticsearch-helm.yaml', 'elastic'],
    port_forwards=['9200'],
    labels=['elasticsearch']
)


# argilla-server is the web backend (FastAPI + SQL database)
docker_build(
    'itnrecal-argilla-server',
    context='.',
    build_args={'ENV': ENV},
    dockerfile='./docker/api.dockerfile',
    only=['./src/argilla/', './docker/', './dist/', './src/argilla/server/alembic/versions/'],
    live_update=[
        # Sync the source code to the container
        fall_back_on('./src/argilla/server/'),
        sync('./src/', '/home/argilla/src/'),
        sync('./src/argilla/server/alembic/versions/', '/home/argilla/src/argilla/server/alembic/versions/'),
        sync('./docker/scripts/start_argilla_server.sh', '/home/argilla/'),
        # Restart the server to pick up code changes
        run('/bin/bash start_argilla_server.sh', trigger='./docker/scripts/start_argilla_server.sh')
    ]
)

k8s_yaml(['./k8s/argilla-server-deployment.yaml', './k8s/argilla-server-service.yaml', './k8s/argilla-server-ingress.yaml'])
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
    'itnrecal-argilla-frontend',
    context='.',
    build_args={'ENV': ENV},
    dockerfile='./docker/web.dockerfile',
    only=['./frontend/', './scripts/', './docs/'],
    ignore=['./frontend/.nuxt/', './frontend/node_modules/', './frontend/package-lock.json'],
    live_update=[
        fall_back_on('./frontend/nuxt.config.ts'),
        # Sync the frontend directory to the container
        sync('./frontend/', '/home/argilla/frontend/'),
        sync('./docs/', '/home/argilla/docs/'),
        run('npm install', trigger=['./frontend/package.json'])
    ]
)

k8s_yaml('./k8s/argilla-frontend-deployment.yaml')
k8s_resource(
  'argilla-frontend-deployment',
  resource_deps=['argilla-server-deployment'],
  port_forwards='3000:3000',
  labels=['argilla-frontend'],
)


