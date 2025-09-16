import { Dictionary } from "../common/Params";

export type ProviderType = "huggingface" | "extralit-hub";
export type OAuthParams = Dictionary<string | (string | null)[]>;
export class OAuthProvider {
  constructor(public readonly name: ProviderType) {}

  get isHuggingFace() {
    return this.name === "huggingface";
  }

  get isExtralitHub() {
    return this.name === "extralit-hub";
  }
}
