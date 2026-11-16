import { AuthProvider } from "./features/auth/AuthContext";
import { useAuth } from "./features/auth/authState";
import { ProtectedRoute } from "./features/auth/ProtectedRoute";
import { homeForRole } from "./features/auth/paths";
import { LoginPage, RegisterPage } from "./pages/auth/AuthPages";
import { lazy, Suspense, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  Check,
  ChevronRight,
  Flower2,
  Heart,
  Menu,
  Scissors,
  Sparkles,
  X,
} from "lucide-react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Brand } from "./shared/ui/Brand";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MasterPage, MastersPage, ServicesPage } from "./pages/CatalogPages";
import { WorkspaceRedirect } from "./features/workspace/WorkspaceRedirect";
import { ThemeProvider } from "./features/theme/ThemeProvider";
import { ThemePicker } from "./features/theme/ThemePicker";
import { PagePosition } from "./shared/ui/PagePosition";
import { ViewportEffects } from "./shared/ui/ViewportEffects";
import { LoadingState } from "./shared/ui/LoadingState";

const AccountPage = lazy(() =>
  import("./pages/AccountPage").then((module) => ({
    default: module.AccountPage,
  })),
);
const ProfilePage = lazy(() =>
  import("./pages/AccountPage").then((module) => ({
    default: module.ProfilePage,
  })),
);
const BookingPage = lazy(() =>
  import("./pages/BookingPage").then((module) => ({
    default: module.BookingPage,
  })),
);
const BookingDetailsPage = lazy(() =>
  import("./features/workspace/Bookings").then((module) => ({
    default: module.BookingDetailsPage,
  })),
);

const queryClient = new QueryClient();

const currentYear = new Date().getFullYear();
const workspaceRoutes = [
  { path: "/bookings", role: "CLIENT", to: "/dashboard", tab: "bookings" },
  { path: "/favorites", role: "CLIENT", to: "/dashboard", tab: "favorites" },
  {
    path: "/master/services",
    role: "MASTER",
    to: "/master/dashboard",
    tab: "offers",
  },
  {
    path: "/master/schedule",
    role: "MASTER",
    to: "/master/dashboard",
    tab: "schedules",
  },
  {
    path: "/master/bookings",
    role: "MASTER",
    to: "/master/dashboard",
    tab: "bookings",
  },
  {
    path: "/master/profile",
    role: "MASTER",
    to: "/master/dashboard",
    tab: "business-profile",
  },
  { path: "/admin/users", role: "ADMIN", to: "/admin", tab: "users" },
  { path: "/admin/masters", role: "ADMIN", to: "/admin", tab: "masters" },
  { path: "/admin/bookings", role: "ADMIN", to: "/admin", tab: "bookings" },
] as const;

const categories = [
  {
    name: "Волосы",
    icon: Scissors,
    description: "Стрижки, окрашивание и уход",
    detail:
      "От нового силуэта до бережного ухода. В профиле мастера собраны услуги, длительность и стоимость.",
  },
  {
    name: "Ногти",
    icon: Sparkles,
    description: "Маникюр и педикюр",
    detail:
      "Лаконичный нюд или яркий акцент. Выберите технику и посмотрите портфолио перед записью.",
  },
  {
    name: "Макияж",
    icon: Heart,
    description: "Образы для особенных моментов",
    detail:
      "Подчеркнуть свое, попробовать новое. Дневные и вечерние образы, подготовка к важному событию.",
  },
  {
    name: "Уход",
    icon: Flower2,
    description: "Лицо, тело и восстановление",
    detail:
      "Время замедлиться. Уходовые процедуры и массаж с понятной информацией об услуге и специалисте.",
  },
];

