---
hide: footer
---
# `ex.Dataset`

`Dataset` is a class that represents a collection of records. It is used to store and manage records in Extralit.

## Usage Examples

### Creating a Dataset

To create a new dataset you need to define its name and settings. Optional parameters are `workspace` and `client`, if you want to create the dataset in a specific workspace or on a specific Extralit instance.

```python
dataset = ex.Dataset(
    name="my_dataset",
    settings=ex.Settings(
        fields=[
            ex.TextField(name="text"),
        ],
        questions=[
            ex.TextQuestion(name="response"),
        ],
    ),
)
dataset.create()
```

For a detail guide of the dataset creation and publication process, see the [Dataset how to guide](../../../admin_guide/dataset.md).

### Retrieving an existing Dataset


To retrieve an existing dataset, use `client.datasets("my_dataset")` instead.

```python
dataset = client.datasets("my_dataset")
```

---

::: src.extralit.datasets._resource.Dataset

::: src.extralit.datasets._io._disk.DiskImportExportMixin

::: src.extralit.datasets._io._hub.HubImportExportMixin


