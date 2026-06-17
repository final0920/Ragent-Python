import { create } from "zustand";
import { api, getToken, setToken } from "../api";

interface AuthState {
  token: string;
  username: string;
  role: string;
  login: (u: string, p: string) => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  token: getToken(),
  username: localStorage.getItem("username") || "",
  role: localStorage.getItem("role") || "",
  login: async (u, p) => {
    const r = await api.login(u, p);
    setToken(r.token);
    localStorage.setItem("username", r.username);
    localStorage.setItem("role", r.role);
    set({ token: r.token, username: r.username, role: r.role });
  },
  logout: () => {
    setToken("");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    set({ token: "", username: "", role: "" });
  },
}));
