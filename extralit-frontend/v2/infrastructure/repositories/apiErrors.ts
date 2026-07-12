export interface V2ApiError {
  status: number | null;
  messages: string[];
}

interface PydanticDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

// v2 endpoints return two 422 body shapes (spec §7): domain errors {"detail": "<string>"}
// and pydantic request errors {"detail": [{loc, msg, type}]}. Normalize both.
export const normalizeV2ApiError = (error: unknown): V2ApiError => {
  const maybeAxios = error as { isAxiosError?: boolean; response?: { status: number; data?: { detail?: unknown } } };

  if (maybeAxios?.isAxiosError && maybeAxios.response) {
    const { status, data } = maybeAxios.response;
    const detail = data?.detail;

    if (typeof detail === "string") return { status, messages: [detail] };
    if (Array.isArray(detail)) {
      return {
        status,
        messages: (detail as PydanticDetail[]).map((d) => `${(d.loc ?? []).join(".")}: ${d.msg}`),
      };
    }
    return { status, messages: [`Request failed with status ${status}`] };
  }

  return { status: null, messages: [error instanceof Error ? error.message : String(error)] };
};
