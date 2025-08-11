---
hide: footer
---
# `ex.Extralit`

To interact with the Extralit server from Python you can use the `Extralit` class. The `Extralit` client is used to create, get, update, and delete all Extralit resources, such as workspaces, users, datasets, and records.

## Usage Examples

### Deploying Extralit Server on Hugging Face Spaces

To deploy Extralit on Hugging Face Spaces, use the `deploy_on_spaces` method.

```python
import extralit as ex

client = ex.Extralit.deploy_on_spaces(api_key="12345678")
```

### Connecting to an Extralit server

To connect to an Extralit server, instantiate the `Extralit` class and pass the `api_url` of the server and the `api_key` to authenticate.

```python
import extralit as ex

client = ex.Extralit(
    api_url="https://extralit-public-demo.hf.space",
    api_key="my_api_key",
)
```

### Accessing Dataset, Workspace, and User objects

The `Extralit` clients provides access to the `Dataset`, `Workspace`, and `User` objects of the Extralit server.

```python

my_dataset = client.datasets("my_dataset")

my_workspace = client.workspaces("my_workspace")

my_user = client.users("my_user")

```

These resources can then be interacted with to access their properties and methods. For example, to list all datasets in a workspace:

```python
for dataset in my_workspace.datasets:
    print(dataset.name)
```


---

::: src.extralit.client.core.Extralit
::: src.extralit.client.resources.Users
::: src.extralit.client.resources.Workspaces
::: src.extralit.client.resources.Datasets

::: src.extralit._helpers._deploy.SpacesDeploymentMixin
