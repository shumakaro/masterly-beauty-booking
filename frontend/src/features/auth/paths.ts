import type { Role } from "../../shared/api/client";
export function homeForRole(role: Role) {
  return role === "ADMIN"
    ? "/admin"
    : role === "MASTER"
      ? "/master/dashboard"
      : "/dashboard";
}
export function afterLogin(role: Role, from: unknown) {
  if (
    typeof from === "string" &&
    from.startsWith("/") &&
    !from.startsWith("//") &&
    !from.includes("\\") &&
    !/^\/(login|register)([?#]|$)/.test(from)
  )
    return from;
  return homeForRole(role);
}
