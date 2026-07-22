import { Question } from "../question/Question";
import { type ReviewCell } from "./ReviewCell";
import { SuggestionHint } from "./SuggestionHint";

// Adapters between server value shapes and the extracted leaf-widget option shapes
// (see Task 9 contracts). Ids follow v1's `${questionName}_${value}` convention.

export interface LabelOption {
  id: string;
  text: string;
  value: string;
  description: string | null;
  isSelected: boolean;
}

export const buildLabelOptions = (question: Question, selected: unknown): LabelOption[] => {
  const selectedValues = Array.isArray(selected)
    ? (selected as string[])
    : selected != null
      ? [selected as string]
      : [];
  return question.options.map((option) => ({
    id: `${question.name}_${option.value}`,
    text: option.text,
    value: option.value,
    description: option.description,
    isSelected: selectedValues.includes(option.value),
  }));
};

export const selectedFromLabelOptions = (options: LabelOption[], multiple: boolean): string | string[] | null => {
  const selected = options.filter((o) => o.isSelected).map((o) => o.value);
  if (multiple) return selected;
  return selected[0] ?? null;
};

export interface RatingOption {
  id: string;
  value: number;
  isSelected: boolean;
}

export const buildRatingOptions = (question: Question, selected: unknown): RatingOption[] =>
  question.ratingValues.map((value) => ({
    id: `${question.name}_${value}`,
    value,
    isSelected: selected === value,
  }));

export const selectedFromRatingOptions = (options: RatingOption[]): number | null =>
  options.find((o) => o.isSelected)?.value ?? null;

export interface RankingValue {
  id: string;
  text: string;
  value: string;
  description: string | null;
  rank: number | null;
}

export const buildRankingValues = (question: Question, ranked: unknown): RankingValue[] => {
  const ranks = new Map<string, number>(
    Array.isArray(ranked) ? (ranked as { value: string; rank: number }[]).map((r) => [r.value, r.rank]) : []
  );
  return question.options.map((option) => ({
    id: `${question.name}_${option.value}`,
    text: option.text,
    value: option.value,
    description: option.description,
    rank: ranks.get(option.value) ?? null,
  }));
};

export const rankingAnswerFromValues = (values: RankingValue[]): { value: string; rank: number }[] =>
  values
    .filter((v) => v.rank != null)
    .sort((a, b) => (a.rank as number) - (b.rank as number))
    .map((v) => ({ value: v.value, rank: v.rank as number }));

export const suggestionHintFor = (cell: ReviewCell): SuggestionHint | null => {
  if (cell.source !== "suggestion" || !cell.provenance) return null;
  return new SuggestionHint(
    cell.provenance.suggestedValue,
    cell.provenance.agent,
    cell.provenance.score,
    cell.question.type === "multi_label_selection"
  );
};
