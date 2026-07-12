import { RecordsPage } from "../entities/record/RecordsPage";
import { SearchCriteria } from "../entities/search/SearchCriteria";
import { V2RecordRepository } from "~/v2/infrastructure/repositories/V2RecordRepository";

export class SearchRecordsUseCase {
  constructor(private readonly recordRepository: V2RecordRepository) {}

  execute(schemaId: string, criteria: SearchCriteria): Promise<RecordsPage> {
    return this.recordRepository.searchRecords(schemaId, criteria);
  }
}
