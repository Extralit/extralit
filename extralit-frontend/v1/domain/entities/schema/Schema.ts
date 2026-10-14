export class Schema {
  constructor(
    public readonly id: string,
    public readonly name: string,
    public readonly status: string,
    public readonly workspaceId: string,
    public readonly currentVersionId: string | null,
    public readonly settings: Record<string, unknown>,
    public readonly insertedAt: string,
    public readonly updatedAt: string
  ) {}
}