function Header() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  const navigation = useRef<HTMLElement>(null);
  return (
    <header
      className="site-header shell"
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          setOpen(false);
          toggle.current?.focus();
        }
      }}
      onBlur={(event) => {
        if (
          event.relatedTarget &&
          !event.currentTarget.contains(event.relatedTarget)
        )
          setOpen(false);
      }}
      onClick={(event) => {
        if ((event.target as Element).closest("a")) setOpen(false);
      }}
    >
      <Brand />
      <ThemePicker />
      <button
        ref={toggle}
        className="menu-toggle icon-button"
        aria-label={open ? "Закрыть меню" : "Открыть меню"}
        aria-expanded={open}
        aria-controls="navigation"
        onClick={() => {
          setOpen(!open);
          if (!open)
            requestAnimationFrame(() =>
              navigation.current?.querySelector("a")?.focus(),
            );
        }}
      >
        {open ? <X /> : <Menu />}
      </button>
      <nav
        ref={navigation}
        id="navigation"
        className={open ? "navigation open" : "navigation"}
        aria-label="Основная навигация"
      >
        <Link to="/masters" onClick={() => setOpen(false)}>
          Мастера
        </Link>
        <Link to="/services" onClick={() => setOpen(false)}>
          Услуги
        </Link>
        <Link to="/brand">Стиль MASTERLY</Link>
        <Link to={user ? homeForRole(user.role) : "/login"}>
          {user ? "Мой кабинет" : "Войти"} <ArrowRight size={15} />
        </Link>
      </nav>
    </header>
  );
}

