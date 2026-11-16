import { Navigate, useSearchParams } from "react-router-dom";
export function WorkspaceRedirect({ to, tab }: { to: string; tab: string }) {
  const [params] = useSearchParams();
  const next = new URLSearchParams(params);
  next.set("tab", tab);
  return <Navigate replace to={`${to}?${next}`} />;
}
