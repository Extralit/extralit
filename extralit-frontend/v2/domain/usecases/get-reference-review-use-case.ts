import { Question } from "../entities/question/Question";
import { SchemaVersion } from "../entities/schema/SchemaVersion";
import {
  type ContextField,
  type OrphanedValue,
  type Provenance,
  ReferenceReview,
  ReviewCell,
  ReviewRecord,
} from "../entities/review/ReferenceReview";
import { SchemaRepository } from "~/v2/infrastructure/repositories/SchemaRepository";
import { V2RecordRepository } from "~/v2/infrastructure/repositories/V2RecordRepository";
import { ProjectionRepository, type ProjectionRecordDto } from "~/v2/infrastructure/repositories/ProjectionRepository";
import { AnnotationRepository, type RecordSuggestion } from "~/v2/infrastructure/repositories/AnnotationRepository";
import { type useReferenceReviews } from "~/v2/infrastructure/storage/ReferenceReviewsStorage";

interface SchemaContext {
  schemaName: string;
  questions: Question[];
  questionsById: Map<string, Question>;
  questionsByName: Map<string, Question>;
  versionsById: Map<string, SchemaVersion>;
}

export class GetReferenceReviewUseCase {
  constructor(
    private readonly projectionRepository: ProjectionRepository,
    private readonly schemaRepository: SchemaRepository,
    private readonly recordRepository: V2RecordRepository,
    private readonly annotationRepository: AnnotationRepository,
    private readonly reviewsStorage: typeof useReferenceReviews
  ) {}

  async execute(reference: string, workspaceId: string): Promise<ReferenceReview> {
    const projection = await this.projectionRepository.getProjection(reference, workspaceId);

    const schemaIds = [...new Set(projection.records.map((r) => r.schemaId))];
    const contexts = new Map<string, SchemaContext>();
    const recordsBySchema = new Map<string, Map<string, Record<string, unknown>>>();
    const versionByRecord = new Map<string, string>();

    await Promise.all(
      schemaIds.map(async (schemaId) => {
        const [schema, questions, versions, page] = await Promise.all([
          this.schemaRepository.getSchema(schemaId),
          this.schemaRepository.getQuestions(schemaId),
          this.schemaRepository.getVersions(schemaId),
          this.recordRepository.getRecords(schemaId, { reference }),
        ]);
        contexts.set(schemaId, {
          schemaName: schema.name,
          questions,
          // The name↔id join: projection cells + response values key by NAME,
          // suggestions key by ID (spec §7). Getting this wrong detaches provenance.
          questionsById: new Map(questions.map((q) => [q.id, q])),
          questionsByName: new Map(questions.map((q) => [q.name, q])),
          versionsById: new Map(versions.map((v) => [v.id, v])),
        });
        recordsBySchema.set(schemaId, new Map(page.items.map((r) => [r.id, r.fields])));
        page.items.forEach((r) => versionByRecord.set(r.id, r.schemaVersionId));
      })
    );

    const reviewRecords = await Promise.all(
      projection.records.map((projected) => this.assembleRecord(projected, contexts, recordsBySchema, versionByRecord))
    );

    const review = new ReferenceReview(reference, reviewRecords, projection.totalRecords);
    this.reviewsStorage().saveReview(review);
    return review;
  }

  private async assembleRecord(
    projected: ProjectionRecordDto,
    contexts: Map<string, SchemaContext>,
    recordsBySchema: Map<string, Map<string, Record<string, unknown>>>,
    versionByRecord: Map<string, string>
  ): Promise<ReviewRecord> {
    const context = contexts.get(projected.schemaId)!;
    const fields = recordsBySchema.get(projected.schemaId)?.get(projected.recordId) ?? {};
    const pinnedVersion = context.versionsById.get(versionByRecord.get(projected.recordId) ?? "");

    const [suggestions, response] = await Promise.all([
      this.annotationRepository.getSuggestions(projected.recordId),
      this.annotationRepository.getResponse(projected.recordId),
    ]);
    const suggestionsByQuestionId = new Map<string, RecordSuggestion>(suggestions.map((s) => [s.questionId, s]));
    const cellsByName = new Map(projected.cells.map((c) => [c.questionName, c]));

    const cells = context.questions.map((question) => {
      const cell = cellsByName.get(question.name);
      const suggestion = suggestionsByQuestionId.get(question.id);
      const provenance: Provenance | null = suggestion
        ? {
            agent: suggestion.agent,
            score: Array.isArray(suggestion.score) ? (suggestion.score[0] ?? null) : suggestion.score,
            suggestedValue: suggestion.value,
          }
        : null;
      // Old-version tolerance (§17.3): every bound column must exist in the pinned cache.
      const notApplicable =
        pinnedVersion !== undefined && question.columns.some((c) => pinnedVersion.findColumn(c) === undefined);

      return new ReviewCell(question, cell?.value ?? null, cell?.source ?? null, provenance, notApplicable);
    });

    const questionColumns = new Set(context.questions.flatMap((q) => q.columns));
    const contextFields: ContextField[] = (pinnedVersion?.columnsCache ?? [])
      .filter((column) => !questionColumns.has(column.name))
      .map((column) => ({ column, value: fields[column.name] ?? null }));

    const orphanedValues: OrphanedValue[] = Object.entries(response?.values ?? {})
      .filter(([name]) => !context.questionsByName.has(name))
      .map(([name, value]) => ({ name, value }));

    const draft = response?.status === "draft" ? response : null;

    return new ReviewRecord(
      projected.recordId,
      projected.schemaId,
      context.schemaName,
      cells,
      contextFields,
      orphanedValues,
      draft,
      pinnedVersion?.columnsCache ?? []
    );
  }
}
