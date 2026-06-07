import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  is_admin: boolean;
}

export interface AuthState {
  provider: string | null;
  isAuthenticated: boolean;
  user: AuthUser | null;
  currentWorkspaceId: string | null;
  workspaces: Array<{
    id: string;
    name: string;
    slug: string;
    role: string;
  }>;
}

const initialState: AuthState = {
  provider: null,
  isAuthenticated: false,
  user: null,
  currentWorkspaceId: null,
  workspaces: [],
};

export const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setAuthUser(state, action: PayloadAction<{ provider: string; user: AuthUser }>) {
      state.provider = action.payload.provider;
      state.isAuthenticated = true;
      state.user = action.payload.user;
    },
    clearAuth(state) {
      state.provider = null;
      state.isAuthenticated = false;
      state.user = null;
      state.currentWorkspaceId = null;
      state.workspaces = [];
    },
    setCurrentWorkspace(state, action: PayloadAction<string | null>) {
      state.currentWorkspaceId = action.payload;
    },
    setWorkspaces(state, action: PayloadAction<AuthState["workspaces"]>) {
      state.workspaces = action.payload;
    },
  },
});

export const { setAuthUser, clearAuth, setCurrentWorkspace, setWorkspaces } = authSlice.actions;
export default authSlice.reducer;
