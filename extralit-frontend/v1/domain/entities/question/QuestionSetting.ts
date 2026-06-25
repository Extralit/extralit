import { QuestionType, type QuestionTypes } from "./QuestionType";

export interface QuestionPrototype {
  type: QuestionTypes;
  use_markdown?: boolean;
  use_table?: boolean;
  visible_options?: number;
  options?: any[];
  options_order?: "natural" | "suggestion";
  allow_overlapping?: boolean;
  allow_character_annotation?: boolean;
  field?: string;
  strict?: boolean;
}

export class QuestionSetting {
  type: QuestionType;
  use_markdown: boolean;
  use_table: boolean;
  visible_options: number;
  allow_overlapping: boolean;
  allow_character_annotation: boolean;
  field: string;
  options: any;
  options_order: "natural" | "suggestion";
  strict: boolean;

  constructor(settings: QuestionPrototype) {
    this.type = QuestionType.from(settings.type);

    this.use_markdown = settings.use_markdown;
    this.use_table = settings.use_table;
    this.visible_options = settings.visible_options;
    this.options = settings.options;
    this.options_order = settings.options_order;
    this.allow_overlapping = settings.allow_overlapping;
    this.allow_character_annotation = settings.allow_character_annotation;
    this.field = settings.field;
    this.strict = settings.strict ?? true; // Default to true for backward compatibility
  }

  get suggestionFirst() {
    if (!this.options_order) return undefined;

    return this.options_order === "suggestion";
  }

  set suggestionFirst(value: boolean) {
    this.options_order = value ? "suggestion" : "natural";
  }

  get shouldShowVisibleOptions() {
    return this.options?.length > 3 && !!this.visible_options;
  }

  isEqual(setting: QuestionSetting) {
    return (
      this.use_markdown === setting.use_markdown &&
      this.use_table === setting.use_table &&
      this.visible_options === setting.visible_options &&
      this.options_order === setting.options_order &&
      this.strict === setting.strict &&
      JSON.stringify(this.options) === JSON.stringify(setting.options)
    );
  }

  toPrototype(): QuestionPrototype {
    return {
      type: this.type.value as QuestionTypes,
      use_markdown: this.use_markdown,
      use_table: this.use_table,
      visible_options: this.visible_options,
      options: this.options,
      options_order: this.options_order,
      allow_overlapping: this.allow_overlapping,
      allow_character_annotation: this.allow_character_annotation,
      field: this.field,
      strict: this.strict,
    };
  }
}
