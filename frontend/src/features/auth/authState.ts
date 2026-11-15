import { createContext, useContext } from "react";
import type { User } from "../../shared/api/client";
export type AuthStatus = "loading" | "authenticated" | "guest" | "unavailable";
interface AuthState {
  user: User | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  retry: () => void;
}
export const AuthContext = createContext<AuthState | null>(null);

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}
