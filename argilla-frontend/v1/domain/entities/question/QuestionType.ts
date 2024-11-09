export class QuestionType extends String {
  private constructor(value: string) {
    super(value);
  }

  public get value(): string {
    return this.toLowerCase();
  }

  public static from(value: string): QuestionType {
    return new QuestionType(value);
  }

  public get isRankingType(): boolean {
    return this.value === "ranking";
  }

  public get isMultiLabelType(): boolean {
    return this.type === "multi_label_selection" || this.type === "dynamic_multi_label_selection";
  }

  public get isSingleLabelType(): boolean {
    return this.type === "label_selection" || this.type === "dynamic_label_selection";
  }

  public get isTextType(): boolean {
    return this.value === "text";
  }

  public get isSpanType(): boolean {
    return this.value === "span";
  }

  public get isRatingType(): boolean {
    return this.value === "rating";
  }
}
