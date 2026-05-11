import type { DashboardDetail, DashboardFreshnessStatus, DashboardNarrative, DashboardWidget } from "@next/features/dashboards/types";

export interface DashboardShareLink {
  id: number;
  dashboard_id: number;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
  share_url: string;
}

export interface DashboardShareLinkCreateResponse extends DashboardShareLink {
  token: string;
}

export interface CreateDashboardShareLinkPayload {
  expires_at?: string | null;
}

export interface SharedDashboardDetail {
  id: number;
  name: string;
  freshness_status: DashboardFreshnessStatus;
  last_successful_refresh_at: string | null;
  next_refresh_at: string | null;
  narrative: DashboardNarrative;
  widgets: DashboardWidget[];
}

export function toAliasedShareUrl(shareUrl: string): string {
  if (shareUrl.startsWith("http://") || shareUrl.startsWith("https://")) {
    return shareUrl.replace("/public/dashboards/", "/share/");
  }

  return shareUrl.replace(/^\/public\/dashboards\//, "/share/");
}

export function toAbsoluteShareUrl(shareUrl: string): string {
  const aliasedPath = toAliasedShareUrl(shareUrl);
  if (aliasedPath.startsWith("http://") || aliasedPath.startsWith("https://")) {
    return aliasedPath;
  }
  return `${window.location.origin}${aliasedPath}`;
}