function EditorialImage({
  src,
  alt,
  className = "",
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  return failed ? (
    <div className={`image-fallback ${className}`} role="img" aria-label={alt}>
      <Flower2 size={64} strokeWidth={1} />
    </div>
  ) : (
    <img
      className={className}
      src={src}
      alt={alt}
      width="1200"
      height="1500"
      onError={() => setFailed(true)}
    />
  );
}

function Home() {
  const [selected, setSelected] = useState(0);
  const ActiveIcon = categories[selected].icon;
  return (
    <>
      <main id="main">
        <section className="hero shell" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow">
              <span className="tiny-line" /> Время для себя
            </p>
            <h1 id="hero-title">
              Красота
              <br />
              начинается
              <br />
              <em>с вашего выбора.</em>
            </h1>
            <p className="hero-description">
              Ваш мастер. Ваш ритм. Ваше время.
              <br />
              Место, где забота о себе становится
              <br className="desktop-break" /> красивой привычкой.
            </p>
            <Link className="button button-dark" to="/masters">
              Найти своего мастера <ArrowRight size={18} />
            </Link>
            <p className="hero-footnote">BEAUTY, ON YOUR TERMS.</p>
          </div>
          <div className="hero-art">
            <span className="vertical-label" aria-hidden="true">
              A LITTLE MOMENT, JUST FOR YOU
            </span>
            <div className="hero-photo">
              <EditorialImage
                src="/images/beauty-editorial.jpg"
                alt="Редакционная фотография укладки волос"
              />
            </div>
            <span className="photo-index" aria-hidden="true">
              01 / THE ART OF SELF-CARE
            </span>
            <div className="hero-note">
              <Sparkles size={22} strokeWidth={1} />
              <span>
                Не особый повод.
                <br />
                <em>Особенное отношение к себе.</em>
              </span>
            </div>
            <span className="orbit" aria-hidden="true">
              m.
            </span>
          </div>
          <a className="explore-link" href="#directions">
            <ArrowDown size={15} /> Откройте свой ритуал
          </a>
        </section>
        <div className="editorial-band" aria-hidden="true">
          <span>BEAUTY</span>
          <span>✳</span>
          <span>CARE</span>
          <span>✳</span>
          <span>CONFIDENCE</span>
          <span>✳</span>
          <span>YOU</span>
        </div>
        <section
          className="directions shell section-space"
          id="directions"
          aria-labelledby="directions-title"
        >
          <div className="section-heading">
            <div>
              <p className="eyebrow">01 / Ваша красота многогранна</p>
              <h2 id="directions-title">
                Чего хочется <em>сегодня?</em>
              </h2>
            </div>
            <p>
              Маленькая перемена.
              <br />
              Совершенно новое ощущение.
            </p>
          </div>
          <div className="category-grid">
            {categories.map(({ name, icon: Icon, description }, index) => (
              <button
                key={name}
                className={`category-card ${selected === index ? "selected" : ""}`}
                aria-pressed={selected === index}
                onClick={() => setSelected(index)}
                aria-controls="category-detail"
              >
                <span className="category-top">
                  <Icon size={28} strokeWidth={1.2} />
                  <span>0{index + 1}</span>
                </span>
                <h3>{name}</h3>
                <p>{description}</p>
                <span className="category-arrow">
                  <ArrowRight size={20} />
                </span>
              </button>
            ))}
          </div>
          <div
            id="category-detail"
            className="category-detail"
            aria-live="polite"
          >
            <ActiveIcon size={24} strokeWidth={1.3} />
            <p>
              <strong>{categories[selected].name}.</strong>{" "}
              {categories[selected].detail}
            </p>
          </div>
          <Link className="text-link" to="/services">
            Все услуги и направления <ArrowRight size={18} />
          </Link>
        </section>
        <section
          className="ritual shell section-space"
          id="how-it-works"
          aria-labelledby="ritual-title"
        >
          <div className="ritual-image">
            <EditorialImage
              src="/images/nails-editorial.jpg"
              alt="Редакционная фотография маникюра"
            />
            <span className="image-caption">
              THE DETAILS MAKE THE DIFFERENCE
            </span>
          </div>
          <div className="ritual-copy">
            <p className="eyebrow">02 / Все начинается с вас</p>
            <h2 id="ritual-title">
              Меньше суеты.
              <br />
              <em>Больше себя.</em>
            </h2>
            <p className="section-intro">
              Мы создаем простой путь от «хочу» до времени, которое принадлежит
              только вам.
            </p>
            <ol className="steps">
              <li>
                <span>01</span>
                <div>
                  <h3>Найдите своего мастера</h3>
                  <p>
                    Выберите направление, познакомьтесь с работами и подходом
                    специалиста.
                  </p>
                </div>
              </li>
              <li>
                <span>02</span>
                <div>
                  <h3>Выберите удобное время</h3>
                  <p>
                    Услуга, дата и свободный слот — в одном понятном сценарии.
                  </p>
                </div>
              </li>
              <li>
                <span>03</span>
                <div>
                  <h3>Оставьте время для себя</h3>
                  <p>
                    Детали посещения будут сохранены в вашем личном кабинете.
                  </p>
                </div>
              </li>
            </ol>
          </div>
        </section>
        <section className="manifesto section-space">
          <div className="shell">
            <Flower2 size={34} strokeWidth={1} />
            <p>
              Красота — это не быть кем-то другим.
              <br />
              Это чувствовать себя <em>собой.</em>
            </p>
            <Link className="text-link" to="/brand">
              Познакомиться с MASTERLY <ArrowRight size={18} />
            </Link>
          </div>
        </section>
        <aside className="development-note shell">
          <span className="status-dot" />
          Ваш мастер. Ваш ритм. Ваше время.
        </aside>
      </main>
    </>
  );
}

const palettes = [
  {
    name: "Soft Luxury",
    selected: true,
    text: "Тепло, тактильность и спокойный характер. Основная палитра MASTERLY.",
    colors: ["#F8F5EF", "#E8DED1", "#D9BDB5", "#80685B", "#302C29"],
  },
  {
    name: "Modern Editorial",
    selected: false,
    text: "Более строгая, контрастная альтернатива с золотым акцентом.",
    colors: ["#FCFAF7", "#D5CBC0", "#C3A66B", "#B78979", "#30221C"],
  },
  {
    name: "Contemporary Beauty",
    selected: false,
    text: "Прохладный жемчужный фон и глубокий сливовый акцент.",
    colors: ["#F4F0EE", "#DECAC0", "#B89CAA", "#80645A", "#422D40"],
  },
];

function BrandPage() {
  return (
    <main id="main" className="brand-page shell section-space">
      <p className="eyebrow">MASTERLY / Visual identity v1.0</p>
      <h1>
        Тихая уверенность.
        <br />
        <em>Выразительные детали.</em>
      </h1>
      <p className="section-intro">
        Визуальная система платформы: теплая палитра, редакционная типографика и
        оригинальная монограмма.
      </p>
      <section className="section-space" aria-labelledby="palette-title">
        <h2 id="palette-title">
          Три направления. <em>Один характер.</em>
        </h2>
        <div className="palette-grid">
          {palettes.map((palette) => (
            <article key={palette.name} className="palette">
              <div className="swatches">
                {palette.colors.map((color) => (
                  <span
                    key={color}
                    style={{ backgroundColor: color }}
                    title={color}
                  >
                    <small>{color}</small>
                  </span>
                ))}
              </div>
              <h3>
                {palette.name}{" "}
                {palette.selected && (
                  <span className="badge">
                    <Check size={12} /> Выбрана
                  </span>
                )}
              </h3>
              <p>{palette.text}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="section-space" aria-labelledby="logo-title">
        <p className="eyebrow">01 / Логотип</p>
        <h2 id="logo-title">
          Два движения. <em>Одна M.</em>
        </h2>
        <p>
          Две арки напоминают зеркало и соединяются в монограмму M. Тонкий знак
          над центром — акцент внимания и заботы.
        </p>
        <div className="logo-gallery">
          <div>
            <Brand />
            <a className="text-link" href="/brand/masterly-light.svg" download>
              SVG для светлого фона <ArrowDown size={15} />
            </a>
          </div>
          <div className="dark-surface">
            <Brand />
            <a className="text-link" href="/brand/masterly-dark.svg" download>
              SVG для темного фона <ArrowDown size={15} />
            </a>
          </div>
          <div>
            <Brand compact />
            <a className="text-link" href="/brand/masterly-symbol.svg" download>
              Монограмма SVG <ArrowDown size={15} />
            </a>
          </div>
        </div>
      </section>
      <section className="type-specimen section-space">
        <div>
          <p className="eyebrow">02 / Cormorant Garamond</p>
          <h2>
            Красота
            <br />
            <em>в простом.</em>
          </h2>
          <p>
            Выразительная антиква для заголовков.
            <br />
            Аа Бб Вв Гг Дд Ее Жж Зз
          </p>
        </div>
        <div>
          <p className="eyebrow">03 / Manrope</p>
          <h3>Понятно. Спокойно. Удобно.</h3>
          <p>
            Интерфейсный шрифт для навигации, форм и текста. Оба семейства
            поддерживают кириллицу и поставляются локально с лицензией SIL OFL
            1.1.
          </p>
          <div className="button-samples">
            <a className="button button-dark" href="/#directions">
              Основное действие <ArrowRight size={16} />
            </a>
            <Link className="button button-outline" to="/">
              Вторичное действие
            </Link>
          </div>
          <label className="sample-field">
            Пример поля
            <input type="text" placeholder="Ваше имя" autoComplete="off" />
          </label>
        </div>
      </section>
    </main>
  );
}

function NotFound() {
  return (
    <main id="main" className="not-found shell">
      <Brand compact />
      <p className="eyebrow">404 / Страница не найдена</p>
      <h1>
        Кажется, здесь
        <br />
        <em>время для паузы.</em>
      </h1>
      <Link className="button button-dark" to="/">
        Вернуться на главную <ChevronRight size={18} />
      </Link>
    </main>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <PagePosition />
            <ViewportEffects />
            <a className="skip-link" href="#main">
              Перейти к содержимому
            </a>
            <Header />
            <Suspense
              fallback={
                <main id="main" className="shell">
                  <LoadingState
                    label="Загружаем…"
                    className="workspace-state"
                  />
                </main>
              }
            >
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/brand" element={<BrandPage />} />
                <Route path="/masters" element={<MastersPage />} />
                <Route path="/masters/:id" element={<MasterPage />} />
                <Route path="/services" element={<ServicesPage />} />
                <Route
                  path="/book/:masterId"
                  element={
                    <ProtectedRoute roles={["CLIENT"]}>
                      <BookingPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/bookings/:id"
                  element={
                    <ProtectedRoute>
                      <BookingDetailsPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                {workspaceRoutes.map((route) => (
                  <Route
                    key={route.path}
                    path={route.path}
                    element={
                      <ProtectedRoute roles={[route.role]}>
                        <WorkspaceRedirect to={route.to} tab={route.tab} />
                      </ProtectedRoute>
                    }
                  />
                ))}
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute roles={["CLIENT"]}>
                      <AccountPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/master/dashboard"
                  element={
                    <ProtectedRoute roles={["MASTER"]}>
                      <AccountPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin"
                  element={
                    <ProtectedRoute roles={["ADMIN"]}>
                      <AccountPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <ProfilePage />
                    </ProtectedRoute>
                  }
                />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
            <footer className="site-footer shell">
              <Brand />
              <p>Немного заботы. Каждый день.</p>
              <Link to="/brand">
                Фирменный стиль <ArrowRight size={15} />
              </Link>
              <span>© {currentYear} MASTERLY</span>
            </footer>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
