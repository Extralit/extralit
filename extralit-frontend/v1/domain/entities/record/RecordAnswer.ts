import { Answer, AnswerCombinations } from "../IAnswer";

export type RecordStatus = "valid" | "pending" | "submitted" | "discarded" | "draft";

export class RecordAnswer implements Answer {
  constructor(
    public readonly id: string,
    public readonly status: RecordStatus,
    public readonly value: AnswerCombinations,
    public readonly updatedAt: string,
    public duration?: number
  ) {}
}
