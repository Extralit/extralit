import { Schema } from "../entities/schema/Schema";
import { SchemaRepository } from "~/v1/infrastructure/repositories/SchemaRepository";
import { type useSchemas } from "~/v1/infrastructure/storage/SchemasStorage";

export class GetSchemasUseCase {
  constructor(
    private readonly schemaRepository: SchemaRepository,
    // ts-injecty resolves the `useSchemas` hook by calling it, so the injected value
    // is the store object, not the hook (same contract as v1 GetWorkspacesUseCase).
    private readonly schemasStorage: ReturnType<typeof useSchemas>
  ) {}

  async execute(workspaceId: string): Promise<Schema[]> {
    const schemas = await this.schemaRepository.getSchemas(workspaceId);
    this.schemasStorage.saveSchemas(schemas);
    return schemas;
  }
}
