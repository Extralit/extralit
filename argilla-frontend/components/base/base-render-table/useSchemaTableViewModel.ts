import { isEqual } from "lodash";
import { ref, Ref } from "vue-demi";
import { useResolve } from "ts-injecty";

import { Question } from "@/v1/domain/entities/question/Question";
import { GetExtractionSchemaUseCase } from "@/v1/domain/usecases/get-extraction-schema-use-case";
import { TableData } from "~/v1/domain/entities/table/TableData";
import { ValidationSchema } from "~/v1/domain/entities/table/Validation";

import { useDataset } from "@/v1/infrastructure/storage/DatasetStorage";
import { waitForAsyncValue } from "~/v1/infrastructure/services/useWait";

export interface SchemaTableViewModel {
  tableJSON: Ref<TableData>;
  validation: Ref<ValidationSchema | null>;
  indexColumns: Ref<string[]>;
  refColumns: Ref<string[]>;
  groupbyColumns: Ref<string[] | null>;
}

export const useSchemaTableViewModel = (
  props: { 
    tableJSON: TableData, 
    editable: boolean, 
    hasValidValues: boolean,
    questions: Question[],
  }, 
) => {
  const getSchema = useResolve(GetExtractionSchemaUseCase);
  const { state: dataset } = useDataset();

  const validation = ref<ValidationSchema | null>(null);
  const indexColumns = ref(props.tableJSON?.schema?.primaryKey || []);
  const refColumns = ref(
    props.tableJSON?.schema?.fields
      .map(field => field.name)
      .filter(name => typeof name === 'string' && (name.endsWith('_ref') || (name.endsWith('_ID') && !name.toLowerCase().startsWith(props.tableJSON?.schema?.schemaName?.toLowerCase())))) || []
  );
  const groupbyColumns = ref(refColumns.value || null);

  const fetchValidation = async ({ latest = false }: { latest?: boolean } = {}) => {
    var schemaName: string = props.tableJSON?.schema?.schemaName || props.tableJSON?.validation?.name;
    if (!schemaName) {
      return;
    }
    var version_id: string = latest ? null : props.tableJSON.schema?.version_id;
    await waitForAsyncValue(() => dataset.workspaceName);
    
    const [schema, fileMetadata] = await getSchema.fetch(dataset.workspaceName, schemaName, version_id);

    const schemaMetadataUpdate = {
      ...props.tableJSON.schema,
      ...fileMetadata
    };
    if (!isEqual(props.tableJSON?.schema, schemaMetadataUpdate)) {
      props.tableJSON.schema = schemaMetadataUpdate;
    }
    validation.value = schema;
  };

  return {
    validation,
    indexColumns,
    refColumns,
    groupbyColumns,
    fetchValidation,
  }
}