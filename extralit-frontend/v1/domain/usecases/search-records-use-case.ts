import { RecordsPage } from "../entities/schema/RecordsPage";
import { SearchCriteria } from "../entities/search/SearchCriteria";
import { SchemaRecordRepository } from "~/v1/infrastructure/repositories/SchemaRecordRepository";

export class SearchRecordsUseCase {
  constructor(private readonly recordRepository: SchemaRecordRepository) {}

  execute(schemaId: string, criteria: SearchCriteria): Promise<RecordsPage> {
    return this.recordRepository.searchRecords(schemaId, criteria);
  }
}
