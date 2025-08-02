import { useResolve } from "ts-injecty";
import { ref, useRoute, useContext } from "@nuxtjs/composition-api";
import { GetHfDatasetCreationUseCase } from "~/v1/domain/usecases/get-hf-dataset-creation-use-case";

export const useNewDatasetViewModel = () => {
  const { error } = useContext();
  const datasetConfig = ref();
  const getDatasetCreationUseCase = useResolve(GetHfDatasetCreationUseCase);

  const getNewHfDatasetByRepoId = async (repositoryId: string) => {
    try {
      datasetConfig.value = await getDatasetCreationUseCase.execute(repositoryId);
    } catch (e) {
      error({ statusCode: 404, message: "Cannot fetch the dataset" });
    }
  };

  const getNewHfDatasetByRepoIdFromUrl = async () => {
    const repositoryId = useRoute().value.params.id;
    await getNewHfDatasetByRepoId(decodeURI(repositoryId));
  };

  const changeSubset = (name: string) => {
    datasetConfig.value.changeSubset(name);
  };

  return {
    getNewHfDatasetByRepoId,
    getNewHfDatasetByRepoIdFromUrl,
    changeSubset,
    datasetConfig,
  };
};
