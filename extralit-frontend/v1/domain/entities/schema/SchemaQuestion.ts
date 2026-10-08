// The schema-slice question entity, distinct from the annotation `Question`
// (`~/v1/domain/entities/question/Question.ts`) and its `QuestionType`, which is a
// `class QuestionType extends String` rather than a union. Both live under
// `v1/domain/entities/` since the v2 fold, so these carry the `Schema` prefix for the
// same reason `SchemaRecord` does — otherwise the two are reachable by absolute imports
// differing only by directory and an IDE auto-import offers either one.
//
// The server's QuestionType enum also includes "span", but span questions are rejected
// on write (spec §7) and are out of scope for the review slice, so the domain type
// omits it. SchemaRepository.toQuestion casts the API value knowing "span" will never
// reach this entity in practice.
export type SchemaQuestionType = "text" | "rating" | "label_selection" | "multi_label_selection" | "ranking" | "table";

export interface SchemaQuestionOption {
  value: string;
  text: string;
  description: string | null;
}

export class SchemaQuestion {
  constructor(
    public readonly id: string,
    public readonly schemaId: string,
    public readonly name: string,
    public readonly title: string,
    public readonly description: string | null,
    public readonly type: SchemaQuestionType,
    // Column bindings live at `settings.columns` server-side (text/table questions only,
    // never span) rather than on the top-level question — null for every other question type.
    public readonly columns: string[] | null,
    public readonly settings: Record<string, unknown>,
    public readonly required: boolean
  ) {}

  get isLabelType(): boolean {
    return this.type === "label_selection" || this.type === "multi_label_selection";
  }

  // label_selection / multi_label_selection / ranking settings.options: {value, text, description}
  get options(): SchemaQuestionOption[] {
    const options = (this.settings.options as SchemaQuestionOption[] | undefined) ?? [];
    return options.map((o) => ({ value: o.value, text: o.text, description: o.description ?? null }));
  }

  // rating settings.options: {value: int}
  get ratingValues(): number[] {
    const options = (this.settings.options as { value: number }[] | undefined) ?? [];
    return options.map((o) => o.value);
  }
}
