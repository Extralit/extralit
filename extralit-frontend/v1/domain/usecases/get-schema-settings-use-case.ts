import { Schema } from "../entities/schema/Schema";
import { SchemaVersion } from "../entities/schema/SchemaVersion";
import { SchemaQuestion } from "../entities/schema/SchemaQuestion";
import { ColumnMeta } from "../entities/schema/ColumnMeta";
import { SchemaRepository } from "~/v1/infrastructure/repositories/SchemaRepository";

export interface SchemaSettings {
  schema: Schema;
  versions: SchemaVersion[];
  questions: SchemaQuestion[];
  // The current version's column manifest — sourced separately from `Field` rows since the
  // v1 fold moved it off `SchemaVersion` (see SchemaRepository.getColumns).
  columns: ColumnMeta[];
}

export class GetSchemaSettingsUseCase {
  constructor(private readonly schemaRepository: SchemaRepository) {}

  async execute(schemaId: string): Promise<SchemaSettings> {
    const [schema, versions, questions, columns] = await Promise.all([
      this.schemaRepository.getSchema(schemaId),
      this.schemaRepository.getVersions(schemaId),
      this.schemaRepository.getQuestions(schemaId),
      this.schemaRepository.getColumns(schemaId),
    ]);
    return { schema, versions, questions, columns };
  }
}
