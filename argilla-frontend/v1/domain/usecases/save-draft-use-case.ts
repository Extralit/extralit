import { IEventDispatcher } from "@codescouts/events";
import { RecordResponseUpdatedEvent } from "../events/RecordResponseUpdatedEvent";
import { Record } from "../entities/record/Record";
import { RecordRepository } from "@/v1/infrastructure/repositories";

export class SaveDraftUseCase {
  constructor(
    private readonly recordRepository: RecordRepository,
    private readonly eventDispatcher: IEventDispatcher
  ) {}

  async execute(record: Record, duration?: number) {
    const response = await this.recordRepository.saveDraft(record, duration);

    record.submit(response);

    this.eventDispatcher.dispatch(new RecordResponseUpdatedEvent(record));
  }
}
