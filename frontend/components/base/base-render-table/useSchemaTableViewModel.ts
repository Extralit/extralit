import { isEqual } from "lodash";
import { ref, Ref, onBeforeMount } from "vue-demi";
import { useResolve } from "ts-injecty";

import { Question } from "@/v1/domain/entities/question/Question";
import { GetExtractionSchemaUseCase } from "@/v1/domain/usecases/get-extraction-schema-use-case";

import { DataFrame, Data, ReferenceValues, PanderaSchema } from "./types";
import { useDataset } from "@/v1/infrastructure/storage/DatasetStorage";


export default function waitForCondition(getValue: () => any, interval=100) {
  return new Promise((resolve, reject) => {
    const checkInterval = setInterval(() => {
      if (getValue()) {
        clearInterval(checkInterval);
        resolve(true);
      }
    }, interval);
  });
};

export interface SchemaTableViewModel {
  tableJSON: Ref<DataFrame>;
  validation: Ref<PanderaSchema | null>;
  indexColumns: Ref<string[]>;
  refColumns: Ref<string[]>;
  groupbyColumns: Ref<string[] | null>;
}

export const useSchemaTableViewModel = (
  props: { 
    tableData: string, 
    editable: boolean, 
    hasValidValues: boolean,
    questions: Question[],
  }, 
) => {
  const getSchema = useResolve(GetExtractionSchemaUseCase);
  const { state: dataset } = useDataset();

  const tableJSON = ref<DataFrame>(JSON.parse(props.tableData));
  const validation = ref<PanderaSchema | null>(null);
  const indexColumns = ref(tableJSON.value?.schema?.primaryKey || []);
  const refColumns = ref(
    tableJSON.value?.schema?.fields
      .map(field => field.name)
      .filter(name => typeof name === 'string' && name.endsWith('_ref')) || []
  );
  const groupbyColumns = ref(refColumns.value || null);

  const fetchValidation = async ({ latest = false }: { latest?: boolean } = {}) => {
    var schemaName: string = tableJSON.value.schema?.schemaName;
    var version_id: string = latest ? null : tableJSON.value.schema?.version_id;
    await waitForCondition(() => dataset.workspaceName);
    
    if (!tableJSON.value.schema.schemaName) {
      schemaName = tableJSON.value?.validation?.name;
    }
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