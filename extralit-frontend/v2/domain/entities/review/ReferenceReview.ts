import { Question } from "../question/Question";
import { type ColumnMeta } from "../schema/ColumnMeta";
import { type RecordResponse } from "~/v2/infrastructure/repositories/AnnotationRepository";

export interface Provenance {
  agent: string | null;
  score: number | null;
  suggestedValue: unknown;
}

export class ReviewCell {
  constructor(
    public readonly question: Question,
    public readonly value: unknown,
    public readonly source: "response" | "suggestion" | null,
    public readonly provenance: Provenance | null,
    // The question binds a column absent from this record's pinned version cache (§17.3).
    public readonly notApplicable: boolean
  ) {}
}

export interface ContextField {
  column: ColumnMeta;
  value: unknown;
}

// Response values keyed by a name no current question owns (deleted/recreated question,
// spec §10.1-E): surfaced read-only, never re-submitted (server would 422 them).
export interface OrphanedValue {
  name: string;
  value: unknown;
}

export class ReviewRecord {
  constructor(
    public readonly recordId: string,
    public readonly schemaId: string,
    public readonly schemaName: string,
    public readonly cells: ReviewCell[],
    public readonly contextFields: ContextField[],
    public readonly orphanedValues: OrphanedValue[],
    public readonly draft: RecordResponse | null, // status === "draft" only
    // Pinned version's columns_cache — table-question sub-columns derive editors from it.
    public readonly columnsCache: ColumnMeta[] = []
  ) {}

  initialValues(): Record<string, unknown> {
    const values: Record<string, unknown> = {};
    for (const cell of this.cells) {
      if (cell.notApplicable) continue;
      const draftValue = this.draft?.values[cell.question.name];
      const value = draftValue !== undefined ? draftValue : cell.value;
      if (value !== null && value !== undefined) values[cell.question.name] = value;
    }
    return values;
  }
}

export class ReferenceReview {
  constructor(
    public readonly reference: string,
    public readonly records: ReviewRecord[],
    public readonly totalRecords: number
  ) {}
}
