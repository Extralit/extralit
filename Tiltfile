
# version_settings() enforces a minimum Tilt version
# https://docs.tilt.dev/api.html#api.version_settings
version_settings(constraint='>=0.23.4')

# Allow deployment on prod K8s context
allow_k8s_contexts(k8s_context())
print("Using context:", k8s_context())


# Read the ENV environment variable
ENV = str(local('echo $ENV')).strip()
USERS_DB = str(local('echo $USERS_DB')).strip()
DOCKER_REPO = str(local('echo $DOCKER_REPO')).strip()
if not DOCKER_REPO:
    DOCKER_REPO = 'localhost:5005'
    print('DOCKER_REPO not set, using default: {DOCKER_REPO}'.format(DOCKER_REPO=DOCKER_REPO))


# Set up the same storage policy for kind as in prod
if 'kind' in k8s_context():
    # Storage policy
    k8s_yaml('./k8s/kind/tilt-local-dev-kind-storage-policy.yaml')


# Installing elastic/elasticsearch Helm
load('ext://helm_resource', 'helm_resource', 'helm_repo')
helm_repo('elastic', 'https://helm.elastic.co', labels=['helm'])
helm_resource(
    name='elasticsearch', 
    chart='elastic/elasticsearch', 
    flags=[
        '--version=8.5.1',
        '--values=./k8s/helm/elasticsearch-helm.yaml'],
    deps=['./k8s/helm/elasticsearch-helm.yaml', 'elastic'],
    port_forwards=['9200'],
    labels=['argilla-server']
)


# argilla-server is the web backend (FastAPI + SQL database)
docker_build(
    "{DOCKER_REPO}/extralit-argilla-server".format(DOCKER_REPO=DOCKER_REPO),
    context='.',
    build_args={'ENV': ENV, 'USERS_DB': USERS_DB},
    dockerfile='./docker/server/argilla_server.dockerfile',
    ignore=['k8s/', 'argilla/', '.venv/', '.*', 'src/extralit', 'docker/server/extralit.dockerfile'],
    live_update=[
        # Sync the source code to the container
        sync('./src/', '/home/argilla/src/'),
        sync('./docker/server/scripts/start_argilla_server.sh', '/home/argilla/'),
        sync('./pyproject.toml', '/home/argilla/pyproject.toml'),
        # Restart the server to pick up code changes
        run('/bin/bash start_argilla_server.sh', trigger='./docker/server/scripts/start_argilla_server.sh'),
    ]
)
argilla_server_k8s_yaml = read_yaml_stream('./k8s/argilla-server-deployment.yaml')
for o in argilla_server_k8s_yaml:
    for container in o['spec']['template']['spec']['containers']:
        if container['image'] == 'extralit-argilla-server':
            container['image'] = "{DOCKER_REPO}/extralit-argilla-server".format(DOCKER_REPO=DOCKER_REPO)

k8s_yaml([
    encode_yaml_stream(argilla_server_k8s_yaml), 
    './k8s/argilla-server-service.yaml', 
    './k8s/argilla-server-ingress.yaml'
    ])
k8s_resource(
    'argilla-server-deployment',
    resource_deps=['main-db', 'elasticsearch'],
    port_forwards=['6901:6900' if 'kind' in k8s_context() else '6900'],
    labels=['argilla-server'],
)
k8s_yaml(['./k8s/argilla-loadbalancer-service.yaml'])


# PostgreSQL is the database for argilla-server
helm_resource(
    name='main-db', 
    chart='bitnami/postgresql', 
    flags=[
        '--version=13.2.0',
        '--values=./k8s/helm/postgres-helm.yaml'],
    deps=['./k8s/helm/postgres-helm.yaml'],
    port_forwards=['5433:5432' if 'kind' in k8s_context() else '5432'],
    labels=['argilla-server']
)


# Langfuse Observability server
k8s_yaml('./k8s/langfuse-deployment.yaml')
k8s_resource(
    'langfuse-deployment',
    port_forwards=['4000'],
    labels=['extralit'],
)

# # Vector-Admin 
# k8s_yaml('./k8s/vector-admin-deployment.yaml')
# k8s_resource(
#     'vector-admin-deployment',
#     port_forwards=['3001:3001'],
#     labels=['extralit'],
# )


