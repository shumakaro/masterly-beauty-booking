import { createContext, useContext } from "react";
export type ThemePreference = "system" | "light" | "dark";
export interface ThemeState {
  preference: ThemePreference;
  setPreference: (value: ThemePreference) => void;
}
export const ThemeContext = createContext<ThemeState | null>(null);
export function readTheme(): ThemePreference {
  try {
    const value = localStorage.getItem("masterly:theme");
    if (value === "light" || value === "dark") return value;
  } catch {
    /* Optional browser storage. */
  }
  return "system";
}
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("ThemeProvider is required");
  return context;
}
