export type RankingAnswer = { value: string; rank: number };

export type SpanAnswer = {
  start: number;
  end: number;
  label: string;
};

export type LabelAnswer = {
  value: string;
  text: string;
  description?: string;
};

export type TableAnswer = {
  data: Array<{ [field: string]: any }>;
  schema: {
    primaryKey: string[];
    fields: Array<{
      name: string;
      type: string;
      extDtype?: string;
    }>;
    metadata?: {
      schemaName?: string;
      etag?: string;
      version_id?: string;
      last_modified?: Date;
      version_tag?: string;
      is_latest?: boolean;
    };
    schemaName?: string;
    version_id?: string;
    is_latest?: boolean;
  };
  reference?: string;
  validation?: {
    name: string;
    columns: {
      [columnName: string]: {
        required: boolean;
        description: string;
        dtype: string;
        nullable: boolean;
        unique: boolean;
        checks: any;
      };
    };
    index: Array<{
      name: string;
      required: boolean;
      description: string;
      dtype: string;
      nullable: boolean;
      unique: boolean;
      checks: any;
    }>;
    checks?: any;
  };
};

export type AnswerCombinations =
  | string
  | string[]
  | number
  | RankingAnswer[]
  | SpanAnswer[]
  | LabelAnswer[]
  | TableAnswer;

export interface Answer {
  value: AnswerCombinations;
}
