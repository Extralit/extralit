import { Schema } from "../entities/schema/Schema";
import { SchemaRepository } from "~/v2/infrastructure/repositories/SchemaRepository";
import { type useSchemas } from "~/v2/infrastructure/storage/SchemasStorage";

export class GetSchemasUseCase {
  constructor(
    private readonly schemaRepository: SchemaRepository,
    private readonly schemasStorage: typeof useSchemas
  ) {}

  async execute(workspaceId: string): Promise<Schema[]> {
    const schemas = await this.schemaRepository.getSchemas(workspaceId);
    this.schemasStorage().saveSchemas(schemas);
    return schemas;
  }
}
