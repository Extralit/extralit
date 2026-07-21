import { ProjectionRepository } from "~/v2/infrastructure/repositories/ProjectionRepository";
import {
  WorkspaceProjection,
  type ProjectionColumn,
  type ProjectionGridRow,
} from "~/v2/domain/entities/projection/WorkspaceProjection";
import { type useExtractions } from "~/v2/infrastructure/storage/ExtractionsStorage";

// The server's `limit` cap per page.
export const PROJECTION_PAGE_SIZE = 100;

export class GetWorkspaceProjectionUseCase {
  constructor(
    private readonly projectionRepository: ProjectionRepository,
    // ts-injecty resolves the `useExtractions` hook by calling it, so the injected
    // value is the store object, not the hook (same contract as GetReferenceReviewUseCase).
    private readonly extractionsStorage: ReturnType<typeof useExtractions>
  ) {}

  // Loads the whole workspace projection in one shot: the grid renders as a single
  // Perspective table client-side, so it needs every row up front rather than a page
  // at a time. Streaming this via Arrow IPC is the recorded §5 follow-up.
  async execute(workspaceId: string): Promise<WorkspaceProjection> {
    let offset = 0;
    let columns: ProjectionColumn[] = [];
    let totalReferences = 0;
    const rows: ProjectionGridRow[] = [];

    for (;;) {
      const page = await this.projectionRepository.getWorkspaceProjection(workspaceId, offset, PROJECTION_PAGE_SIZE);
      if (offset === 0) {
        // Every page returns the same manifest — capture it once, in server order.
        columns = page.columns;
      }
      totalReferences = page.totalReferences;
      rows.push(...page.rows);

      // Guard against a zero-progress response (e.g. a server bug that keeps reporting
      // outstanding references but never returns any) so a stuck server can't hang the browser.
      if (page.rows.length === 0) {
        break;
      }

      // `offset`/`limit` count REFERENCES, not the fanned-out rows the endpoint returns —
      // always advance by the fixed page size, never by `rows.length`.
      offset += PROJECTION_PAGE_SIZE;
      if (offset >= totalReferences) {
        break;
      }
    }

    const projection = new WorkspaceProjection(columns, rows, totalReferences);
    this.extractionsStorage.saveProjection(projection);
    return projection;
  }
}
