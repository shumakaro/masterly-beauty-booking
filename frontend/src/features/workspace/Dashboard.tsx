import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/authState";
import { BookingsList, MyReviews } from "./Bookings";
import { Favorites } from "./Favorites";
import { AdminManagement, MasterManagement } from "./Management";
import "./workspace.css";
import { Overview } from "./Overview";

const tabs = {
  CLIENT: [
    ["bookings", "Посещения"],
    ["favorites", "Избранное"],
    ["reviews", "Мои отзывы"],
  ],
  MASTER: [
    ["bookings", "Посещения"],
    ["business-profile", "Профиль мастера"],
    ["offers", "Мои услуги"],
    ["schedules", "Рабочая неделя"],
    ["exceptions", "Особые даты"],
    ["portfolio", "Портфолио"],
  ],
  ADMIN: [
    ["bookings", "Посещения"],
    ["users", "Пользователи"],
    ["masters", "Мастера"],
    ["categories", "Направления"],
    ["services", "Услуги"],
  ],
};
export function Dashboard() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  if (!user) return null;
  const options = tabs[user.role];
  const tab = options.some(([key]) => key === params.get("tab"))
    ? params.get("tab")!
    : "bookings";
  return (
    <div className="dashboard-workspace">
      <Overview />
      <nav className="workspace-tabs" aria-label="Разделы кабинета">
        {options.map(([key, label]) => (
          <Link
            key={key}
            to={`?tab=${key}`}
            aria-current={tab === key ? "page" : undefined}
          >
            {label}
          </Link>
        ))}
      </nav>
      <div key={`${user.id}:${tab}`}>
        {tab === "bookings" ? (
          <BookingsList />
        ) : user.role === "CLIENT" ? (
          tab === "favorites" ? (
            <Favorites />
          ) : (
            <MyReviews />
          )
        ) : user.role === "MASTER" ? (
          <MasterManagement tab={tab} />
        ) : (
          <AdminManagement tab={tab} />
        )}
      </div>
    </div>
  );
}
