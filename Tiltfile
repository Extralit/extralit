# version_settings() enforces a minimum Tilt version
# https://docs.tilt.dev/api.html#api.version_settings
version_settings(constraint='>=0.23.4')

# Allow deployment on prod K8s context
allow_k8s_contexts(k8s_context())
print("Using context:", k8s_context())

# User-provided environment variables
ENV = str(local('echo $ENV')).strip() or 'dev'
USERS_DB = str(local('echo $USERS_DB')).strip()
DOCKER_REPO = str(local('echo $DOCKER_REPO')).strip() or 'localhost:5005'

ARGILLA_DATABASE_URL = str(local('echo $ARGILLA_DATABASE_URL')).strip()
if ARGILLA_DATABASE_URL:
    print("Using external database with ARGILLA_DATABASE_URL envvar, skipping `main-db` deployment")
S3_ENDPOINT = str(local('echo $S3_ENDPOINT')).strip()
S3_ACCESS_KEY = str(local('echo $S3_ACCESS_KEY')).strip()
S3_SECRET_KEY = str(local('echo $S3_SECRET_KEY')).strip()
if S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY:
    print("Using external S3 storage with S3_ENDPOINT envvar, skipping `minio` deployment")
OPENAI_API_KEY = str(local('echo $OPENAI_API_KEY')).strip()
if OPENAI_API_KEY:
    print("Using external OpenAI API key")
WCS_HTTP_URL = str(local('echo $WCS_HTTP_URL')).strip()
WCS_GRPC_URL = str(local('echo $WCS_GRPC_URL')).strip()
WCS_API_KEY = str(local('echo $WCS_API_KEY')).strip()
if WCS_HTTP_URL and WCS_API_KEY:
    print("Using external Weaviate Cloud Service with WCS_HTTP_URL envvar, skipping `weaviate` deployment")

# Set up policies for kind of k3d development
if 'kind' in k8s_context():
    # Storage policy
    k8s_yaml('examples/deployments/k8s/kind/tilt-local-dev-storage-policy.yaml')
if 'k3d' in k8s_context():
    k8s_yaml('examples/deployments/k8s/k3d/k3d-auto-purge-pods.yaml')

load('ext://helm_resource', 'helm_resource', 'helm_repo')

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

# PostgreSQL is the database for argilla-server
helm_repo('bitnami', 'https://charts.bitnami.com/bitnami', labels=['helm'], resource_name='bitnami-helm')
if not ARGILLA_DATABASE_URL:
    helm_resource(
        name='main-db', 
        chart='bitnami/postgresql', 
        flags=[
            '--version=13.2.0',
            '--values=examples/deployments/k8s/helm/postgres-helm.yaml'],
        port_forwards=['5432'],
        labels=['argilla-server'],
        resource_deps=['bitnami-helm'],
    )

# Add Redis deployment
helm_repo('bitnami-redis', 'https://charts.bitnami.com/bitnami', labels=['helm'], resource_name='redis-helm')
helm_resource(
    name='redis',
    chart='bitnami/redis',
    flags=[
        '--version=17.11.3',
        '--set=auth.enabled=false',
        '--set=architecture=standalone',
        '--set=master.persistence.size=1Gi'
    ],
    port_forwards=['6379'],
    labels=['argilla-server'],
    resource_deps=['redis-helm', 'bitnami-helm']
)

# argilla-server is the web backend (FastAPI + SQL database)
if not os.path.exists('argilla-frontend/dist'):
    local('npm install && npm run build', dir='argilla-frontend', quiet=True)
if not os.path.exists('argilla-server/src/argilla_server/static'):
    local('cp -r argilla-frontend/dist argilla-server/src/argilla_server/static', quiet=True)
if not os.path.exists('argilla-server/dist/'):
    local('pdm build', dir='argilla-server')
docker_build(
    "{DOCKER_REPO}/argilla-server".format(DOCKER_REPO=DOCKER_REPO),
    context='argilla-server/',
    build_args={'ENV': ENV, 'USERS_DB': USERS_DB},
    dockerfile='argilla-server/docker/server/dev.argilla_server.dockerfile',
    ignore=['examples/', 'argilla/', '.*', '**/__pycache__', '*.pyc', 'CHANGELOG.md'],
    live_update=[
        # Sync the source code to the container
        sync('argilla-server/src/', '/home/argilla/src/'),
        sync('argilla-server/docker/server/scripts/start_argilla_server.sh', '/home/argilla/'),
        sync('argilla-server/pyproject.toml', '/home/argilla/pyproject.toml'),
    ]
)
argilla_server_k8s_yaml = read_yaml_stream('examples/deployments/k8s/argilla-server-deployment.yaml')
for o in argilla_server_k8s_yaml:
    for container in o['spec']['template']['spec']['containers']:
        if container['name'] == 'argilla-server':
            container['image'] = "{DOCKER_REPO}/argilla-server".format(DOCKER_REPO=DOCKER_REPO)
            if ARGILLA_DATABASE_URL:
                container['env'].extend([
                    {'name': 'ARGILLA_DATABASE_URL', 'value': ARGILLA_DATABASE_URL},
                    {'name': 'POSTGRES_HOST', 'value': ""},
                    {'name': 'POSTGRES_PASSWORD', 'value': ""},
                ])
            if S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY:
                container['env'].extend([
                    {'name': 'ARGILLA_S3_ENDPOINT', 'value': S3_ENDPOINT},
                    {'name': 'ARGILLA_S3_ACCESS_KEY', 'value': S3_ACCESS_KEY},
                    {'name': 'ARGILLA_S3_SECRET_KEY', 'value': S3_SECRET_KEY}
                ])

