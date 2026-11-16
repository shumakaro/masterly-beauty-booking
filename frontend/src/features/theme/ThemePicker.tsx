import { SunMoon } from "lucide-react";
import { useTheme, type ThemePreference } from "./themeState";
export function ThemePicker() {
  const { preference, setPreference } = useTheme();
  return (
    <label className="theme-picker">
      <SunMoon size={17} aria-hidden="true" />
      <span className="visually-hidden">Цветовая тема</span>
      <select
        value={preference}
        onChange={(event) =>
          setPreference(event.target.value as ThemePreference)
        }
      >
        <option value="system">Авто</option>
        <option value="light">Светлая</option>
        <option value="dark">Темная</option>
      </select>
    </label>
  );
}
