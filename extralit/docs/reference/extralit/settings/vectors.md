---
hide: footer
---
# Vectors

Vector fields in Extralit are used to define the vector form of a record that will be reviewed by a user.

## Usage Examples

To define a vector field, instantiate the `VectorField` class with a name and dimensions, then pass it to the `vectors` parameter of the `Settings` class.

```python
settings = ex.Settings(
    fields=[
        ex.TextField(name="text"),
    ],
    vectors=[
        ex.VectorField(
            name="my_vector",
            dimension=768,
            title="Document Embedding",
        ),
    ],
)
```

> To add records with vectors, refer to the [`ex.Vector`](../records/vectors.md) class documentation.

---

::: src.extralit.settings._vector.VectorField