k8s_yaml([
    encode_yaml_stream(argilla_server_k8s_yaml), 
    'examples/deployments/k8s/argilla-server-service.yaml', 
    'examples/deployments/k8s/argilla-server-ingress.yaml',
    # 'examples/deployments/k8s/argilla-loadbalancer-service.yaml'
    ])
k8s_resource(
    'argilla-server',
    port_forwards=['6900'],
    labels=['argilla-server'],
    resource_deps=['redis', 'main-db', 'elasticsearch'] if not ARGILLA_DATABASE_URL else ['redis', 'elasticsearch'],
)

# Langfuse Observability server
k8s_yaml('examples/deployments/k8s/langfuse-deployment.yaml')
k8s_resource(
    'langfuse-deployment',
    port_forwards=['4000'],
    labels=['extralit'],
    auto_init=False,
    resource_deps=['main-db'] if not ARGILLA_DATABASE_URL else [],
)

# MinIO S3 storage
if not S3_ENDPOINT or not S3_ACCESS_KEY or not S3_SECRET_KEY:
    k8s_yaml([
        'examples/deployments/k8s/minio-dev.yaml', 
        'examples/deployments/k8s/minio-standalone-pvc.yaml'])
    k8s_resource(
      'minio',
      port_forwards=['9000', '9090'],
      labels=['extralit'],
    )

# Weaviate vector database
helm_repo('weaviate', 'https://weaviate.github.io/weaviate-helm', labels=['helm'], resource_name='weaviate-helm')
helm_resource(
    name='weaviate-server', 
    chart='weaviate/weaviate', 
    flags=[
        '--version=16.8.8',
        '--values=examples/deployments/k8s/helm/weaviate-helm.yaml'],
    auto_init=False,
    port_forwards=['8080:8080', '50051:50051'],
    labels=['extralit'],
    resource_deps=['weaviate-helm'],
)

# Extralit server
if not os.path.exists('argilla/dist/'):
    local('pdm build', dir='argilla')
docker_build(
    "{DOCKER_REPO}/extralit-server".format(DOCKER_REPO=DOCKER_REPO),
    context='argilla/',
    dockerfile='argilla/docker/extralit.dockerfile',
    ignore=['.*', 'argilla-frontend/', 'argilla-server/', '**/__pycache__', '*.pyc'],
    live_update=[
        sync('argilla/', '/home/extralit/'),
    ]
)
extralit_k8s_yaml = read_yaml_stream('examples/deployments/k8s/extralit-deployment.yaml')
for o in extralit_k8s_yaml:
    if o['kind'] == 'Deployment' and o['metadata']['name'] == 'extralit-server':
        for container in o['spec']['template']['spec']['containers']:
            if container['name'] == 'extralit-server':
                container['image'] = "{DOCKER_REPO}/extralit-server".format(DOCKER_REPO=DOCKER_REPO)
                if S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY:
                    container['env'].extend([
                        {'name': 'S3_ENDPOINT', 'value': S3_ENDPOINT, 'valueFrom': None},
                        {'name': 'S3_ACCESS_KEY', 'value': S3_ACCESS_KEY, 'valueFrom': None},
                        {'name': 'S3_SECRET_KEY', 'value': S3_SECRET_KEY, 'valueFrom': None}
                    ])
                if OPENAI_API_KEY:
                    container['env'].extend([
                        {'name': 'OPENAI_API_KEY', 'value': OPENAI_API_KEY, 'valueFrom': None}
                    ])
                if WCS_HTTP_URL and WCS_API_KEY:
                    container['env'].extend([
                        {'name': 'WCS_HTTP_URL', 'value': WCS_HTTP_URL},
                        {'name': 'WCS_GRPC_URL', 'value': WCS_GRPC_URL or ""},
                        {'name': 'WCS_API_KEY', 'value': WCS_API_KEY}
                    ])

k8s_yaml([
    encode_yaml_stream(extralit_k8s_yaml), 
    'examples/deployments/k8s/extralit-configs.yaml'
])
k8s_resource(
    'extralit-server',
    port_forwards=['5555'],
    labels=['extralit'],
    resource_deps=['minio'] if not (S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY) else [],
)

