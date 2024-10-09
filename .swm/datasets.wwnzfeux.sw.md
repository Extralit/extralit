---
hide: footer
title: datasets
---
# `rg.Dataset`

`Dataset` is a class that represents a collection of records. It is used to store and manage records in Argilla.

## Usage Examples

### Creating a Dataset

To create a new dataset you need to define its name and settings. Optional parameters are `workspace` and `client`, if you want to create the dataset in a specific workspace or on a specific Argilla instance.

```python
dataset = rg.Dataset(
    name="my_dataset",
    settings=rg.Settings(
        fields=[
            rg.TextField(name="text"),
        ],
        questions=[
            rg.TextQuestion(name="response"),
        ],
    ),
)
dataset.create()
```

For a detail guide of the dataset creation and publication process, see the <SwmLink doc-title="dataset" repo-id="Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA==" repo-name="extralit" path="/.swm/dataset.yyswcprd.sw.md">[dataset](https://app.swimm.io/repos/Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA%3D%3D/docs/yyswcprd)</SwmLink>.

### Retrieving an existing Dataset

To retrieve an existing dataset, use `client.datasets("my_dataset")` instead.

```python
dataset = client.datasets("my_dataset")
```

---

## `rg.Dataset`

<SwmMeta version="3.0.0"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
