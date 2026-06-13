import type { AxiosInstance } from "axios";
import type { Response } from "~/v1/infrastructure/types/api";
import type { BackendDataset } from "~/v1/infrastructure/types/dataset";

export interface GetImportCompatibleDatasetsParams {
  columnNames: string[];
  workspaceId?: string;
}

export class GetImportCompatibleDatasetsUseCase {
  constructor(private readonly axios: AxiosInstance) { }

  async execute(params: GetImportCompatibleDatasetsParams): Promise<BackendDataset[]> {
    try {
      const { data } = await this.axios.post<Response<BackendDataset[]>>("/v1/datasets/compatible", {
        column_names: params.columnNames,
        workspace_id: params.workspaceId,
      });

      return data.items || []
    } catch (error) {
      throw new Error("Failed to fetch compatible datasets");
    }
  }
}
