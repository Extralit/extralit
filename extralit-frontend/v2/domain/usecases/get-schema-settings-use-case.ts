import { Schema } from "../entities/schema/Schema";
import { SchemaVersion } from "../entities/schema/SchemaVersion";
import { Question } from "../entities/question/Question";
import { SchemaRepository } from "~/v2/infrastructure/repositories/SchemaRepository";

export interface SchemaSettings {
  schema: Schema;
  versions: SchemaVersion[];
  questions: Question[];
}

export class GetSchemaSettingsUseCase {
  constructor(private readonly schemaRepository: SchemaRepository) {}

  async execute(schemaId: string): Promise<SchemaSettings> {
    const [schema, versions, questions] = await Promise.all([
      this.schemaRepository.getSchema(schemaId),
      this.schemaRepository.getVersions(schemaId),
      this.schemaRepository.getQuestions(schemaId),
    ]);
    return { schema, versions, questions };
  }
}
