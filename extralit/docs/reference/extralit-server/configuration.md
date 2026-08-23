# Server configuration

This section explains advanced operations and settings for running the Extralit Server and Extralit Python Client.

By default, the Extralit Server will look for your Elasticsearch (ES) endpoint at `http://localhost:9200`. You can customize this by setting the `EXTRALIT_ELASTICSEARCH` environment variable. Have a look at the list of available [environment variables](#environment-variables) to further configure the Extralit server.

From the Extralit version `1.19.0`, you must set up the search engine manually to work with datasets. You should set the
environment variable `EXTRALIT_SEARCH_ENGINE=opensearch` or `EXTRALIT_SEARCH_ENGINE=elasticsearch` depending on the backend you're using
The default value for this variable is set to `elasticsearch`. The minimal version for Elasticsearch is `8.5.0`, and for Opensearch is `2.4.0`.
Please, review your backend and upgrade it if necessary.

!!! warning
    For vector search in OpenSearch, the filtering applied is using a `post_filter` step, since there is a bug that makes queries fail using filtering + knn from Extralit.
    See https://github.com/opensearch-project/k-NN/issues/1286

    This may result in unexpected results when combining filtering with vector search with this engine.

## Launching

## Environment variables

You can set the following environment variables to further configure your server and client.

### Server

#### FastAPI

- `EXTRALIT_HOME_PATH`: The directory where Extralit will store all the files needed to run. If the path doesn't exist it will be automatically created (Default: `~/.extralit`).

- `EXTRALIT_BASE_URL`: If you want to launch the Extralit server in a specific base path other than /, you should set up this environment variable. This can be useful when running Extralit behind a proxy that adds a prefix path to route the service (Default: "/").

- `EXTRALIT_CORS_ORIGINS`: List of host patterns for CORS origin access.

- `EXTRALIT_DOCS_ENABLED`: If False, disables openapi docs endpoint at _/api/docs_.

- `EXTRALIT_ENABLE_SHARE_YOUR_PROGRESS`: If True, enables the share your progress feature. This feature allows users to share their progress with the community. If False, the feature will be disabled.

- `HF_HUB_DISABLE_TELEMETRY`: If True, disables telemetry for usage metrics. Alternatively, you can disable telemetry by setting `HF_HUB_OFFLINE=1`.

#### Authentication

- `USERNAME`: If provided, the owner username (Default: `None`).
- `PASSWORD`: If provided, the owner password (Default: `None`).
- `EXTRALIT_AUTH_SECRET_KEY`: The secret key used to sign the API token data. You can use `openssl rand -hex 32` to generate a 32 character string to use with this environment variable. By default a random value is generated, so if you are using more than one server worker (or more than one Extralit server) you will need to set the same value for all of them.
- `EXTRALIT_AUTH_OAUTH_CFG`: Path to the OAuth2 configuration file (Default: `$PWD/.oauth.yml`).

If `USERNAME` and `PASSWORD` are provided, the owner user will be created with these credentials on the server startup.

#### Database

- `EXTRALIT_DATABASE_URL`: A URL string that contains the necessary information to connect to a database. Extralit uses SQLite by default, PostgreSQL is also officially supported (Default: `sqlite:///$EXTRALIT_HOME_PATH/extralit.db?check_same_thread=False`).

##### SQLite

The following environment variables are useful only when SQLite is used:

- `EXTRALIT_DATABASE_SQLITE_TIMEOUT`: How many seconds the connection should wait before raising an `OperationalError` when a table is locked. If another connection opens a transaction to modify a table, that table will be locked until the transaction is committed. (Defaut: `15` seconds).

##### PostgreSQL

The following environment variables are useful only when PostgreSQL is used:

- `EXTRALIT_DATABASE_POSTGRESQL_POOL_SIZE`: The number of connections to keep open inside the database connection pool (Default: `15`).

- `EXTRALIT_DATABASE_POSTGRESQL_MAX_OVERFLOW`: The number of connections that can be opened above and beyond `EXTRALIT_DATABASE_POSTGRESQL_POOL_SIZE` setting (Default: `10`).

#### Search engine

- `EXTRALIT_ELASTICSEARCH`: URL of the connection endpoint of the Elasticsearch instance (Default: `http://localhost:9200`).

- `EXTRALIT_SEARCH_ENGINE`: Search engine to use. Valid values are "elasticsearch" and "opensearch" (Default: "elasticsearch").

- `EXTRALIT_ELASTICSEARCH_SSL_VERIFY`: If "False", disables SSL certificate verification when connecting to the Elasticsearch backend.

- `EXTRALIT_ELASTICSEARCH_CA_PATH`: Path to CA cert for ES host. For example: `/full/path/to/root-ca.pem` (Optional)

- `EXTRALIT_ES_RECORDS_INDEX_SHARDS`: Default number of elasticsearch/opensearch shards for each search index. (Default: `1`).

- `EXTRALIT_ES_RECORDS_INDEX_REPLICAS`: Default number of elasticsearch/opensearch replicas for each search index. (Default: `0`).

### Object storage

- `EXTRALIT_STORAGE_URL`: Root of object storage. Every workspace is a directory under it, holding its `pdf/`, `thumbnails/`, `layout/` and `schemas/` keys (Default: `file://$EXTRALIT_HOME_PATH/storage`). Accepted forms:
    - `file:///path/to/dir` — local disk.
    - `s3://bucket[/prefix]` — AWS S3.
    - `http(s)://host[:port]/bucket[/prefix]` — MinIO, Cloudflare R2 (`https://<ACCOUNT_ID>.r2.cloudflarestorage.com/bucket`) or any S3-compatible endpoint, addressed path-style.

    The bucket must already exist; the server never creates or deletes buckets. Use `https` in production: plain `http` sends your objects and their signatures in the clear, and is only appropriate on an isolated development host or a trusted internal network. Credentials belong in `EXTRALIT_S3_ACCESS_KEY`/`_SECRET_KEY`, never in the URL — a URL carrying them is rejected at startup.

- `EXTRALIT_S3_ACCESS_KEY`, `EXTRALIT_S3_SECRET_KEY`: Static credentials, set together or not at all. When unset, credentials are resolved from the environment the way the AWS SDKs do: `AWS_*` variables, EC2 instance profile (IMDSv2), ECS task role, or EKS IRSA web identity. That is the recommended setup on AWS; `~/.aws/config` profiles and `credential_process` are not read.
- `EXTRALIT_S3_REGION`: Region for request signing (Default: `us-east-1`; use `auto` for R2).

!!! note "Migrating from bucket-per-workspace"
    Servers before this setting created one bucket per workspace. Copy each into the new root before switching, e.g. `mc mirror minio/<workspace> minio/<bucket>/<prefix>/<workspace>`; the object keys are unchanged.

    **Local storage moved too.** It used to sit directly under `$EXTRALIT_HOME_PATH/<workspace>/`, alongside `extralit.db` and `lance/`; the default root is now the `storage/` subdirectory. Move each workspace into it — `mkdir -p $EXTRALIT_HOME_PATH/storage && mv $EXTRALIT_HOME_PATH/<workspace> $EXTRALIT_HOME_PATH/storage/` — or keep the old layout by setting `EXTRALIT_STORAGE_URL=file://$EXTRALIT_HOME_PATH`. Nothing is deleted if you skip this, but the server will not find the existing files.

### Redis

Redis is used by Extralit to store information about jobs to be processed on background. The following environment variables are useful to config how Extralit connects to Redis:

- `EXTRALIT_REDIS_URL`: A URL string that contains the necessary information to connect to a Redis instance (Default: `redis://localhost:6379/0`).
- `EXTRALIT_REDIS_USE_CLUSTER`: If "True" tries the connection with the URL to a  Redis Cluster instead of a Redis Standalone instance.

### Datasets

- `EXTRALIT_LABEL_SELECTION_OPTIONS_MAX_ITEMS`: Set the number of maximum items to be allowed by label and multi label questions (Default: `500`).

- `EXTRALIT_SPAN_OPTIONS_MAX_ITEMS`: Set the number of maximum items to be allowed by span questions (Default: `500`).

- `EXTRALIT_MIN_MESSAGE_LENGTH`: Set the minimum length of the message to be allowed in chat questions (Default: `1`).

- `EXTRALIT_MAX_MESSAGE_LENGTH`: Set the maximum length of the message to be allowed in chat questions (Default: `20000`).

- `EXTRALIT_MIN_ROLE_LENGTH`: Set the minimum length of the role to be allowed in chat questions (Default: `1`).

- `EXTRALIT_MAX_ROLE_LENGTH`: Set the maximum length of the role to be allowed in chat questions (Default: `20`).

### Hugging Face

- `EXTRALIT_SHOW_HUGGINGFACE_SPACE_PERSISTENT_STORAGE_WARNING`: When Extralit is running on Hugging Face Spaces you can use this environment variable to disable the warning message showed when persistent storage is disabled for the space (Default: `true`).

### Docker images only

- `REINDEX_DATASETS`: If `true` or `1`, the datasets will be reindexed in the search engine. This is needed when some search configuration changed or data must be refreshed (Default: `0`).

- `USERNAME`: If provided, the owner username. This can be combined with HF OAuth to define the extralit server owner (Default: `""`).

- `PASSWORD`: If provided, the owner password. If `USERNAME` and `PASSWORD` are provided, the owner user will be created with these credentials on the server startup (Default: `""`).

- `WORKSPACE`: If provided, the workspace name. If `USERNAME`, `PASSWORD` and `WORSPACE` are provided, a default workspace will be created with this name (Default: `""`).

- `API_KEY`: The default user api key to user. If API_KEY is not provided, a new random api key will be generated (Default: `""`).

- `UVICORN_APP`: [Advanced] The name of the FastAPI app to run. This is useful when you want to extend the FastAPI app with additional routes or middleware. The default value is `extralit_server:app`.

## REST API docs

FastAPI also provides beautiful REST API docs that you can check at [http://localhost:6900/api/v1/docs](http://localhost:6900/api/v1/docs).
