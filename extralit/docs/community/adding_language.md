# Adding a new language to Argilla

If you want to add a new language to Argilla you need to go to two places:

1. Add a new translation specification in the folder: `extralit-frontend/translation` E.g. for Korean with Code `ko` add a `ko.js` file by coping the `en.js` file. The text values need to be translated:
```javascript
export default {
    multi_label_selection: "다중 라벨",
    ranking: "순위",
    label_selection: "라벨",
    span: "범위",
    text: "텍스트",
    ...
```
2. Then update the i18n Nuxt: `extralit-frontend/nuxt.config.ts`

```javascript
  i18n: {
    locales: [
      {
        code: "en",
        file: "en.js",
      },
      ...
      {
        code: "ko",
        file: "ko.js",
      },
    ],
```

### How to test it

1. Start a local instance of Argilla, easiest by just using the docker recipe [here](../getting_started/how-to-deploy-argilla-with-docker.md). It will give you a backend API for the frontend.
2. Compile a new version of the frontend. Check [this guide](https://github.com/extralit/extralit/tree/develop/extralit-frontend). This is basically:
    - `git clone https://github.com/extralit/extralit`
    - `cd extralit-frontend`
    - Install the dependencies: `npm i`
    - Build the new frontend with the updates: `npm run build`
    - Serve the UI via `npm run start`. You can reach it under localhost:3000 by default.
    - Check the translations.
3. Deploy a small test dataset to test the translation on a dataset too:
```python
import argilla as rg

client_local = ex.Extralit(api_url="http://localhost:6900/", api_key="extralit.apikey")

sample_questions = [
    ex.SpanQuestion(
        name="question1",
        field="text",
        labels={
            "PERSON": "Person",
            "ORG": "Organization",
            "LOC": "Location",
            "MISC": "Miscellaneous"
        },  # or ["PERSON", "ORG", "LOC", "MISC"]
        title="Select the entities in the text",
        description="Select the entities in the text",
        required=True,
        allow_overlapping=False,
    ),
    ex.LabelQuestion(
        name="question2",
        labels={"YES": "Yes", "NO": "No"},  # or ["YES", "NO"]
        title="Is the answer relevant to the given prompt?",
        description="Choose the option that applies.",
        required=True,
    ),
    ex.MultiLabelQuestion(
        name="question3",
        labels={
            "hate": "Hate speech",
            "sexual": "Sexual content",
            "violent": "Violent content",
            "pii": "Personal information",
            "untruthful": "False information",
            "not_english": "Not English",
            "inappropriate": "Inappropriate content"
        },  # or ["hate", "sexual", "violent", "pii", "untruthful", "not_english", "inappropriate"]
        title="Does the response contain any of the following?",
        description="Select all applicable options.",
        required=True,
        visible_labels=3,
        labels_order="natural"
    ),
    ex.RankingQuestion(
        name="question4",
        values={
            "reply-1": "Answer 1",
            "reply-2": "Answer 2",
            "reply-3": "Answer 3"
        },  # or ["reply-1", "reply-2", "reply-3"]
        title="Rank the answers by your preference",
        description="1 = best, 3 = worst. Equal ratings are allowed.",
        required=True,
    ),
    ex.RatingQuestion(
        name="question5",
        values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        title="How satisfied are you with the answer?",
        description="1 = very dissatisfied, 10 = very satisfied",
        required=True,
    ),
    ex.TextQuestion(
        name="question6",
        title="Please provide your feedback on the answer",
        description="Please provide your feedback on the answer",
        required=True,
        use_markdown=True
    )
]

sample_fields = [
    ex.ChatField(
        name="chat",
        title="Previous conversation with the customer",
        use_markdown=True,
        required=True,
        description="Dialog between AI & customer up to the last question",
    ),
    ex.TextField(
        name="text",
        title="Customer's question",
        use_markdown=False,
        required=True,
        description="This is a question from the customer",
    ),
    ex.ImageField(
        name="image",
        title="Image related to the question",
        required=True,
        description="Image sent by the customer",
    ),
]

# Create a new dataset with the same settings as the original
settings = ex.Settings(
    fields=sample_fields,
    questions=sample_questions,
)
new_dataset = ex.Dataset(
    name="demo_dataset",
    workspace="default",
    settings=settings,
    client=client_local,
)
new_dataset.create()

def fix_record():
    return ex.Record(
        fields={
            "chat": [
                {"role": "user", "content": "What is Argilla?"},
                {"role": "assistant", "content": "Argilla is a collaboration tool for AI engineers and domain experts to build high-quality datasets"},
            ],
            "image": "https://images.unsplash.com/photo-1523567353-71ea31cb9f73?w=900&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTJ8fGNvcmdpfGVufDB8fDB8fHww",
            "text": "Which town has a greater population as of the 2010 census, Minden, Nevada or Gardnerville, Nevada?",
        },
    )

new_records = [fix_record() for _ in range(10)]
new_dataset.records.log(new_records)
```
4. Test if your translation also works with the dataset and in the dataset settings.
