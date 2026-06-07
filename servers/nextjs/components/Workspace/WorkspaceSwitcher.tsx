"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSelector, useDispatch } from "react-redux";
import { RootState, AppDispatch } from "@/store/store";
import { setAuthUser, setCurrentWorkspace, setWorkspaces } from "@/store/slices/authSlice";
import { setWorkspaces as setWs, setCurrentWorkspaceId } from "@/store/slices/workspaceSlice";
import { getApiUrl } from "@/utils/api";
import { ChevronDown, Plus, LogOut } from "lucide-react";

interface Workspace {
  id: string;
  name: string;
  slug: string;
  role: string;
}

async function fetchWorkspaces(): Promise<Workspace[]> {
  const res = await fetch(getApiUrl("/api/v1/projects"), { credentials: "include" });
  if (!res.ok) return [];
  return res.json();
}

export function WorkspaceSwitcher() {
  const router = useRouter();
  const dispatch = useDispatch<AppDispatch>();
  const provider = useSelector((state: RootState) => state.auth?.provider);
  const currentWsId = useSelector((state: RootState) => state.auth?.currentWorkspaceId);
  const workspaces = useSelector((state: RootState) => state.auth?.workspaces);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (provider !== "oidc") return;
    fetchWorkspaces().then((list) => {
      dispatch(setWorkspaces(list));
      dispatch(setWs(list));
      if (!currentWsId && list.length > 0) {
        dispatch(setCurrentWorkspace(list[0].id));
        dispatch(setCurrentWorkspaceId(list[0].id));
      }
    });
  }, [provider]);

  if (provider !== "oidc" || workspaces.length === 0) return null;

  const currentWs = workspaces.find((w) => w.id === currentWsId);

  async function handleLogout() {
    await fetch(getApiUrl("/api/v1/oidc/logout"), {
      method: "POST",
      credentials: "include",
    });
    window.location.href = "/";
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-white/80 hover:bg-white/10 transition"
      >
        <span className="h-6 w-6 rounded bg-[#7C51F8] flex items-center justify-center text-[10px] font-semibold text-white shrink-0">
          {(currentWs?.name || "W").charAt(0).toUpperCase()}
        </span>
        <span className="flex-1 truncate font-syne">{currentWs?.name || "Select workspace"}</span>
        <ChevronDown className={`h-4 w-4 shrink-0 transition ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-[#2D2D3A] bg-[#1C1C2A] py-1 shadow-lg">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => {
                  dispatch(setCurrentWorkspace(ws.id));
                  dispatch(setCurrentWorkspaceId(ws.id));
                  setIsOpen(false);
                  router.push(`/projects/${ws.slug}`);
                }}
                className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition ${
                  ws.id === currentWsId
                    ? "bg-[#7C51F8]/20 text-white"
                    : "text-white/70 hover:bg-white/10"
                }`}
              >
                <span className="h-5 w-5 rounded bg-white/20 flex items-center justify-center text-[10px] font-semibold shrink-0">
                  {ws.name.charAt(0).toUpperCase()}
                </span>
                <span className="flex-1 truncate font-syne">{ws.name}</span>
                <span className="text-[10px] text-white/40 uppercase">{ws.role}</span>
              </button>
            ))}
            <div className="border-t border-[#2D2D3A] my-1" />
            <button
              onClick={() => {
                setIsOpen(false);
                router.push("/projects/new");
              }}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-white/70 hover:bg-white/10 transition"
            >
              <Plus className="h-4 w-4" />
              <span className="font-syne">New Workspace</span>
            </button>
            <button
              onClick={handleLogout}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-400/80 hover:bg-white/10 transition"
            >
              <LogOut className="h-4 w-4" />
              <span className="font-syne">Sign out</span>
            </button>
          </div>
        </>
      )}
    </div>
  );
}
