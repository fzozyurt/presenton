import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface WorkspaceSummary {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  created_by: string;
  role: string;
}

export interface WorkspaceState {
  workspaces: WorkspaceSummary[];
  currentWorkspaceId: string | null;
  isLoading: boolean;
}

const initialState: WorkspaceState = {
  workspaces: [],
  currentWorkspaceId: null,
  isLoading: false,
};

export const workspaceSlice = createSlice({
  name: "workspace",
  initialState,
  reducers: {
    setWorkspaces(state, action: PayloadAction<WorkspaceSummary[]>) {
      state.workspaces = action.payload;
    },
    addWorkspace(state, action: PayloadAction<WorkspaceSummary>) {
      state.workspaces.push(action.payload);
    },
    removeWorkspace(state, action: PayloadAction<string>) {
      state.workspaces = state.workspaces.filter((w) => w.id !== action.payload);
    },
    setCurrentWorkspaceId(state, action: PayloadAction<string | null>) {
      state.currentWorkspaceId = action.payload;
    },
    setWorkspacesLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
  },
});

export const {
  setWorkspaces,
  addWorkspace,
  removeWorkspace,
  setCurrentWorkspaceId,
  setWorkspacesLoading,
} = workspaceSlice.actions;
export default workspaceSlice.reducer;
