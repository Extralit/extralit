export interface OAuthProvider {
  name: string;
  display_name: string;
  enabled: boolean;
  icon?: string;
}

export interface BackendEnvironment {
  extralit: {
    show_huggingface_space_persistent_storage_warning: boolean;
    share_your_progress_enabled: boolean;
  };
  huggingface: {
    space_id: string;
    space_title: string;
    space_subdomain: string;
    space_host: string;
    space_repo_name: string;
    space_author_name: string;
    space_persistent_storage_enabled: boolean;
  };
  oauth_providers: OAuthProvider[];
}
