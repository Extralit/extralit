---
hide: footer
title: vectors
---
# Vectors

Vector fields in Argilla are used to define the vector form of a record that will be reviewed by a user.

## Usage Examples

To define a vector field, instantiate the `VectorField` class with a name and dimenstions, then pass it to the `vectors` parameter of the `Settings` class.

```python
settings = rg.Settings(
    fields=[
        rg.TextField(name="text"),
    ],
    vectors=[
        rg.VectorField(
            name="my_vector",
            dimension=768,
            title="Document Embedding",
        ),
    ],
)
```

> To add records with vectors, refer to the `rg.Vector` class documentation.

---

## `rg.VectorField`

<SwmMeta version="3.0.0"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
