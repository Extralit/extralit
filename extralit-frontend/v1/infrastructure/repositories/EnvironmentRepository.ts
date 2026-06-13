import type { AxiosInstance } from "axios";
import { BackendEnvironment } from "../types/environment";
import { PublicAxiosInstance } from "../services/useAxiosExtension";
import { largeCache } from "./AxiosCache";
import { Environment } from "~/v1/domain/entities/environment/Environment";
import { IEnvironmentRepository } from "~/v1/domain/services/IEnvironmentRepository";

const enum ENVIRONMENT_API_ERRORS {
  FETCHING = "ERROR_FETCHING_ENVIRONMENT_SETTINGS",
}

export class EnvironmentRepository implements IEnvironmentRepository {
  private readonly axios: AxiosInstance;
  constructor(axios: PublicAxiosInstance) {
    this.axios = axios.makePublic();
  }

  async getEnvironment(): Promise<Environment> {
    try {
      const { data } = await this.axios.get<BackendEnvironment>("v1/settings", largeCache());

      const {
        extralit = {
          share_your_progress_enabled: false,
          show_huggingface_space_persistent_storage_warning: false,
        },
        huggingface = {
          space_author_name: "",
          space_host: "",
          space_id: "",
          space_persistent_storage_enabled: false,
          space_repo_name: "",
          space_subdomain: "",
          space_title: "",
        },
      } = data;

      return new Environment(
        {
          showHuggingfaceSpacePersistentStorageWarning: extralit.show_huggingface_space_persistent_storage_warning,
          shareYourProgressEnabled: extralit.share_your_progress_enabled,
        },
        {
          spaceId: huggingface.space_id,
          spaceTitle: huggingface.space_title,
          spaceSubdomain: huggingface.space_subdomain,
          spaceHost: huggingface.space_host,
          spaceRepoName: huggingface.space_repo_name,
          spaceAuthorName: huggingface.space_author_name,
          spacePersistentStorageEnabled: huggingface.space_persistent_storage_enabled,
        }
      );
    } catch (err) {
      throw {
        response: ENVIRONMENT_API_ERRORS.FETCHING,
      };
    }
  }
}
