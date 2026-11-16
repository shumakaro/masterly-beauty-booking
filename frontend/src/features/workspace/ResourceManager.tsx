import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { usePrivateQuery, useWrite } from "./api";
import { DataPanel, Feedback, Pager } from "./ui";
import { pageNumber } from "./api";
import type { Page } from "../catalog/api";

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
}: {
  path: string;
  method: "POST" | "PATCH";
  fields: Field[];
  initial?: Row;
  prepare?: ResourceConfig["prepare"];
  onSaved?: () => void;
}) {
  const write = useWrite();
  const [saved, setSaved] = useState(false);
  return (
    <form
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
            else values[field.name] = value;
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
      <Feedback error={write.error} />
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

function ResourceItem({ item, config }: { item: Row; config: ResourceConfig }) {
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const remove = useWrite();
  return (
    <article className="resource-item">
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
          <button className="text-link" onClick={() => setEditing(true)}>
            Изменить
          </button>
          {config.remove && (
            <button className="text-link" onClick={() => setConfirm(true)}>
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
            onSaved={() => setEditing(false)}
          />
          <button className="text-link" onClick={() => setEditing(false)}>
            Закрыть редактирование
          </button>
        </>
      )}
      {confirm && (
        <div
          className="confirm-action"
          role="group"
          aria-label="Подтверждение удаления"
        >
          <p>
            {config.removeLabel === "Отключить"
              ? "Отключить предложение? История посещений сохранится."
              : "Удалить этот объект?"}
          </p>
          <Feedback error={remove.error} />
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
              onClick={() => setConfirm(false)}
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
  const [params] = useSearchParams();
  const query = usePrivateQuery<Page<Row>>(
    `${config.read}?page=${pageNumber(params)}&page_size=10`,
  );
  return (
    <section className="workspace-section">
      <h2>{config.title}</h2>
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
                <ResourceItem item={item} config={config} key={item.id} />
              ))}
            </div>
            <Pager data={data} />
          </>
        )}
      </DataPanel>
    </section>
  );
}
