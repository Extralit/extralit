import { computed, onBeforeMount, ref } from "vue";
import { useResolve } from "ts-injecty";
import { GetSchemaRecordsUseCase } from "~/v1/domain/usecases/get-schema-records-use-case";
import { SearchRecordsUseCase } from "~/v1/domain/usecases/search-records-use-case";
import { GetSchemaSettingsUseCase } from "~/v1/domain/usecases/get-schema-settings-use-case";
import { RecordsPage } from "~/v1/domain/entities/schema/RecordsPage";
import { SearchCriteria, type RecordFilter } from "~/v1/domain/entities/search/SearchCriteria";
import { Schema } from "~/v1/domain/entities/schema/Schema";
import { ColumnMeta } from "~/v1/domain/entities/schema/ColumnMeta";
import { type SchemaRecordStatus } from "~/v1/domain/entities/schema/SchemaRecord";

const PAGE_SIZE = 25;

export const useSchemaRecordsViewModel = (schemaId: string) => {
  const getRecordsUseCase = useResolve(GetSchemaRecordsUseCase);
  const searchRecordsUseCase = useResolve(SearchRecordsUseCase);
  const getSettingsUseCase = useResolve(GetSchemaSettingsUseCase);

  const schema = ref<Schema | null>(null);
  const columns = ref<ColumnMeta[]>([]);
  const page = ref<RecordsPage>(new RecordsPage([], 0));
  const isLoading = ref(false);
  const searchText = ref("");
  const statusFilter = ref<SchemaRecordStatus | "">("");
  const currentOffset = ref(0);

  const hasQuery = computed(() => Boolean(searchText.value.trim() || statusFilter.value));

  const loadSettings = async () => {
    const settings = await getSettingsUseCase.execute(schemaId);
    schema.value = settings.schema;
    columns.value = settings.columns;
  };

  const search = async () => {
    isLoading.value = true;
    try {
      if (hasQuery.value) {
        const filters: RecordFilter[] = statusFilter.value
          ? [{ column: "status", op: "eq", value: statusFilter.value }]
          : [];
        const criteria = new SearchCriteria(searchText.value.trim() || null, filters, currentOffset.value, PAGE_SIZE);
        page.value = await searchRecordsUseCase.execute(schemaId, criteria);
      } else {
        page.value = await getRecordsUseCase.execute(schemaId, { offset: currentOffset.value, limit: PAGE_SIZE });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const goToOffset = async (offset: number) => {
    currentOffset.value = Math.max(0, offset);
    await search();
  };

  onBeforeMount(async () => {
    await Promise.all([loadSettings(), search()]);
  });

  return {
    schema,
    columns,
    page,
    isLoading,
    searchText,
    statusFilter,
    currentOffset,
    pageSize: PAGE_SIZE,
    search,
    goToOffset,
  };
};
