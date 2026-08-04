import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError, api } from "./api/client";
import type { User } from "./api/types";

const TOKEN_KEY = "solvix_token";

interface AuthState {
  token: string | null;
  user: User | null;
  loading: boolean;
  login: (token: string) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY),
  );
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const login = useCallback((next: string) => {
    localStorage.setItem(TOKEN_KEY, next);
    setToken(next);
  }, []);

  const loadUser = useCallback(async () => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api.me(token));
    } catch (err) {
      // A stored token that the backend rejects is worse than no token: it
      // leaves the app stuck on a dashboard that cannot load anything.
      if (err instanceof ApiError && err.status === 401) logout();
      else setUser(null);
    } finally {
      setLoading(false);
    }
  }, [token, logout]);

  useEffect(() => {
    setLoading(true);
    void loadUser();
  }, [loadUser]);

  const value = useMemo(
    () => ({ token, user, loading, login, logout, refreshUser: loadUser }),
    [token, user, loading, login, logout, loadUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
