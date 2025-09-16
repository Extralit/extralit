import type { OAuthProvider } from "../../../infrastructure/types/environment";

export class Environment {
  constructor(
    private readonly extralit: {
      showHuggingfaceSpacePersistentStorageWarning: boolean;
      shareYourProgressEnabled: boolean;
    },
    private readonly huggingface: {
      spaceId: string;
      spaceTitle: string;
      spaceSubdomain: string;
      spaceHost: string;
      spaceRepoName: string;
      spaceAuthorName: string;
      spacePersistentStorageEnabled: boolean;
    },
    private readonly oauthProviders: OAuthProvider[] = []
  ) {}

  get shouldShowHuggingfaceSpacePersistentStorageWarning(): boolean {
    return this.extralit.showHuggingfaceSpacePersistentStorageWarning && !this.huggingface.spacePersistentStorageEnabled;
  }

  get shareYourProgressEnabled() {
    return this.extralit.shareYourProgressEnabled;
  }

  get huggingFaceSpace() {
    if (this.huggingface?.spaceId) {
      return {
        space: this.huggingface.spaceRepoName,
        user: this.huggingface.spaceAuthorName,
        host: this.huggingface.spaceHost,
      };
    }
  }

  get availableOAuthProviders(): OAuthProvider[] {
    return this.oauthProviders.filter(provider => provider.enabled);
  }

  hasOAuthProvider(providerName: string): boolean {
    return this.oauthProviders.some(provider => provider.name === providerName && provider.enabled);
  }
}
