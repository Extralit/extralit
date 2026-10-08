// jest-mock-extended (used by @codescouts/test/jest) lazily calls jest.fn();
// alias the jest global to vitest's vi so the mock factory works under Vitest.
(globalThis as any).jest ??= vi;

import { mock } from "@codescouts/test/jest";
import { IQuestionRepository } from "../services/IQuestionRepository";
import { GetDatasetQuestionsGroupedUseCase } from "./get-dataset-questions-grouped-use-case";

const createBackendQuestion = (type: string) => {
  return {
    id: "1",
    name: "name",
    description: "description",
    title: "title",
    required: true,
    settings: {
      type,
      options: [
        {
          description: "description",
          text: "text",
          value: "value",
        },
      ],
    },
  };
};

describe("GetDatasetQuestionsGroupedUseCase should", () => {
  test("return a list of questions grouped by type", async () => {
    const datasetId = "datasetId";
    const backendQuestions = [
      createBackendQuestion("label_selection"),
      createBackendQuestion("label_selection"),
      createBackendQuestion("rating"),
    ];

    const questionRepository = mock<IQuestionRepository>();
    (questionRepository.getQuestions as any).mockResolvedValue(backendQuestions);

    const getDatasetQuestionsGroupedUseCase = new GetDatasetQuestionsGroupedUseCase(questionRepository);

    const result = await getDatasetQuestionsGroupedUseCase.execute(datasetId);

    expect(result).toHaveLength(2);
  });

  test("return an empty list if there are no questions", async () => {
    const datasetId = "datasetId";
    const backendQuestions = [];

    const questionRepository = mock<IQuestionRepository>();
    (questionRepository.getQuestions as any).mockResolvedValue(backendQuestions);

    const getDatasetQuestionsGroupedUseCase = new GetDatasetQuestionsGroupedUseCase(questionRepository);

    const result = await getDatasetQuestionsGroupedUseCase.execute(datasetId);

    expect(result).toHaveLength(0);
  });
});
