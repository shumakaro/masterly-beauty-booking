import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "./App";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ error: { message: "Unauthorized" } }),
      }),
  );
  window.history.replaceState({}, "", "/");
  vi.stubGlobal("scrollTo", vi.fn());
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("lets visitors explore a direction without pretending to make a booking", () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: /Ногти/ }));
  expect(screen.getByText(/Лаконичный нюд/)).toBeInTheDocument();
  expect(screen.getByText(/Онлайн-запись откроется/)).toBeInTheDocument();
});

it("provides a real recovery route for an unknown URL", () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ error: { message: "Unauthorized" } }),
      }),
  );
  window.history.replaceState({}, "", "/unknown-page");
  render(<App />);
  fireEvent.click(screen.getByRole("link", { name: /Вернуться на главную/ }));
  expect(
    screen.getByRole("heading", { level: 1, name: /Красота/ }),
  ).toBeInTheDocument();
});
