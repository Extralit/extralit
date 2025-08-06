---
hide: footer
---

# Fields

Fields in Extralit define the content of a record that will be reviewed by a user.

## Usage Examples

To define a field, instantiate the different field classes and pass it to the `fields` parameter of the `Settings` class.

```python
text_field = ex.TextField(name="text")
markdown_field = ex.TextField(name="text", use_markdown=True)
image_field = ex.ImageField(name="image")
```

The `fields` parameter of the `Settings` class can accept a list of fields, like this:

```python
settings = ex.Settings(
    fields=[
        text_field,
        markdown_field,
        image_field,
    ],
    questions=[
        ex.TextQuestion(name="response"),
    ],
)

data = ex.Dataset(
    name="my_dataset",
    settings=settings,
)
```

> To add records with values for fields, refer to the [`ex.Dataset.records`](../records/records.md) documentation.

---

::: src.argilla.settings._field.TextField

::: src.argilla.settings._field.ImageField

::: src.argilla.settings._field.ChatField

::: src.argilla.settings._field.CustomField
