import type { AxiosInstance } from "axios";
import type { components } from "../api/generated/v2-api";
import { unwrapResponseValues, wrapResponseValues } from "~/v2/domain/entities/review/response-values";

type BackendSuggestions = components["schemas"]["Suggestions"];
type BackendResponse = components["schemas"]["ResponseRead"];

export type ResponseStatus = "draft" | "submitted" | "discarded";

export interface RecordSuggestion {
  id: string;
  recordId: string;
  questionId: string; // suggestions key by question ID, not name (spec §7 asymmetric keying)
  value: unknown;
  score: number | number[] | null;
  agent: string | null;
}

export interface RecordResponse {
  id: string;
  recordId: string;
  userId: string;
  values: Record<string, unknown>; // unwrapped; keyed by question NAME
  status: ResponseStatus;
}

const toResponse = (backend: BackendResponse): RecordResponse => ({
  id: backend.id,
  recordId: backend.record_id,
  userId: backend.user_id,
  values: unwrapResponseValues(backend.values as Record<string, { value: unknown }> | null),
  status: backend.status as ResponseStatus,
});

export class AnnotationRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getSuggestions(recordId: string): Promise<RecordSuggestion[]> {
    const { data } = await this.axios.get<BackendSuggestions>(`/v2/records/${recordId}/suggestions`);
    return data.items.map((s) => ({
      id: s.id,
      recordId: s.record_id,
      questionId: s.question_id,
      value: s.value,
      score: (s.score ?? null) as number | number[] | null,
      agent: s.agent ?? null,
    }));
  }

  async getResponse(recordId: string): Promise<RecordResponse | null> {
    // 200 with literal null body when the user has no response yet — never a 404.
    const { data } = await this.axios.get<BackendResponse | null>(`/v2/records/${recordId}/responses`);
    return data ? toResponse(data) : null;
  }

  async upsertResponse(
    recordId: string,
    values: Record<string, unknown> | null,
    status: ResponseStatus
  ): Promise<RecordResponse> {
    const body = { values: values ? wrapResponseValues(values) : null, status };
    const { data } = await this.axios.put<BackendResponse>(`/v2/records/${recordId}/responses`, body);
    return toResponse(data);
  }
}
