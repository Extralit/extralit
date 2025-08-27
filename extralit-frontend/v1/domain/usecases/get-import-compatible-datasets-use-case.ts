import { type NuxtAxiosInstance } from "@nuxtjs/axios";
import { Dataset } from "../entities/dataset/Dataset";

export interface GetImportCompatibleDatasetsParams {
  columnNames: string[];
  workspaceId?: string;
}

export class GetImportCompatibleDatasetsUseCase {
  constructor(private readonly axios: NuxtAxiosInstance) {}

  async execute(params: GetImportCompatibleDatasetsParams): Promise<Dataset[]> {
    try {
      const response = await this.axios.get("/api/v1/datasets/compatible", {
        params: {
          column_names: params.columnNames,
          workspace_id: params.workspaceId,
        },
      });

      return (response.data.items || []).map(
        (datasetFromBackend: any) =>
          new Dataset(
            datasetFromBackend.id,
            datasetFromBackend.name,
            datasetFromBackend.guidelines,
            datasetFromBackend.status,
            datasetFromBackend.workspace_id,
            datasetFromBackend.workspace_name,
            datasetFromBackend.allow_extra_metadata,
            {
              strategy: datasetFromBackend.distribution.strategy,
              minSubmitted: datasetFromBackend.distribution.min_submitted,
            },
            datasetFromBackend.metadata,
            datasetFromBackend.inserted_at,
            datasetFromBackend.updated_at,
            datasetFromBackend.last_activity_at
          )
      );
    } catch (error) {
      console.error("Error fetching compatible datasets:", error);
      throw new Error("Failed to fetch compatible datasets");
    }
  }
}
