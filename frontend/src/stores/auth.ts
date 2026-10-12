import { create } from "zustand";
import { api, setTokens } from "../lib/api";

export type AuthUser = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  membership_status: string;
  system_role: string;
  is_active: boolean;
  permissions: string[];
};

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  user: AuthUser;
};

type Theme = "light" | "dark";

type AuthState = {
  user: AuthUser | null;
  theme: Theme;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadMe: () => Promise<void>;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  can: (permission: string) => boolean;
};

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
}

function initialTheme(): Theme {
  const stored = localStorage.getItem("bierkasse7.theme") as Theme | null;
  if (stored) return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  theme: initialTheme(),
  ready: false,

  login: async (email, password) => {
    const res = await api.post<LoginResponse>("/auth/login", { email, password }, { auth: false });
    setTokens(res.access_token, res.refresh_token);
    set({ user: res.user });
  },

  logout: () => {
    setTokens(null, null);
    set({ user: null });
  },

  loadMe: async () => {
    try {
      const user = await api.get<AuthUser>("/auth/me");
      set({ user, ready: true });
    } catch {
      set({ user: null, ready: true });
    }
  },

  setTheme: (theme) => {
    localStorage.setItem("bierkasse7.theme", theme);
    applyTheme(theme);
    set({ theme });
  },

  toggleTheme: () => {
    const next: Theme = get().theme === "dark" ? "light" : "dark";
    get().setTheme(next);
  },

  can: (permission) => {
    const user = get().user;
    return !!user && (user.permissions.includes(permission) || user.permissions.includes("read:all"));
  },
}));

applyTheme(initialTheme());
