import { ProjectionRepository } from "~/v1/infrastructure/repositories/ProjectionRepository";
import {
  WorkspaceProjection,
  type ProjectionColumn,
  type ProjectionGridRow,
} from "~/v1/domain/entities/projection/WorkspaceProjection";
import { type useExtractions } from "~/v1/infrastructure/storage/ExtractionsStorage";

// The server's `limit` cap per page.
export const PROJECTION_PAGE_SIZE = 100;

export class GetWorkspaceProjectionUseCase {
  constructor(
    private readonly projectionRepository: ProjectionRepository,
    // ts-injecty resolves the `useExtractions` hook by calling it, so the injected
    // value is the store object, not the hook.
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
        // Every page returns the same manifest and total — capture both from the first
        // page only, in server order, so a shifting count mid-paging can't mix into a
        // result built from a stale row set.
        columns = page.columns;
        totalReferences = page.totalReferences;
      }
      rows.push(...page.rows);

      // Guard against a zero-progress response (e.g. a server bug that keeps reporting
      // outstanding references but never returns any) so a stuck server can't hang the browser.
      // Safe because every reference in a page yields >= 1 row: the server's `spine` CTE
      // emits `max_idx + 1` rows per reference (minimum 1) and keeps the spine row even when
      // `column_name IS NULL` — so an empty `rows` array can only mean an empty reference page.
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
