import { isEqual } from "lodash";
import { ref, Ref } from "vue-demi";
import { useResolve } from "ts-injecty";

import { Question } from "@/v1/domain/entities/question/Question";
import { GetExtractionSchemaUseCase } from "@/v1/domain/usecases/get-extraction-schema-use-case";

import { DataFrame, PanderaSchema } from "./types";
import { useDataset } from "@/v1/infrastructure/storage/DatasetStorage";
import { waitForAsyncValue } from "~/v1/infrastructure/services/useWait";

export interface SchemaTableViewModel {
  tableJSON: Ref<DataFrame>;
  validation: Ref<PanderaSchema | null>;
  indexColumns: Ref<string[]>;
  refColumns: Ref<string[]>;
  groupbyColumns: Ref<string[] | null>;
}

export const useSchemaTableViewModel = (
  props: { 
    tableJSON: DataFrame, 
    editable: boolean, 
    hasValidValues: boolean,
    questions: Question[],
  }, 
) => {
  const getSchema = useResolve(GetExtractionSchemaUseCase);
  const { state: dataset } = useDataset();

  const tableJSON = ref<DataFrame>(props.tableJSON);

  const validation = ref<PanderaSchema | null>(null);
  const indexColumns = ref(tableJSON.value?.schema?.primaryKey || []);
  const refColumns = ref(
    tableJSON.value?.schema?.fields
      .map(field => field.name)
      .filter(name => typeof name === 'string' && (name.endsWith('_ref') || (name.endsWith('_ID') && !name.toLowerCase().startsWith(tableJSON.value?.schema?.schemaName?.toLowerCase())))) || []
  );
  const groupbyColumns = ref(refColumns.value || null);

  const fetchValidation = async ({ latest = false }: { latest?: boolean } = {}) => {
    var schemaName: string = tableJSON.value?.schema?.schemaName || tableJSON.value?.validation?.name;
    if (!schemaName) {
      return;
    }
    var version_id: string = latest ? null : tableJSON.value.schema?.version_id;
    await waitForAsyncValue(() => dataset.workspaceName);
    
    const [schema, fileMetadata] = await getSchema.fetch(dataset.workspaceName, schemaName, version_id);

    const schemaMetadataUpdate = {
      ...tableJSON.value.schema,
      ...fileMetadata
    };
    if (!isEqual(tableJSON.value?.schema, schemaMetadataUpdate)) {
      tableJSON.value.schema = schemaMetadataUpdate;
    }
    validation.value = schema;
  };

  return {
    tableJSON,
    validation,
    indexColumns,
    refColumns,
    groupbyColumns,
    fetchValidation,
  }
}