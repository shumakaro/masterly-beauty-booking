import { useAuth } from "../auth/authState";
import { money } from "../catalog/api";
import { usePrivateQuery } from "./api";
import { DataPanel } from "./ui";

interface OverviewData {
  total: number;
  confirmed: number;
  upcoming: number;
  completed: number;
  cancelled: number;
  completed_value: string;
  currency: "KZT";
}
interface AdminOverview {
  users: number;
  masters: number;
  bookings: number;
}
export function Overview() {
  const { user } = useAuth();
  const query = usePrivateQuery<OverviewData>(
    "overview",
    user?.role !== "ADMIN",
  );
  const admin = usePrivateQuery<AdminOverview>(
    "admin/overview",
    user?.role === "ADMIN",
  );
  return (
    <section className="overview-section" aria-labelledby="overview-heading">
      <h2 id="overview-heading">Обзор</h2>
      {user?.role === "ADMIN" ? (
        <DataPanel query={admin}>
          {(data) => (
            <dl className="overview-grid">
              <div>
                <dt>Аккаунтов</dt>
                <dd>{data.users}</dd>
              </div>
              <div>
                <dt>Профилей мастеров</dt>
                <dd>{data.masters}</dd>
              </div>
              <div>
                <dt>Всего посещений</dt>
                <dd>{data.bookings}</dd>
              </div>
            </dl>
          )}
        </DataPanel>
      ) : (
        <DataPanel query={query}>
          {(data) => (
            <>
              <dl className="overview-grid">
                <div>
                  <dt>Всего посещений</dt>
                  <dd>{data.total}</dd>
                </div>
                <div>
                  <dt>Предстоящие</dt>
                  <dd>{data.upcoming}</dd>
                </div>
                <div>
                  <dt>Подтверждены</dt>
                  <dd>{data.confirmed}</dd>
                </div>
                <div>
                  <dt>Завершены</dt>
                  <dd>{data.completed}</dd>
                </div>
                <div>
                  <dt>Отменены</dt>
                  <dd>{data.cancelled}</dd>
                </div>
                <div>
                  <dt>Стоимость завершенных услуг</dt>
                  <dd>{money(data.completed_value)}</dd>
                </div>
              </dl>
              <p className="workspace-hint">
                Стоимость по сохраненным условиям посещений. Оплата через
                платформу не проводится.
              </p>
            </>
          )}
        </DataPanel>
      )}
    </section>
  );
}
