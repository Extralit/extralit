
# version_settings() enforces a minimum Tilt version
# https://docs.tilt.dev/api.html#api.version_settings
version_settings(constraint='>=0.23.4')

# Allow deployment on prod K8s context
allow_k8s_contexts(k8s_context())
print("Using context:", k8s_context())

# Read the ENV environment variable
ENV = str(local('echo $ENV')).strip() or 'dev'
USERS_DB = str(local('echo $USERS_DB')).strip()
DOCKER_REPO = str(local('echo $DOCKER_REPO')).strip() or 'localhost:5005'

# Set up the same storage policy for kind as in prod
if 'kind' in k8s_context():
    # Storage policy
    k8s_yaml('examples/deployments/k8s/kind/tilt-local-dev-storage-policy.yaml')
if 'k3d' in k8s_context():
    k8s_yaml('examples/deployments/k8s/k3d/k3d-config.yaml')

load('ext://helm_resource', 'helm_resource', 'helm_repo')

# Installing elastic/elasticsearch Helm
# helm_repo('elastic', 'https://helm.elastic.co', labels=['helm'], resource_name='elastic-helm')
# helm_resource(
#     name='elasticsearch', 
#     chart='elastic/elasticsearch', 
#     flags=[
#         '--version=8.5.1',
#         '--values=./examples/deployments/k8s/helm/elasticsearch-helm.yaml'],
#     deps=['elastic-helm'],
#     port_forwards=['9200'],
#     labels=['argilla-server']
# )

# Elasticsearch deployment using k8s_yaml
k8s_yaml([
    'examples/deployments/k8s/elasticsearch-deployment.yaml',
    'examples/deployments/k8s/elasticsearch-pvc.yaml',
    'examples/deployments/k8s/elasticsearch-service.yaml'
    ])
k8s_resource(
    'elasticsearch',
    port_forwards=['9200'],
    labels=['argilla-server'],
)

# argilla-server is the web backend (FastAPI + SQL database)
if not os.path.exists('argilla-frontend/dist'):
    local('npm install && npm run build', dir='argilla-frontend')
if not os.path.exists('argilla-server/src/argilla_server/static'):
    local('cp -r argilla-frontend/dist argilla-server/src/argilla_server/static')
if not os.path.exists('argilla-server/dist/'):
    local('pdm build', dir='argilla-server')
docker_build(
    "{DOCKER_REPO}/argilla-server".format(DOCKER_REPO=DOCKER_REPO),
    context='argilla-server/',
    build_args={'ENV': ENV, 'USERS_DB': USERS_DB},
    dockerfile='argilla-server/docker/server/argilla_server.dockerfile',
    ignore=['examples/', 'argilla/', '.*'],
    live_update=[
        # Sync the source code to the container
        sync('argilla-server/src/', '/home/argilla/src/'),
        sync('argilla-server/docker/server/scripts/start_argilla_server.sh', '/home/argilla/'),
        sync('argilla-server/pyproject.toml', '/home/argilla/pyproject.toml'),
        # Restart the server to pick up code changes
        run('/bin/bash start_argilla_server.sh', trigger='argilla-server/docker/server/scripts/start_argilla_server.sh'),
    ]
)
argilla_server_k8s_yaml = read_yaml_stream('examples/deployments/k8s/argilla-server-deployment.yaml')
for o in argilla_server_k8s_yaml:
    for container in o['spec']['template']['spec']['containers']:
        if container['name'] == 'argilla-server':
            container['image'] = "{DOCKER_REPO}/argilla-server".format(DOCKER_REPO=DOCKER_REPO)

k8s_yaml([
    encode_yaml_stream(argilla_server_k8s_yaml), 
    'examples/deployments/k8s/argilla-server-service.yaml', 
    'examples/deployments/k8s/argilla-server-ingress.yaml',
    # 'examples/deployments/k8s/argilla-loadbalancer-service.yaml'
    ])
k8s_resource(
    'argilla-server-deployment',
    resource_deps=['main-db', 'elasticsearch'],
    port_forwards=['6900'],
    labels=['argilla-server'],
)



# PostgreSQL is the database for argilla-server
helm_repo('bitnami', 'https://charts.bitnami.com/bitnami', labels=['helm'], resource_name='postgres-helm')
helm_resource(
    name='main-db', 
    chart='bitnami/postgresql', 
    flags=[
        '--version=13.2.0',
        '--values=examples/deployments/k8s/helm/postgres-helm.yaml'],
    deps=['postgres-helm'],
    port_forwards=['5432'],
    labels=['argilla-server']
)


# Langfuse Observability server
k8s_yaml('examples/deployments/k8s/langfuse-deployment.yaml')
k8s_resource(
    'langfuse-deployment',
    resource_deps=['main-db'],
    port_forwards=['4000'],
    labels=['extralit'],
    auto_init=False,
)

# MinIO S3 storage
k8s_yaml([
    'examples/deployments/k8s/minio-dev.yaml', 
    'examples/deployments/k8s/minio-standalone-pvc.yaml'])
k8s_resource(
  'minio',
  port_forwards=['9000', '9090'],
  labels=['storage'],
)

# Weaviate vector database
helm_repo('weaviate', 'https://weaviate.github.io/weaviate-helm', labels=['helm'], resource_name='weaviate-helm')
helm_resource(
    name='weaviate-server', 
    chart='weaviate/weaviate', 
    flags=[
        '--version=16.8.8',
        '--values=examples/deployments/k8s/helm/weaviate-helm.yaml'],
    deps=['weaviate-helm'],
    port_forwards=['8080:8080', '50051:50051'],
    labels=['extralit']
)

# Extralit server
if not os.path.exists('argilla/dist/'):
    local('pdm build', dir='argilla')
docker_build(
    "{DOCKER_REPO}/extralit-server".format(DOCKER_REPO=DOCKER_REPO),
    context='argilla/',
    dockerfile='argilla/docker/extralit.dockerfile',
    ignore=['.*', 'argilla-frontend/', 'argilla_server/'],
    live_update=[
        sync('./argilla/', '/home/extralit/argilla/'),
    ]
)
extralit_k8s_yaml = read_yaml_stream('examples/deployments/k8s/extralit-deployment.yaml')
for o in extralit_k8s_yaml:
    if o['kind'] == 'Deployment' and o['metadata']['name'] == 'extralit-server':
        for container in o['spec']['template']['spec']['containers']:
            if container['name'] == 'extralit-server':
                container['image'] = "{DOCKER_REPO}/extralit-server".format(DOCKER_REPO=DOCKER_REPO)
                
k8s_yaml([
    encode_yaml_stream(extralit_k8s_yaml), 
    'examples/deployments/k8s/extralit-configs.yaml'
    ])
k8s_resource(
    'extralit-server',
    resource_deps=['minio', 'weaviate-server'],
    port_forwards=['5555'],
    labels=['extralit'],
)

