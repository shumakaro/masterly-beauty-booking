import { useEffect, useRef, type ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, describeError } from "../../shared/api/client";
import type { Page } from "../catalog/api";
import { LoadingState } from "../../shared/ui/LoadingState";

export function Feedback({
  error,
  focus = false,
  id,
}: {
  error: unknown;
  focus?: boolean;
  id?: string;
}) {
  const target = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (error && focus) target.current?.focus();
  }, [error, focus]);
  return error ? (
    <div className="form-error" role="alert" id={id} ref={target} tabIndex={-1}>
      <p>{describeError(error)}</p>
      {error instanceof ApiError && error.fields.length > 0 && (
        <ul>
          {error.fields.map((field, index) => (
            <li key={index}>{field.message}</li>
          ))}
        </ul>
      )}
    </div>
  ) : null;
}
export function DataPanel<T>({
  query,
  children,
}: {
  query: UseQueryResult<T, Error>;
  children: (data: T) => ReactNode;
}) {
  if (query.isPending)
    return <LoadingState label="Загружаем…" className="workspace-state" />;
  if (query.isError)
    return (
      <div className="workspace-state">
        <Feedback error={query.error} />
        <button
          className="button button-outline"
          onClick={() => void query.refetch()}
        >
          Повторить загрузку
        </button>
      </div>
    );
  return children(query.data);
}
export function Pager({ data }: { data: Page<unknown> }) {
  const [params] = useSearchParams();
  const last = Math.max(1, Math.ceil(data.total / data.page_size));
  const url = (page: number) => {
    const next = new URLSearchParams(params);
    next.set("page", String(page));
    return `?${next}`;
  };
  if (last === 1 && data.page === 1) return null;
  return (
    <nav className="catalog-pagination" aria-label="Страницы кабинета">
      {data.page > 1 && <Link to={url(data.page - 1)}>← Назад</Link>}
      <span>
        Страница {data.page} из {last}
      </span>
      {data.page < last && <Link to={url(data.page + 1)}>Далее →</Link>}
      {data.page > last && <Link to={url(1)}>К первой странице</Link>}
    </nav>
  );
}
