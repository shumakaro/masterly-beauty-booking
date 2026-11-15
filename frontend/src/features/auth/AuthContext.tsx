import { AuthContext, type AuthStatus } from "./authState";
import type { User } from "../../shared/api/client";
import { useEffect, useState, type ReactNode } from "react";
import {
  ApiError,
  loginSession,
  logoutSession,
  refreshSession,
  subscribeSession,
} from "../../shared/api/client";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    const unsubscribe = subscribeSession((next) => {
      if (active) {
        setUser(next);
        setStatus(next ? "authenticated" : "guest");
      }
    });
    refreshSession().catch((error) => {
      if (active)
        setStatus(
          error instanceof ApiError && error.status === 401
            ? "guest"
            : "unavailable",
        );
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, [attempt]);
  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        login: async (email, password) => {
          const data = await loginSession(email, password);
          setUser(data.user);
          setStatus("authenticated");
          return data.user;
        },
        logout: async () => {
          await logoutSession();
          setUser(null);
          setStatus("guest");
        },
        retry: () => {
          setStatus("loading");
          setAttempt((value) => value + 1);
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
