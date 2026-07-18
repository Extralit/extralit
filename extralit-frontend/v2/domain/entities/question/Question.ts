// The server's QuestionType enum also includes "span", but span questions are rejected
// on write (spec §7) and are out of scope for the v2 review slice, so the domain type
// omits it. SchemaRepository.toQuestion casts the API value knowing "span" will never
// reach this entity in practice.
export type QuestionType = "text" | "rating" | "label_selection" | "multi_label_selection" | "ranking" | "table";

export interface QuestionOption {
  value: string;
  text: string;
  description: string | null;
}

export class Question {
  constructor(
    public readonly id: string,
    public readonly schemaId: string,
    public readonly name: string,
    public readonly title: string,
    public readonly description: string | null,
    public readonly type: QuestionType,
    public readonly columns: string[],
    public readonly settings: Record<string, unknown>,
    public readonly required: boolean
  ) {}

  get isLabelType(): boolean {
    return this.type === "label_selection" || this.type === "multi_label_selection";
  }

  // label_selection / multi_label_selection / ranking settings.options: {value, text, description}
  get options(): QuestionOption[] {
    const options = (this.settings.options as QuestionOption[] | undefined) ?? [];
    return options.map((o) => ({ value: o.value, text: o.text, description: o.description ?? null }));
  }

  // rating settings.options: {value: int}
  get ratingValues(): number[] {
    const options = (this.settings.options as { value: number }[] | undefined) ?? [];
    return options.map((o) => o.value);
  }
}
