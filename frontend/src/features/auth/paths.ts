import type { Role } from "../../shared/api/client";
export function homeForRole(role: Role) {
  return role === "ADMIN"
    ? "/admin"
    : role === "MASTER"
      ? "/master/dashboard"
      : "/dashboard";
}
