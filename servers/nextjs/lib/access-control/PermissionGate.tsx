"use client";

import { ReactNode } from "react";
import { useSelector } from "react-redux";
import { RootState } from "@/store/store";

type PermissionGateProps = {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
};

const ROLE_PERMISSIONS: Record<string, string[]> = {
  owner: ["presentation:read", "presentation:write", "presentation:delete", "presentation:export",
    "template:read", "template:write", "template:delete",
    "integration:read", "integration:write", "integration:manage",
    "webhook:read", "webhook:write", "webhook:manage",
    "workspace:read", "workspace:write", "workspace:delete",
    "member:read", "member:write", "member:manage"],
  admin: ["presentation:read", "presentation:write", "presentation:delete", "presentation:export",
    "template:read", "template:write", "template:delete",
    "integration:read", "integration:write",
    "webhook:read", "webhook:write",
    "workspace:read", "workspace:write",
    "member:read", "member:write"],
  editor: ["presentation:read", "presentation:write", "presentation:export",
    "template:read", "template:write",
    "integration:read",
    "webhook:read",
    "workspace:read",
    "member:read"],
  viewer: ["presentation:read", "template:read", "workspace:read", "member:read"],
};

export function PermissionGate({ permission, children, fallback = null }: PermissionGateProps) {
  const provider = useSelector((state: RootState) => state.auth?.provider);
  const currentWsId = useSelector((state: RootState) => state.auth?.currentWorkspaceId);
  const workspaces = useSelector((state: RootState) => state.auth?.workspaces);

  if (provider !== "oidc") {
    return <>{children}</>;
  }

  if (!currentWsId) {
    return <>{children}</>;
  }

  const currentWs = workspaces.find((w) => w.id === currentWsId);
  const role = currentWs?.role || "viewer";
  const permissions = ROLE_PERMISSIONS[role] || [];

  if (permissions.includes(permission)) {
    return <>{children}</>;
  }

  return <>{fallback}</>;
}

export function useWorkspaceRole(): string {
  const currentWsId = useSelector((state: RootState) => state.auth?.currentWorkspaceId);
  const workspaces = useSelector((state: RootState) => state.auth?.workspaces);
  if (!currentWsId) return "viewer";
  const ws = workspaces.find((w) => w.id === currentWsId);
  return ws?.role || "viewer";
}

export function useHasPermission(permission: string): boolean {
  const provider = useSelector((state: RootState) => state.auth?.provider);
  const role = useWorkspaceRole();
  if (provider !== "oidc") return true;
  return (ROLE_PERMISSIONS[role] || []).includes(permission);
}
