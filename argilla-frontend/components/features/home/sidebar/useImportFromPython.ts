import { useUser } from "~/v1/infrastructure/services/useUser";
import { useRunningEnvironment } from "~/v1/infrastructure/services/useRunningEnvironment";
export const useImportFromPython = () => {
  const { isRunningOnHuggingFace } = useRunningEnvironment();
  const { getUser } = useUser();

  const user = getUser();

  const isRunningOnHF = isRunningOnHuggingFace();

  const snippet = `
# pip install extralit
# to run this code snippet

import argilla as rg

client = ex.Extralit(
    api_url="${window.location.origin}",
    api_key="${user.apiKey}",
)

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
            labels=["yes", "no"]
        ),
    ],
)

dataset = ex.Dataset(
    name="my_dataset",
    settings=settings,
)

dataset.create()

records = [
    {
        "text": "Do you need oxygen to breathe?",
        "label": "yes",
    }
]

dataset.records.log(records)
`;

  return { snippet, isRunningOnHF };
};
