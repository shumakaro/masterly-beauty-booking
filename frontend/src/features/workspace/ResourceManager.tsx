import { useEffect, useId, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { usePrivateQuery, useWrite } from "./api";
import { DataPanel, Feedback, Pager } from "./ui";
import { pageNumber } from "./api";
import type { Page } from "../catalog/api";
import { ApiError } from "../../shared/api/client";

export type Row = Record<string, unknown> & { id: string };
export interface Field {
  name: string;
  label: string;
  type?:
    | "text"
    | "textarea"
    | "number"
    | "decimal"
    | "time"
    | "date"
    | "url"
    | "checkbox"
    | "select";
  required?: boolean;
  maxLength?: number;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: string; label: string }[];
  default?: string | number | boolean;
  createOnly?: boolean;
}
export interface ResourceConfig {
  title: string;
  read: string;
  write: string;
  fields: Field[];
  summary: (row: Row) => string;
  description?: string;
  create?: boolean;
  remove?: boolean;
  removeLabel?: string;
  prepare?: (values: Record<string, unknown>) => Record<string, unknown>;
}
export function ResourceForm({
  path,
  method,
  fields,
  initial,
  prepare,
  onSaved,
  autoFocus = false,
}: {
  path: string;
  method: "POST" | "PATCH";
  fields: Field[];
  initial?: Row;
  prepare?: ResourceConfig["prepare"];
  onSaved?: () => void;
  autoFocus?: boolean;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const errorId = useId();
  useEffect(() => {
    if (autoFocus)
      formRef.current
        ?.querySelector<HTMLElement>("input, select, textarea")
        ?.focus();
  }, [autoFocus]);
  const write = useWrite();
  const [saved, setSaved] = useState(false);
  return (
    <form
      ref={formRef}
      className="workspace-form"
      onChange={() => {
        setSaved(false);
        write.reset();
      }}
      onSubmit={async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const data = new FormData(form);
        const values: Record<string, unknown> = {};
        for (const field of fields) {
          if (method === "PATCH" && field.createOnly) continue;
          if (field.type === "checkbox")
            values[field.name] = data.has(field.name);
          else {
            const value = String(data.get(field.name) ?? "").trim();
            if (field.type === "number" && value)
              values[field.name] = Number(value);
            else
              values[field.name] =
                field.name === "photo_url" ? value || null : value;
          }
        }
        try {
          await write.mutateAsync({
            path,
            method,
            body: prepare ? prepare(values) : values,
          });
          setSaved(true);
          if (method === "POST") form.reset();
          onSaved?.();
          if (!onSaved)
            requestAnimationFrame(() =>
              form
                .querySelector<HTMLElement>(
                  method === "POST"
                    ? "input, select, textarea"
                    : "button[type=submit], button:not([type])",
                )
                ?.focus({ preventScroll: true }),
            );
        } catch {
          /* Server error is shown next to the form; values remain editable. */
        }
      }}
    >
      {fields
        .filter((field) => method === "POST" || !field.createOnly)
        .map((field) => {
          const value = initial?.[field.name] ?? field.default ?? "";
          const common = {
            name: field.name,
            required: field.required,
            maxLength: field.maxLength,
            disabled: write.isPending,
            "aria-invalid":
              (write.error instanceof ApiError &&
                write.error.fields.some(
                  (error) =>
                    error.path === field.name ||
                    error.path.endsWith(`.${field.name}`),
                )) ||
              undefined,
            "aria-describedby": write.error ? errorId : undefined,
          };
          return (
            <label
              className={field.type === "checkbox" ? "workspace-checkbox" : ""}
              key={field.name}
            >
              {field.type !== "checkbox" && <span>{field.label}</span>}
              {field.type === "select" ? (
                <select {...common} defaultValue={String(value)}>
                  <option value="">Выберите…</option>
                  {field.options?.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : field.type === "textarea" ? (
                <textarea {...common} defaultValue={String(value)} rows={4} />
              ) : field.type === "checkbox" ? (
                <>
                  <input
                    {...common}
                    type="checkbox"
                    defaultChecked={Boolean(value)}
                  />
                  <span>{field.label}</span>
                </>
              ) : (
                <input
                  {...common}
                  type={
                    field.type === "decimal" ? "number" : (field.type ?? "text")
                  }
                  defaultValue={String(value)}
                  min={field.min}
                  max={field.max}
                  step={
                    field.step ??
                    (field.type === "decimal"
                      ? "0.01"
                      : field.type === "time"
                        ? "900"
                        : undefined)
                  }
                />
              )}
            </label>
          );
        })}
      <Feedback error={write.error} focus id={errorId} />
      {saved && (
        <p className="form-success" role="status">
          Сохранено.
        </p>
      )}
      <button className="button button-dark" disabled={write.isPending}>
        {write.isPending
          ? "Сохраняем…"
          : method === "POST"
            ? "Добавить"
            : "Сохранить изменения"}
      </button>
    </form>
  );
}

function ResourceItem({
  item,
  config,
  onRemoved,
}: {
  item: Row;
  config: ResourceConfig;
  onRemoved: (id: string) => void;
}) {
  const editButton = useRef<HTMLButtonElement>(null);
  const removeButton = useRef<HTMLButtonElement>(null);
  const confirmPanel = useRef<HTMLDivElement>(null);
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const remove = useWrite();
  useEffect(() => {
    if (confirm)
      confirmPanel.current?.querySelector<HTMLElement>("button")?.focus();
  }, [confirm]);
  const closeEditor = () => {
    setEditing(false);
    requestAnimationFrame(() =>
      editButton.current?.focus({ preventScroll: true }),
    );
  };
  return (
    <article className="resource-item" data-resource-id={item.id}>
      <h3>{config.summary(item)}</h3>
      {typeof item.url === "string" && (
        <img
          src={item.url}
          alt={String(item.alt_text ?? "Работа мастера")}
          loading="lazy"
        />
      )}
      {typeof item.text === "string" && <p>{item.text}</p>}
      {!editing && (
        <div className="workspace-actions">
          <button
            ref={editButton}
            className="text-link"
            onClick={() => setEditing(true)}
          >
            Изменить
          </button>
          {config.remove && (
            <button
              ref={removeButton}
              className="text-link"
              onClick={() => setConfirm(true)}
            >
              {config.removeLabel ?? "Удалить"}
            </button>
          )}
        </div>
      )}
      {editing && (
        <>
          <ResourceForm
            path={`${config.write}/${item.id}`}
            method="PATCH"
            fields={config.fields}
            initial={item}
            prepare={config.prepare}
            onSaved={closeEditor}
            autoFocus
          />
          <button className="text-link" onClick={closeEditor}>
            Закрыть редактирование
          </button>
        </>
      )}
      {confirm && (
        <div
          className="confirm-action"
          role="group"
          aria-label="Подтверждение удаления"
          ref={confirmPanel}
          onKeyDown={(event) => {
            if (event.key === "Escape" && !remove.isPending) {
              setConfirm(false);
              removeButton.current?.focus();
            }
          }}
        >
          <p>
            {config.removeLabel === "Отключить"
              ? "Отключить предложение? История посещений сохранится."
              : "Удалить этот объект?"}
          </p>
          <Feedback error={remove.error} focus />
          <div className="workspace-actions">
            <button
              className="button button-outline"
              disabled={remove.isPending}
              onClick={async () => {
                try {
                  await remove.mutateAsync({
                    path: `${config.write}/${item.id}`,
                    method: "DELETE",
                  });
                  setConfirm(false);
                  onRemoved(item.id);
                } catch {
                  /* Feedback above. */
                }
              }}
            >
              Подтвердить
            </button>
            <button
              className="text-link"
              disabled={remove.isPending}
              onClick={() => {
                setConfirm(false);
                removeButton.current?.focus();
              }}
            >
              Оставить
            </button>
          </div>
        </div>
      )}
    </article>
  );
}
export function ResourceManager({ config }: { config: ResourceConfig }) {
  const section = useRef<HTMLElement>(null);
  const [params] = useSearchParams();
  const query = usePrivateQuery<Page<Row>>(
    `${config.read}?page=${pageNumber(params)}&page_size=10`,
  );
  return (
    <section className="workspace-section" ref={section}>
      <h2 tabIndex={-1}>{config.title}</h2>
      {config.description && (
        <p className="workspace-hint">{config.description}</p>
      )}
      {config.create && (
        <details className="create-resource">
          <summary>Добавить</summary>
          <ResourceForm
            path={config.write}
            method="POST"
            fields={config.fields}
            prepare={config.prepare}
          />
        </details>
      )}
      <DataPanel query={query}>
        {(data) => (
          <>
            {data.items.length === 0 && (
              <p className="workspace-state">Пока ничего нет.</p>
            )}
            <div className="resource-list">
              {data.items.map((item) => (
                <ResourceItem
                  item={item}
                  config={config}
                  key={item.id}
                  onRemoved={(id) => {
                    requestAnimationFrame(() => {
                      const target =
                        section.current?.querySelector<HTMLElement>(
                          `[data-resource-id="${id}"] button`,
                        ) ??
                        section.current?.querySelector<HTMLElement>(
                          ".resource-item button, h2",
                        );
                      target?.focus({ preventScroll: true });
                    });
                  }}
                />
              ))}
            </div>
            <Pager data={data} />
          </>
        )}
      </DataPanel>
    </section>
  );
}
