import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { z } from "zod";
import { ArrowRight, Eye, EyeOff } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../features/auth/authState";
import { afterLogin, homeForRole } from "../../features/auth/paths";
import { loginSchema, registrationSchema } from "../../features/auth/schemas";
import {
  ApiError,
  describeError,
  requestJson,
  type User,
} from "../../shared/api/client";

function PasswordField({
  id,
  label,
  error,
  registration,
  ...input
}: {
  id: string;
  label: string;
  error?: string;
  registration?: boolean;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      <div className="password-control">
        <input
          {...input}
          id={id}
          type={visible ? "text" : "password"}
          autoComplete={registration ? "new-password" : "current-password"}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
        />
        <button
          type="button"
          className="password-toggle"
          aria-label={visible ? `Скрыть: ${label}` : `Показать: ${label}`}
          aria-pressed={visible}
          onClick={() => setVisible(!visible)}
        >
          {visible ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
      {error && (
        <p id={`${id}-error`} className="field-error">
          {error}
        </p>
      )}
    </div>
  );
}

function AuthLayout({
  register,
  children,
}: {
  register?: boolean;
  children: React.ReactNode;
}) {
  return (
    <main id="main" className="auth-layout shell">
      <aside className="auth-editorial">
        <img
          src="/images/beauty-editorial.jpg"
          alt="Укладка волос: редакционный кадр"
          width="1200"
          height="1500"
        />
        <div>
          <p className="eyebrow">MASTERLY / YOUR BEAUTY RITUAL</p>
          <h2>
            Ваше время.
            <br />
            <em>Ваш маленький ритуал.</em>
          </h2>
          <p>Забота о себе начинается с простых решений.</p>
        </div>
      </aside>
      <section className="auth-panel" aria-labelledby="auth-title">
        <p className="eyebrow">
          {register ? "Первый шаг к своему ритму" : "Рады видеть вас снова"}
        </p>
        <h1 id="auth-title">
          {register ? (
            <>
              Начните
              <br />
              <em>с себя.</em>
            </>
          ) : (
            <>
              С возвращением
              <br />
              <em>в MASTERLY.</em>
            </>
          )}
        </h1>
        {children}
      </section>
    </main>
  );
}

export function LoginPage() {
  const auth = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const form = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email:
        typeof location.state?.email === "string" ? location.state.email : "",
      password: "",
    },
  });
  if (auth.user)
    return (
      <Navigate to={afterLogin(auth.user.role, location.state?.from)} replace />
    );
  return (
    <AuthLayout>
      <p className="auth-intro">Войдите, чтобы управлять своим профилем.</p>
      {location.state?.registered && (
        <p className="form-success" role="status">
          Аккаунт создан. Войдите с вашим email и паролем.
        </p>
      )}
      <form
        noValidate
        onSubmit={form.handleSubmit(async (values) => {
          setError("");
          try {
            const user = await auth.login(values.email, values.password);
            navigate(afterLogin(user.role, location.state?.from), {
              replace: true,
            });
          } catch (problem) {
            setError(describeError(problem));
          }
        })}
      >
        <div className="form-field">
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            {...form.register("email")}
            aria-invalid={!!form.formState.errors.email}
            aria-describedby={
              form.formState.errors.email ? "login-email-error" : undefined
            }
          />
          {form.formState.errors.email && (
            <p id="login-email-error" className="field-error">
              {form.formState.errors.email.message}
            </p>
          )}
        </div>
        <PasswordField
          id="login-password"
          label="Пароль"
          {...form.register("password")}
          error={form.formState.errors.password?.message}
        />
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button
          className="button button-dark form-submit"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? "Входим…" : "Войти"}
          <ArrowRight size={18} />
        </button>
      </form>
      <p className="auth-switch">
        Впервые здесь?{" "}
        <Link to="/register" state={{ from: location.state?.from }}>
          Создать аккаунт
        </Link>
      </p>
    </AuthLayout>
  );
}

export function RegisterPage() {
  const auth = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const form = useForm<z.infer<typeof registrationSchema>>({
    resolver: zodResolver(registrationSchema),
    defaultValues: {
      email: "",
      display_name: "",
      password: "",
      confirm_password: "",
      role: "CLIENT",
    },
  });
  if (auth.user) return <Navigate to={homeForRole(auth.user.role)} replace />;
  return (
    <AuthLayout register>
      <p className="auth-intro">
        Выберите, как вы хотите пользоваться платформой.
      </p>
      <form
        noValidate
        onSubmit={form.handleSubmit(async (values) => {
          setError("");
          try {
            await requestJson<User>("auth/register", {
              method: "POST",
              body: {
                email: values.email,
                password: values.password,
                display_name: values.display_name,
                role: values.role,
              },
            });
            navigate("/login", {
              replace: true,
              state: {
                registered: true,
                email: values.email,
                from: location.state?.from,
              },
            });
          } catch (problem) {
            setError(describeError(problem));
            if (problem instanceof ApiError)
              for (const field of problem.fields) {
                if (
                  ["email", "display_name", "password", "role"].includes(
                    field.path,
                  )
                )
                  form.setError(
                    field.path as
                      "email" | "display_name" | "password" | "role",
                    { message: field.message },
                  );
              }
          }
        })}
      >
        <fieldset className="role-selector">
          <legend>Тип аккаунта</legend>
          <label>
            <input type="radio" value="CLIENT" {...form.register("role")} />
            <span>Я клиент</span>
          </label>
          <label>
            <input type="radio" value="MASTER" {...form.register("role")} />
            <span>Я мастер</span>
          </label>
        </fieldset>
        <div className="form-field">
          <label htmlFor="register-name">Ваше имя</label>
          <input
            id="register-name"
            autoComplete="name"
            {...form.register("display_name")}
            aria-invalid={!!form.formState.errors.display_name}
            aria-describedby={
              form.formState.errors.display_name
                ? "register-name-error"
                : undefined
            }
          />
          {form.formState.errors.display_name && (
            <p id="register-name-error" className="field-error">
              {form.formState.errors.display_name.message}
            </p>
          )}
        </div>
        <div className="form-field">
          <label htmlFor="register-email">Email</label>
          <input
            id="register-email"
            type="email"
            autoComplete="email"
            {...form.register("email")}
            aria-invalid={!!form.formState.errors.email}
            aria-describedby={
              form.formState.errors.email ? "register-email-error" : undefined
            }
          />
          {form.formState.errors.email && (
            <p id="register-email-error" className="field-error">
              {form.formState.errors.email.message}
            </p>
          )}
        </div>
        <PasswordField
          id="register-password"
          label="Пароль"
          registration
          {...form.register("password")}
          error={form.formState.errors.password?.message}
        />
        <p className="form-hint">
          От 10 символов, не более 72 байт UTF-8. Пароль не обрезается.
        </p>
        <PasswordField
          id="register-confirm"
          label="Повторите пароль"
          registration
          {...form.register("confirm_password")}
          error={form.formState.errors.confirm_password?.message}
        />
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button
          className="button button-dark form-submit"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? "Создаем аккаунт…" : "Создать аккаунт"}
          <ArrowRight size={18} />
        </button>
      </form>
      <p className="auth-switch">
        Уже есть аккаунт? <Link to="/login">Войти</Link>
      </p>
    </AuthLayout>
  );
}
