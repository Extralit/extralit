---
hide: footer
title: workspaces
---
# `rg.Workspace`

In Argilla, workspaces are used to organize datasets in to groups. For example, you might have a workspace for each project or team.

## Usage Examples

To create a new workspace, instantiate the `Workspace` object with the client and the name:

```python
workspace = rg.Workspace(name="my_workspace")
workspace.create()
```

To retrieve an existing workspace, use the `client.workspaces` attribute:

```python
workspace = client.workspaces("my_workspace")
```

---

## `rg.Workspace`

<SwmMeta version="3.0.0"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
