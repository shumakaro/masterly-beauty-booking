import { afterEach, expect, it, vi } from "vitest";
import { bookingKey, forgetBookingKey } from "./api";

afterEach(() => {
  sessionStorage.clear();
  vi.restoreAllMocks();
});
it("keeps an uncertain booking retry stable across module reloads, isolates users and renews after acknowledgement", async () => {
  const first = bookingKey("client-a", "offer", "2030-01-01T10:00:00Z");
  expect(bookingKey("client-b", "offer", "2030-01-01T10:00:00Z")).not.toBe(
    first,
  );
  vi.resetModules();
  const restored = await import("./api");
  expect(restored.bookingKey("client-a", "offer", "2030-01-01T10:00:00Z")).toBe(
    first,
  );
  restored.forgetBookingKey("client-a", "offer", "2030-01-01T10:00:00Z");
  expect(
    restored.bookingKey("client-a", "offer", "2030-01-01T10:00:00Z"),
  ).not.toBe(first);
  forgetBookingKey("client-a", "offer", "2030-01-01T10:00:00Z");
});
it("can retry safely when session storage is unavailable", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  const first = bookingKey("private-mode", "offer", "2030-01-02T10:00:00Z");
  expect(bookingKey("private-mode", "offer", "2030-01-02T10:00:00Z")).toBe(
    first,
  );
});
