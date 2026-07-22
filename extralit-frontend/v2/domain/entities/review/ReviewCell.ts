import { Question } from "../question/Question";

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
