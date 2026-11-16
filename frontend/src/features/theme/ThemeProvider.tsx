import { useEffect, useState, type ReactNode } from "react";
import { ThemeContext, readTheme, type ThemePreference } from "./themeState";
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setValue] = useState<ThemePreference>(readTheme);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      document.documentElement.dataset.theme =
        preference === "system"
          ? media.matches
            ? "dark"
            : "light"
          : preference;
    };
    const synchronize = (event: StorageEvent) => {
      if (event.key === "masterly:theme" || event.key === null)
        setValue(readTheme());
    };
    apply();
    media.addEventListener("change", apply);
    window.addEventListener("storage", synchronize);
    return () => {
      media.removeEventListener("change", apply);
      window.removeEventListener("storage", synchronize);
    };
  }, [preference]);
  return (
    <ThemeContext.Provider
      value={{
        preference,
        setPreference: (value) => {
          setValue(value);
          try {
            localStorage.setItem("masterly:theme", value);
          } catch {
            /* The preference remains usable in memory. */
          }
        },
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}