# Aimstack Observability server
# docker_build(
#     "{DOCKER_REPO}/extralit-aim-server".format(DOCKER_REPO=DOCKER_REPO),
#     context='.',
#     dockerfile='./docker/services/aim.dockerfile',
#     only=['./docker/services/'],
# )
# aim_server_k8s_yaml = read_yaml_stream('./k8s/aim-server-deployment.yaml')
# for o in aim_server_k8s_yaml:
#     for container in o['spec']['template']['spec']['containers']:
#         print(container['name'])
#         if container['name'] == 'aim-server':
#             container['image'] = "{DOCKER_REPO}/extralit-aim-server".format(DOCKER_REPO=DOCKER_REPO)
# k8s_yaml([
#     encode_yaml_stream(aim_server_k8s_yaml), 
#     './k8s/aim-server-service.yaml', 
#     ])
# k8s_resource(
#   'aim-deployment',
#   port_forwards=['53800:43800'],
#   labels=['aim-observability'],
# )


# Add the MinIO Helm repository
# helm_repo('minio', 'https://operator.min.io/', labels=['helm'])
# Deploy the MinIO operator
# k8s_yaml('./k8s/minio-tenant.yaml')
# helm_resource(
#     name='extralit-minio-operator', 
#     chart='minio/minio-operator', 
#     flags=[
#         '--version=4.3.7',
#         '--values=./k8s/helm/minio-operator-helm.yaml'],
#     deps=['./k8s/helm/minio-operator-helm.yaml'],
#     port_forwards=['9090', '9443'],
#     labels=['minio']
# )

# Add the MinIO deployment
k8s_yaml(['./k8s/minio-dev.yaml', './k8s/minio-standalone-pvc.yaml'])
k8s_resource(
  'minio',
  port_forwards=['9000', '9090'],
  labels=['storage'],
)


# Weaviate vector database
helm_repo('weaviate-helm', 'https://weaviate.github.io/weaviate-helm', labels=['helm'])
helm_resource(
    name='weaviate', 
    chart='weaviate/weaviate', 
    flags=[
        '--version=16.8.8',
        '--values=./k8s/helm/weaviate-helm.yaml'],
    deps=['./k8s/helm/weaviate-helm.yaml'],
    port_forwards=['8080:8080', '50051:50051'],
    labels=['extralit']
)


# Extralit server
docker_build(
    "{DOCKER_REPO}/extralit-server".format(DOCKER_REPO=DOCKER_REPO),
    context='.',
    dockerfile='./docker/server/extralit.dockerfile',
    ignore=['k8s/', '.venv/', '.*', 'docker/', 'argilla/frontend/',
            'src/argilla_server/', '!src/argilla_server/_version.py'],
    live_update=[
        sync('./argilla/', '/home/extralit/argilla/'),
        sync('./src/', '/home/extralit/src/'),
        sync('./pyproject.toml', '/home/extralit/pyproject.toml'),
        run('uv pip install --upgrade -e ".[extraction,llm]"', trigger='./pyproject.toml'),
    ]
)
extralit_k8s_yaml = read_yaml_stream('./k8s/extralit-deployment.yaml')
for o in extralit_k8s_yaml:
    for container in o['spec']['template']['spec']['containers']:
        if container['name'] == 'extralit-server':
            container['image'] = "{DOCKER_REPO}/extralit-server".format(DOCKER_REPO=DOCKER_REPO)
k8s_yaml([
    encode_yaml_stream(extralit_k8s_yaml), 
    './k8s/extralit-storage-service.yaml'
    ])
k8s_resource(
    'extralit-server',
    resource_deps=['minio', 'weaviate'],
    port_forwards=['5555'],
    labels=['extralit'],
)


# Cert-manager for SSL certificates
# helm_repo('jetstack', 'https://charts.jetstack.io', labels=['helm'])
# helm_resource(
#     name='cert-manager', 
#     chart='jetstack/cert-manager', 
#     flags=[
#         '--version=1.7.1',
#         '--set=installCRDs=true'
#     ],
#     labels=['security']
# )
