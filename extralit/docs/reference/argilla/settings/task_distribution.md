---
hide: footer
---
# Distribution

Distribution settings are used to define the criteria used by the tool to automatically manage records in the dataset depending on the expected number of submitted responses per record.

## Usage Examples

The default minimum submitted responses per record is 1. If you wish to increase this value, you can define it through the `TaskDistribution` class and pass it to the `Settings` class.

```python
settings = ex.Settings(
    guidelines="These are some guidelines.",
    fields=[
        ex.TextField(
            name="text",
        ),
    ],
    questions=[
        ex.LabelQuestion(
            name="label",
            labels=["label_1", "label_2", "label_3"]
        ),
    ],
    distribution=ex.TaskDistribution(min_submitted=3)
)

dataset = ex.Dataset(
    name="my_dataset",
    settings=settings
)
```

---

::: src.extralit.settings._task_distribution.OverlapTaskDistribution
