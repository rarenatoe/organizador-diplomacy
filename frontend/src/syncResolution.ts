export type ResolutionAction =
  | "merge_notion"
  | "merge_local"
  | "link_only"
  | "link_rename"
  | "use_existing"
  | "skip";

export interface MergePair {
  from: string;
  to: string;
  action: ResolutionAction;
  notion_id?: string;
}
