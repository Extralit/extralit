---
hide: footer
---

# Questions

Extralit uses questions to gather the feedback. The questions will be answered by users or models.

## Usage Examples

To define a label question, for example, instantiate the `LabelQuestion` class and pass it to the `Settings` class.

```python
label_question = ex.LabelQuestion(name="label", labels=["positive", "negative"])

settings = ex.Settings(
    fields=[
        ex.TextField(name="text"),
    ],
    questions=[
        label_question,
    ],
)
```

Questions can be combined in extensible ways based on the type of feedback you want to collect. For example, you can combine a label question with a text question to collect both a label and a text response.

```python
label_question = ex.LabelQuestion(name="label", labels=["positive", "negative"])
text_question = ex.TextQuestion(name="response")

settings = ex.Settings(
    fields=[
        ex.TextField(name="text"),
    ],
    questions=[
        label_question,
        text_question,
    ],
)

dataset = ex.Dataset(
    name="my_dataset",
    settings=settings,
)
```

> To add records with responses to questions, refer to the [`ex.Response`](../records/responses.md) class documentation.

---

::: src.extralit.settings._question.LabelQuestion

::: src.extralit.settings._question.MultiLabelQuestion

::: src.extralit.settings._question.RankingQuestion

::: src.extralit.settings._question.TextQuestion

::: src.extralit.settings._question.RatingQuestion

::: src.extralit.settings._question.SpanQuestion
