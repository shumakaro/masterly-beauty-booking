import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/authState";
import { homeForRole } from "../features/auth/paths";
import { profileSchema } from "../features/auth/schemas";
import { describeError, updateOwnProfile } from "../shared/api/client";

const labels = {
  CLIENT: "Кабинет клиента",
  MASTER: "Кабинет мастера",
  ADMIN: "Кабинет администратора",
};
export function AccountPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (!user) return null;
  return (
    <main id="main" className="shell account-page section-space">
      <p className="eyebrow">{labels[user.role]}</p>
      <h1>
        Здравствуйте,
        <br />
        <em>{user.display_name}.</em>
      </h1>
      <p className="section-intro">
        Ваш аккаунт подключен. Здесь будут собраны ваши{" "}
        {user.role === "MASTER"
          ? "услуги, расписание и записи клиентов"
          : user.role === "ADMIN"
            ? "инструменты управления платформой"
            : "записи и избранные мастера"}
        .
      </p>
      <section className="account-card" aria-labelledby="account-details">
        <h2 id="account-details">Ваш профиль</h2>
        <dl>
          <div>
            <dt>Имя</dt>
            <dd>{user.display_name}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{user.email}</dd>
          </div>
          <div>
            <dt>Роль</dt>
            <dd>{user.role}</dd>
          </div>
        </dl>
        <Link className="text-link" to="/profile">
          Изменить имя →
        </Link>
      </section>
      <p className="development-note">
        Каталог и онлайн-запись находятся в разработке. Существующие записи не
        имитируются.
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button
        className="button button-outline"
        disabled={busy}
        onClick={async () => {
          setError("");
          setBusy(true);
          try {
            await logout();
            navigate("/login", { replace: true });
          } catch (problem) {
            setError(describeError(problem));
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Выходим…" : "Выйти из аккаунта"}
      </button>
    </main>
  );
}

export function ProfilePage() {
  const { user } = useAuth();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const form = useForm<z.infer<typeof profileSchema>>({
    resolver: zodResolver(profileSchema),
    defaultValues: { display_name: user?.display_name ?? "" },
  });
  if (!user) return null;
  return (
    <main id="main" className="shell account-page section-space">
      <Link className="text-link" to={homeForRole(user.role)}>
        ← В кабинет
      </Link>
      <h1>
        Настройки
        <br />
        <em>профиля.</em>
      </h1>
      <form
        className="profile-form"
        noValidate
        onSubmit={form.handleSubmit(async (values) => {
          setMessage("");
          setError("");
          try {
            await updateOwnProfile(values.display_name);
            setMessage("Имя сохранено.");
          } catch (problem) {
            setError(describeError(problem));
          }
        })}
      >
        <div className="form-field">
          <label htmlFor="profile-name">Ваше имя</label>
          <input
            id="profile-name"
            autoComplete="name"
            {...form.register("display_name")}
            aria-invalid={!!form.formState.errors.display_name}
            aria-describedby="profile-name-error"
          />
          {form.formState.errors.display_name && (
            <p className="field-error" id="profile-name-error">
              {form.formState.errors.display_name.message}
            </p>
          )}
        </div>
        {message && (
          <p className="form-success" role="status">
            {message}
          </p>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button
          className="button button-dark"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? "Сохраняем…" : "Сохранить изменения"}
        </button>
      </form>
    </main>
  );
}
