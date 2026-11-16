import { useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../auth/authState";
import { type Master, type Page, money } from "../catalog/api";
import { usePrivateQuery, usePrivateOptions, useWrite } from "./api";
import { DataPanel, Feedback, Pager } from "./ui";
import { pageNumber } from "./api";

export function FavoriteButton({ masterId }: { masterId: string }) {
  const { user } = useAuth();
  const query = usePrivateOptions<Master>("favorites", user?.role === "CLIENT");
  const write = useWrite();
  if (user?.role !== "CLIENT") return null;
  const selected =
    query.data?.some((master) => master.id === masterId) ?? false;
  return (
    <div className="favorite-control">
      <Feedback error={write.error ?? query.error} />
      {query.isError ? (
        <button className="text-link" onClick={() => void query.refetch()}>
          Повторить загрузку избранного
        </button>
      ) : (
        <button
          className="button button-outline"
          aria-pressed={selected}
          disabled={query.isPending || write.isPending}
          onClick={() => {
            void write
              .mutateAsync({
                path: `favorites/${masterId}`,
                method: selected ? "DELETE" : "PUT",
              })
              .catch(() => undefined);
          }}
        >
          {selected ? "В избранном · убрать" : "В избранное"}
        </button>
      )}
    </div>
  );
}
function FavoriteItem({ master }: { master: Master }) {
  const write = useWrite();
  return (
    <article className="resource-item">
      <h3>
        <Link to={`/masters/${master.id}`}>{master.display_name}</Link>
      </h3>
      <p>
        {master.price_from === null
          ? "Услуги пока не добавлены"
          : `от ${money(master.price_from)}`}
      </p>
      <Feedback error={write.error} />
      <div className="workspace-actions">
        <Link className="text-link" to={`/masters/${master.id}`}>
          Профиль и услуги →
        </Link>
        <button
          className="text-link"
          disabled={write.isPending}
          onClick={() =>
            void write
              .mutateAsync({ path: `favorites/${master.id}`, method: "DELETE" })
              .catch(() => undefined)
          }
        >
          Убрать из избранного
        </button>
      </div>
    </article>
  );
}
export function Favorites() {
  const [params] = useSearchParams();
  const query = usePrivateQuery<Page<Master>>(
    `favorites?page=${pageNumber(params)}&page_size=10`,
  );
  return (
    <section className="workspace-section">
      <h2>Избранные мастера</h2>
      <DataPanel query={query}>
        {(data) => (
          <>
            {data.items.length === 0 && (
              <p className="workspace-state">
                Здесь появятся мастера, которых вы добавите в избранное.
              </p>
            )}
            {data.items.map((master) => (
              <FavoriteItem key={master.id} master={master} />
            ))}
            <Pager data={data} />
          </>
        )}
      </DataPanel>
    </section>
  );
}
