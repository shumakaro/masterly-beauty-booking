import { homeForRole } from "./paths";
import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import type { Role } from "../../shared/api/client";
import { useAuth } from "./authState";

export function ProtectedRoute({
  roles,
  children,
}: {
  roles?: Role[];
  children: ReactNode;
}) {
  const { status, user, retry } = useAuth();
  const location = useLocation();
  if (status === "loading")
    return (
      <main id="main" className="shell auth-status" role="status">
        Проверяем сессию…
      </main>
    );
  if (status === "unavailable")
    return (
      <main id="main" className="shell auth-status">
        <h1>Не удалось проверить сессию.</h1>
        <p>Проверьте подключение и повторите попытку.</p>
        <button className="button button-dark" onClick={retry}>
          Повторить
        </button>
      </main>
    );
  if (!user)
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    );
  if (roles && !roles.includes(user.role))
    return <Navigate to={homeForRole(user.role)} replace />;
  return children;
}
