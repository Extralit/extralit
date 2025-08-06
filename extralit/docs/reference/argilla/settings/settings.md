---
hide: footer
---
# `ex.Settings`

`ex.Settings` is used to define the settings of an Extralit `Dataset`. The settings can be used to configure the
behavior of the dataset, such as the fields, questions, guidelines, metadata, and vectors. The `Settings` class is
passed to the `Dataset` class and used to create the dataset on the server. Once created, the settings of a dataset
cannot be changed.

## Usage Examples

### Creating a new dataset with settings

To create a new dataset with settings, instantiate the `Settings` class and pass it to the `Dataset` class.

```python
import extralit as ex

settings = ex.Settings(
    guidelines="Select the sentiment of the prompt.",
    fields=[ex.TextField(name="prompt", use_markdown=True)],
    questions=[ex.LabelQuestion(name="sentiment", labels=["positive", "negative"])],
)

dataset = ex.Dataset(name="sentiment_analysis", settings=settings)

# Create the dataset on the server
dataset.create()

```

To define the settings for fields, questions, metadata, vectors, or distribution, refer to the [`ex.TextField`](fields.md), [`ex.LabelQuestion`](questions.md), [`ex.TermsMetadataProperty`](metadata_property.md), and [`ex.VectorField`](vectors.md), [`ex.TaskDistribution`](task_distribution.md) class documentation.

### Adding or removing properties to settings

The settings object can be modified before create the dataset by adding, replacing or removing properties by using
the method `settings.add` and `settings.<>.remove`

```python
import extralit as ex

settings = ex.Settings(
    guidelines="Select the sentiment of the prompt.",
    fields=[ex.TextField(name="prompt", use_markdown=True)],
    questions=[ex.LabelQuestion(name="sentiment", labels=["positive", "negative"])],
)

# Adding a new property
settings.add(ex.TextField(name="response", use_markdown=True))

# Replace an existing property by other property type
settings.add(ex.TextQuestion(name="response", use_markdown=False))

# Remove an existing property
settings.questions.remove("response")

```

### Creating settings using built in templates

Extralit provides built-in templates for creating settings for common dataset types. To use a template, use the class methods of the `Settings` class. There are three built-in templates available for classification, ranking, and rating tasks. Template settings also include default guidelines and mappings.

#### Classification Task

You can define a classification task using the `ex.Settings.for_classification` class method. This will create a dataset with a text field and a label question. You can select field types using the `field_type` parameter with `image` or `text`.

```python
settings = ex.Settings.for_classification(labels=["positive", "negative"]) # (1)
```

This will return a `Settings` object with the following settings:

```python
settings = Settings(
    guidelines="Select a label for the document.",
    fields=[ex.TextField(field_type)(name="text")],
    questions=[LabelQuestion(name="label", labels=labels)],
    mapping={"input": "text", "output": "label", "document": "text"},
)
```

#### Ranking Task

You can define a ranking task using the `ex.Settings.for_ranking` class method. This will create a dataset with a text field and a ranking question.

```python
settings = ex.Settings.for_ranking()
```

This will return a `Settings` object with the following settings:

```python
settings = Settings(
    guidelines="Rank the responses.",
    fields=[
        ex.TextField(name="instruction"),
        ex.TextField(name="response1"),
        ex.TextField(name="response2"),
    ],
    questions=[RankingQuestion(name="ranking", values=["response1", "response2"])],
    mapping={
        "input": "instruction",
        "prompt": "instruction",
        "chosen": "response1",
        "rejected": "response2",
    },
)
```

#### Rating Task

You can define a rating task using the `ex.Settings.for_rating` class method. This will create a dataset with a text field and a rating question.

```python
settings = ex.Settings.for_rating()
```

This will return a `Settings` object with the following settings:

```python
settings = Settings(
    guidelines="Rate the response.",
    fields=[
        ex.TextField(name="instruction"),
        ex.TextField(name="response"),
    ],
    questions=[RatingQuestion(name="rating", values=[1, 2, 3, 4, 5])],
    mapping={
        "input": "instruction",
        "prompt": "instruction",
        "output": "response",
        "score": "rating",
    },
)
```

---

::: src.extralit.settings._resource.Settings
