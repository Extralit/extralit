import { useStoreFor } from "@/v1/store/create";
import { WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";

// Class name is the Pinia store key — must stay unique vs every v1/v2 useStoreFor class.
class Extractions {
  constructor(public readonly projection: WorkspaceProjection | null = null) {}
}

interface IExtractionsStorage {
  saveProjection(projection: WorkspaceProjection): void;
}

const useStoreForExtractions = useStoreFor<Extractions, IExtractionsStorage>(Extractions);

export const useExtractions = () => {
  const store = useStoreForExtractions();

  const saveProjection = (projection: WorkspaceProjection) => {
    store.save(new Extractions(projection));
  };

  return { ...store, saveProjection };
};
