export type RankingAnswer = { value: string; rank: number };

export type SpanAnswer = {
  start: number;
  end: number;
  label: string;
};

export type LabelAnswer = {
  value: string;
  label: string;
  description?: string;
};

export type AnswerCombinations =
  | string
  | string[]
  | number
  | RankingAnswer[]
  | SpanAnswer[]
  | LabelAnswer[];

export interface Answer {
  value: AnswerCombinations;
}
