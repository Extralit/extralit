// Implements the duck-type the extracted leaf widgets consume as their `suggestion` prop:
// isSuggested(value) / getSuggestion(value) -> { agent, score?: { fixed } } (see Task 9 contract).
export class SuggestionHint {
  constructor(
    private readonly suggestedValue: unknown,
    private readonly agent: string | null,
    private readonly score: number | null,
    private readonly multiple: boolean
  ) {}

  isSuggested(value: unknown): boolean {
    if (this.multiple && Array.isArray(this.suggestedValue)) {
      return (this.suggestedValue as unknown[]).includes(value);
    }
    return this.suggestedValue === value;
  }

  getSuggestion(value: unknown): { agent: string | null; score?: { fixed: string } } | undefined {
    if (!this.isSuggested(value)) return undefined;
    return { agent: this.agent, score: this.score != null ? { fixed: this.score.toFixed(1) } : undefined };
  }
}
