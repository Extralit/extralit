import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { GetReferenceReviewUseCase } from "./get-reference-review-use-case";
import { Question } from "../entities/question/Question";
import { Schema } from "../entities/schema/Schema";
import { SchemaVersion } from "../entities/schema/SchemaVersion";
import { ColumnMeta } from "../entities/schema/ColumnMeta";
import { V2Record } from "../entities/record/V2Record";
import { RecordsPage } from "../entities/record/RecordsPage";
import { useReferenceReviews } from "~/v2/infrastructure/storage/ReferenceReviewsStorage";

const REFERENCE = "10.1000/j.x";
const WORKSPACE = "w-1";

const sizeQuestion = new Question("q-size", "s-1", "size", "Sample size", null, "text", ["size"], {}, true);
const record = new V2Record(
  "r-1",
  "s-1",
  "v-1",
  REFERENCE,
  null,
  { size: "12", country: "KE" },
  null,
  "pending",
  "",
  ""
);

const projectionRepository = {
  getProjection: vi.fn(async () => ({
    reference: REFERENCE,
    totalRecords: 1,
    records: [
      {
        recordId: "r-1",
        schemaId: "s-1",
        reference: REFERENCE,
        cells: [{ questionName: "size", value: "12", source: "suggestion" as const }],
      },
    ],
  })),
};

const schemaRepository = {
  getSchema: vi.fn(async () => new Schema("s-1", "sample_size", "published", WORKSPACE, "v-1", {}, "", "")),
  getQuestions: vi.fn(async () => [sizeQuestion]),
  getVersions: vi.fn(async () => [
    new SchemaVersion(
      "v-1",
      "s-1",
      1,
      [new ColumnMeta("size", "str", false, null), new ColumnMeta("country", "str", true, null)],
      {},
      ""
    ),
  ]),
};

const recordRepository = { getRecords: vi.fn(async () => new RecordsPage([record], 1)) };

const annotationRepository = {
  getSuggestions: vi.fn(async () => [
    { id: "sug-1", recordId: "r-1", questionId: "q-size", value: "12", score: 0.9, agent: "gpt" },
  ]),
  getResponse: vi.fn(async () => null),
};

const makeUseCase = () =>
  new GetReferenceReviewUseCase(
    projectionRepository as never,
    schemaRepository as never,
    recordRepository as never,
    annotationRepository as never,
    useReferenceReviews
  );

describe("GetReferenceReviewUseCase", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("joins suggestion provenance to cells through the name↔id question map", async () => {
    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);

    const cell = review.records[0].cells.find((c) => c.question.name === "size")!;
    expect(cell.source).toBe("suggestion");
    expect(cell.provenance).toEqual({ agent: "gpt", score: 0.9, suggestedValue: "12" });
  });

  it("exposes non-question columns as read-only context fields", async () => {
    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);

    expect(review.records[0].contextFields).toEqual([
      { column: expect.objectContaining({ name: "country" }), value: "KE" },
    ]);
  });

  it("marks a question not-applicable when its column is missing from the pinned version cache", async () => {
    schemaRepository.getQuestions.mockResolvedValueOnce([
      sizeQuestion,
      new Question("q-new", "s-1", "added_later", "Added later", null, "text", ["added_later"], {}, false),
    ]);

    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);

    expect(review.records[0].cells.find((c) => c.question.name === "added_later")?.notApplicable).toBe(true);
  });

  it("collects response values orphaned by deleted questions and keeps a draft for prefill", async () => {
    annotationRepository.getResponse.mockResolvedValueOnce({
      id: "resp-1",
      recordId: "r-1",
      userId: "u-1",
      values: { size: "13", ghost_question: "zzz" },
      status: "draft",
    });

    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);
    const reviewRecord = review.records[0];

    expect(reviewRecord.orphanedValues).toEqual([{ name: "ghost_question", value: "zzz" }]);
    expect(reviewRecord.draft?.status).toBe("draft");
    // draft wins over the projection cell for prefill; orphans are excluded
    expect(reviewRecord.initialValues()).toEqual({ size: "13" });
  });

  it("prefills from the projection cell when there is no draft, and saves to storage by reference", async () => {
    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);

    expect(review.records[0].initialValues()).toEqual({ size: "12" });
    // The Pinia-backed store reconstructs+reactive-wraps on read (v1/store/non-reactive),
    // so assert deep equality, not object identity (matches SchemasStorage's test posture).
    expect(useReferenceReviews().findByReference(REFERENCE)).toEqual(review);
  });

  it("ignores a submitted response for prefill (projection already reflects it)", async () => {
    annotationRepository.getResponse.mockResolvedValueOnce({
      id: "resp-1",
      recordId: "r-1",
      userId: "u-1",
      values: { size: "12" },
      status: "submitted",
    });

    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);

    expect(review.records[0].draft).toBeNull();
  });
});
