import { expect, it } from "vitest";
import { registrationSchema } from "./schemas";
const valid = {
  email: "test@example.com",
  display_name: "Test",
  role: "CLIENT",
  password: "MyStrongPassword123",
  confirm_password: "MyStrongPassword123",
};
it("requires matching passwords", () => {
  const result = registrationSchema.safeParse({
    ...valid,
    confirm_password: "different",
  });
  expect(result.success).toBe(false);
  if (!result.success)
    expect(result.error.issues[0].path).toEqual(["confirm_password"]);
});
it("checks UTF-8 bytes without truncating Cyrillic passwords", () => {
  const password = "я".repeat(40);
  expect(
    registrationSchema.safeParse({
      ...valid,
      password,
      confirm_password: password,
    }).success,
  ).toBe(false);
});
it("rejects self-assigned ADMIN", () => {
  expect(
    registrationSchema.safeParse({ ...valid, role: "ADMIN" }).success,
  ).toBe(false);
});
