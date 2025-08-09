/**
 * Enhanced breadcrumb item interface that supports workspace detection
 * and dynamic link generation for workspace-aware breadcrumbs.
 */
export interface BreadcrumbItem {
  /** Display name of the breadcrumb item */
  name: string;

  /** Navigation link - can be a string path or Nuxt route object */
  link?: string | object;

  /** Action to emit when breadcrumb is clicked (for non-link breadcrumbs) */
  action?: string;

  /** Flag to identify workspace breadcrumb items for special rendering */
  isWorkspace?: boolean;

  /** Current workspace ID for workspace breadcrumbs */
  workspaceId?: string;
}

/**
 * Event data emitted when workspace selection changes in breadcrumb dropdown
 */
export interface WorkspaceChangeEvent {
  /** Selected workspace object */
  workspace: any | null;

  /** Selected workspace ID */
  workspaceId: string | null;

  /** Selected workspace name */
  workspaceName: string | null;

  /** Updated link object with workspace parameter */
  link: object;
}
