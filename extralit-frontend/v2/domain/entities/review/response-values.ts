// The server stores and returns response values double-wrapped: {question_name: {"value": ...}}
// on BOTH PUT and GET, while projection cells are bare (spec §7 asymmetric-wrapping gotcha).
export const wrapResponseValues = (values: Record<string, unknown>): Record<string, { value: unknown }> =>
  Object.fromEntries(Object.entries(values).map(([name, value]) => [name, { value }]));

export const unwrapResponseValues = (
  wrapped: Record<string, { value: unknown }> | null | undefined
): Record<string, unknown> =>
  Object.fromEntries(Object.entries(wrapped ?? {}).map(([name, box]) => [name, box?.value]));
