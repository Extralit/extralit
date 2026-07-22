import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";
import { type BreadcrumbItem } from "~/v1/infrastructure/types/breadcrumb";

export const useV2Breadcrumbs = () => {
  const workspacesStore = useWorkspaces();

  const schemasBreadcrumbs = (leaf: { name: string; link?: string }[] = []): BreadcrumbItem[] => {
    const selected = workspacesStore.get().selectedWorkspace;
    const crumbs: BreadcrumbItem[] = [{ name: "Home", link: "/" }];
    if (selected) {
      crumbs.push({ name: selected.name, isWorkspace: true, workspaceId: selected.id });
    }
    crumbs.push({ name: "Schemas", link: "/schemas" });
    crumbs.push(...leaf);
    return crumbs;
  };

  const extractionsBreadcrumbs = (leaf: { name: string; link?: string }[] = []): BreadcrumbItem[] => {
    const selected = workspacesStore.get().selectedWorkspace;
    const crumbs: BreadcrumbItem[] = [{ name: "Home", link: "/" }];
    if (selected) {
      crumbs.push({ name: selected.name, isWorkspace: true, workspaceId: selected.id });
    }
    crumbs.push({ name: "Extractions", link: "/extractions" });
    crumbs.push(...leaf);
    return crumbs;
  };

  return { schemasBreadcrumbs, extractionsBreadcrumbs };
};
