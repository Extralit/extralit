## Description

This is a basic webhook example to show how to configure webhook listeners using the argilla SDK

The application defines three webhook listeners for the following events:

- Record events: `record.deleted`, `record.completed`
- Dataset events: `dataset.created`, `dataset.updated`, `dataset.published`, `dataset.deleted`
- Response events: `response.created`, `response.updated`

You can visit the [Extralit documentation](https://docs.extralit.ai/dev/admin_guide/webhooks) for more information.

## Running the app

First, you must start the extralit server. We recommend you to use the docker installation. You can run the following commands to start the extralit server:
```bash
mkdir extralit && cd extralit
curl https://raw.githubusercontent.com/extralit/extralit/main/docker-compose.yaml -o docker-compose.yaml
docker compose up -d
```

For more information on how to install the server, please refer to the [Extralit documentation](https://docs.extralit.ai/latest/getting_started).

Once the extralit server is up and running, start the webhook server by running the following command:

```bash
EXTRALIT_API_KEY=extralit.apikey \
WEBHOOK_SERVER_URL=http://host.docker.internal:8000 \
uvicorn main:server
```

The `EXTRALIT_API_KEY` environment variable should be set to the API key of the extralit server.
The `WEBHOOK_SERVER_URL` environment variable should be set to the URL where the webhook server is running.
In this case, we are using `http://host.docker.internal:8000` because the webhook calls will be done inside a docker container.

The application will remove all existing webhook listeners and create new ones for the events mentioned above.

## Testing the app

When you start working with the extralit server, you can see the logs in the webhook server.
You can test the webhook listeners by creating, updating, and deleting datasets, responses and records in the extralit server.
