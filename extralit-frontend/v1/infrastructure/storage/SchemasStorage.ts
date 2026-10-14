import { useStoreFor } from "@/v1/store/create";
import { Schema } from "~/v1/domain/entities/schema/Schema";

// Class name is the Pinia store key — must stay unique vs every v1 useStoreFor class.
class Schemas {
  constructor(public readonly schemas: Schema[] = []) {}
}

interface ISchemasStorage {
  saveSchemas(schemas: Schema[]): void;
}

const useStoreForSchemas = useStoreFor<Schemas, ISchemasStorage>(Schemas);

export const useSchemas = () => {
  const store = useStoreForSchemas();

  const saveSchemas = (schemas: Schema[]) => {
    store.save(new Schemas(schemas));
  };

  return { ...store, saveSchemas };
};
