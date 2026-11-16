import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ThemeProvider } from "./ThemeProvider";
import { ThemePicker } from "./ThemePicker";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
});
it("follows device changes only in system mode and persists an explicit choice", () => {
  const listeners = new Set<() => void>();
  const media = {
    matches: false,
    addEventListener: (_: string, callback: () => void) =>
      listeners.add(callback),
    removeEventListener: (_: string, callback: () => void) =>
      listeners.delete(callback),
  };
  vi.spyOn(window, "matchMedia").mockReturnValue(
    media as unknown as MediaQueryList,
  );
  render(
    <ThemeProvider>
      <ThemePicker />
    </ThemeProvider>,
  );
  expect(document.documentElement.dataset.theme).toBe("light");
  act(() => {
    media.matches = true;
    listeners.forEach((callback) => callback());
  });
  expect(document.documentElement.dataset.theme).toBe("dark");
  fireEvent.change(screen.getByRole("combobox", { name: "Цветовая тема" }), {
    target: { value: "light" },
  });
  expect(localStorage.getItem("masterly:theme")).toBe("light");
  act(() => listeners.forEach((callback) => callback()));
  expect(document.documentElement.dataset.theme).toBe("light");
});
it("still allows changing theme when browser storage is blocked", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  render(
    <ThemeProvider>
      <ThemePicker />
    </ThemeProvider>,
  );
  fireEvent.change(screen.getByRole("combobox", { name: "Цветовая тема" }), {
    target: { value: "dark" },
  });
  expect(document.documentElement.dataset.theme).toBe("dark");
});
