---
description: In this section, we will provide a step-by-step guide to show how to manage workspaces.
---

# Workspace management

This guide provides an overview of workspaces, explaining how to set up and manage workspaces in Extralit.

A **workspace** is a *space* inside your Extralit instance where authorized users can collaborate on datasets. It is accessible through the Python SDK and the UI.

??? Question "Question: Who can manage workspaces?"

    Only users with the `owner` role can manage (create, read and delete) workspaces.

    A user with the `admin` role can only read the workspace to which it belongs.

## Initial workspaces

Depending on [your Extralit deployment](../getting_started/quickstart.md), the initial workspace will vary.

* If you deploy on the Hugging Face Hub, the initial workspace will be the one indicated in the `.oauth.yaml` file. By default, `extralit`.
* If you deploy with Docker, you will need to create a workspace as shown [in the next section](#create-a-new-workspace).

!!! info "Main Class"

    ```python
    ex.Workspace(
        name = "name",
        client=client
    )
    ```
    > Check the [Workspace - Python Reference](../reference/extralit/workspaces.md) to see the attributes, arguments, and methods of the `Workspace` class in detail.

## Create a new workspace

To create a new workspace in Extralit, you can define it in the `Workspace` class and then call the `create` method. This method is inherited from the `Resource` base class and operates without modifications.

> When you create a new workspace, it will be empty. To create and add a new dataset, check these [guides](dataset.md).

```python
import extralit as ex

client = ex.Extralit(api_url="<api_url>", api_key="<api_key>")

workspace_to_create = ex.Workspace(name="my_workspace")

created_workspace = workspace_to_create.create()
```
!!! tip "Accessing attributes"
    Access the attributes of a workspace by calling them directly on the `Workspace` object. For example, `workspace.id` or `workspace.name`.

## List workspaces

You can list all the existing workspaces in Extralit by calling the `workspaces` attribute on the `Extralit` class and iterating over them. You can also use `len(client.workspaces)` to get the number of workspaces.

```python
import extralit as ex

client = ex.Extralit(api_url="<api_url>", api_key="<api_key>")

workspaces = client.workspaces

for workspace in workspaces:
    print(workspace)
```
!!! tip "Notebooks"
    When using a notebook, executing `client.workspaces` will display a table with the number of `datasets` in each workspace, `name`, `id`, and the last update as `updated_at`.

## Retrieve a workspace

You can retrieve a workspace by accessing the `workspaces` method on the `Extralit` class and passing the `name` or `id` of the workspace as an argument. If the workspace does not exist, a warning message will be raised and `None` will be returned.

=== "By name"

    ```python
    import extralit as ex

    client = ex.Extralit(api_url="<api_url>", api_key="<api_key>")

    retrieved_workspace = client.workspaces("my_workspace")
    ```

=== "By id"

    ```python
    import extralit as ex

    client = ex.Extralit(api_url="<api_url>", api_key="<api_key>")

    retrieved_workspace = client.workspaces(id="<uuid-or-uuid-string>")
    ```

## Check workspace existence

You can check if a workspace exists. The `client.workspaces` method will return `None` if the workspace is not found.

```python
import extralit as ex

client = ex.Extralit(api_url="<api_url>", api_key="<api_key>")

workspace = client.workspaces("my_workspace")

if workspace is not None:
    pass
```

## List users in a workspace

You can list all the users in a workspace by accessing the `users` attribute on the `Workspace` class and iterating over them. You can also use `len(workspace.users)` to get the number of users by workspace.

> For further information on how to manage users, check this [how-to guide](user.md).

```python
import extralit as ex

client = ex.Extralit(api_url="<api_url>", api_key="<api_key>")

workspace = client.workspaces('my_workspace')

for user in workspace.users:
    print(user)
```

## Add a user to a workspace

You can also add a user to a workspace by calling the `add_user` method on the `Workspace` class.

> For further information on how to manage users, check this [how-to guide](user.md).

```python
import extralit as ex

client = ex.Extralit(api_url="<api_url>", api_key="<api_key>")

workspace = client.workspaces("my_workspace")

added_user = workspace.add_user("my_username")
```

## Remove a user from workspace

You can also remove a user from a workspace by calling the `remove_user` method on the `Workspace` class.

> For further information on how to manage users, check this [how-to guide](user.md).

```python
import extralit as ex

client = ex.Extralit(api_url="<api_url>", api_key="<api_key>")

workspace = client.workspaces("my_workspace")

removed_user = workspace.remove_user("my_username")
```

## Diagnose workspace health

You can run health diagnostics on a workspace to check for common issues like missing S3 buckets, connectivity problems, or configuration issues. The `doctor` method checks various aspects of the workspace setup and can automatically fix certain issues.

```python
import extralit as ex

client = ex.Extralit(api_url="<api_url>", api_key="<api_key>")

workspace = client.workspaces("my_workspace")

# Run diagnostics with automatic fixes
doctor_response = client.workspaces.doctor(workspace.id, autofix=True)

# View results
print(f"Overall status: {doctor_response.overall_status}")
for check in doctor_response.checks:
    print(f"{check.check_name}: {check.status} - {check.message}")
```

The doctor checks:
- **S3 bucket existence**: Creates the bucket if missing (when autofix=True)
- **Bucket versioning**: Verifies file versioning policy (informational)
- **RQ worker pool**: Tests background job queue connectivity (informational)
- **Elasticsearch indexes**: Checks dataset index availability (informational)

!!! tip "CLI Alternative"
    You can also run workspace diagnostics from the command line:
    ```bash
    extralit workspaces --name my_workspace doctor
    ```

## Delete a workspace

To delete a workspace, **no dataset can be associated with it**. If the workspace contains any dataset, deletion will fail. You can delete a workspace by calling the `delete` method on the `Workspace` class.

> To clear a workspace and delete all their datasets, refer to this [how-to guide](dataset.md).

```python
import extralit as ex

client = ex.Extralit(api_url="<api_url>", api_key="<api_key>")

workspace_to_delete = client.workspaces("my_workspace")

deleted_workspace = workspace_to_delete.delete()
```
