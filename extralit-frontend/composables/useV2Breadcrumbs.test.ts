import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useV2Breadcrumbs } from "./useV2Breadcrumbs";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";

describe("useV2Breadcrumbs", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("builds Home › workspace › Schemas with a workspace dropdown item", () => {
    const store = useWorkspaces();
    store.saveWorkspaces([{ id: "w-1", name: "e2e-v2" } as never]);
    store.saveSelectedWorkspace({ id: "w-1", name: "e2e-v2" } as never);

    const crumbs = useV2Breadcrumbs().schemasBreadcrumbs();

    expect(crumbs.map((c) => c.name)).toEqual(["Home", "e2e-v2", "Schemas"]);
    expect(crumbs[1]).toMatchObject({ isWorkspace: true, workspaceId: "w-1" });
    expect(crumbs[2].link).toBe("/schemas");
  });

  it("appends leaf crumbs", () => {
    const crumbs = useV2Breadcrumbs().schemasBreadcrumbs([{ name: "sample_size", link: "/schemas/s-1" }]);
    expect(crumbs.at(-1)).toMatchObject({ name: "sample_size", link: "/schemas/s-1" });
  });
});
