# MASTERLY

Индивидуальный учебный проект платформы записи к мастерам красоты. Отдельный репозиторий: https://github.com/shumakaro/masterly-beauty-booking. BookNest не используется.

## Текущий статус

Этап 7: React/TypeScript/Vite и FastAPI, фирменный стиль и адаптивные страницы, PostgreSQL (12 таблиц, четыре миграции), регистрация/JWT/refresh и права трех ролей. Backend содержит каталог, график/исключения, availability, настоящую запись/отмену/завершение, отзывы, избранное и администрирование. UI пока подключен к авторизации/профилю; интерфейс каталога и бронирования готовится на следующих этапах. Публичного рабочего сайта пока нет.

Пользователь подтвердил индивидуальный формат и сохранение расширенного объема: CLIENT, MASTER, ADMIN. Разрешение преподавателя на расширение относительно силлабуса пока не подтверждено. Срок: как можно раньше, календарный дедлайн не задан.

## Локальный запуск (PowerShell, из корня)

Требуется Node.js 24 и Python 3.12. Docker понадобится на этапе контейнеризации.

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
cd backend
..\.venv\Scripts\python.exe scripts/configure_local.py
# Configure private DATABASE_URL and DATABASE_URL_UNPOOLED in .env before migration.
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

В другом терминале из корня:

```powershell
cd frontend
npm ci
npm run dev
```

Frontend: http://localhost:5173. API: http://localhost:8000/api/v1/health. OpenAPI: http://localhost:8000/docs. Эти адреса только для локальной разработки; API URL задается через .env. После изменения VITE-переменных перезапустить Vite.

## Проверки

```powershell
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

```powershell
cd backend
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m ruff format --check .
..\.venv\Scripts\python.exe -m pytest -q
```

Зависимости frontend закреплены package-lock.json; backend - requirements.txt и requirements-dev.txt. Для изменения backend-зависимостей обновить pyproject.toml и пересоздать lock через pip-compile; не редактировать транзитивные версии вручную.

## Структура

- frontend/src: React, pages/features/shared, единый API-клиент.
- backend/app: main, api/v1, core, services, repositories.
- backend/tests: изолированные тесты API.
- .github/workflows/ci.yml: lint/typecheck/tests/build.
- docs/audit: исходный аудит, сценарии и SHA256 материалов.
- docs/report: матрица требований и непрерывный журнал.
- Исходный TSX, syllabus, ODT и ZIP сохранены в корне как материалы, не как исполняемая часть.

Схема БД описана в backend/DATABASE.md; ER и доказательства доступны в локальном отчете. Production URL пока нет. Реальные локальные скриншоты интерфейса сохранены в локальном отчете. Не использовать вымышленные данные доступа. Health показывает только работоспособность процесса API, не готовность БД.

Использование AI раскрыто в AI_USAGE.md. Полный план и критерии приемки: docs/audit/02_ROUTES_AND_ACCEPTANCE.md и docs/report/14_REQUIREMENTS_CHECKLIST.md.

Официальные источники настройки: https://vite.dev/guide/ и https://fastapi.tiangolo.com/.

## Фирменный стиль и проверка дизайна

Страница /brand показывает три палитры, выбранную Soft Luxury, SVG-логотипы, шрифты и компоненты. Шрифты хранятся локально, лицензии включены в frontend/public/licenses; источники фото — frontend/ASSET_SOURCES.md.

Браузерная проверка (требует установленный Microsoft Edge): запустить frontend командой npm run dev -- --host 127.0.0.1 --port 5174 --strictPort, затем из frontend выполнить node scripts/check-design.mjs. Скрипт проверяет 7 ширин, навигацию и reduced motion и сохраняет PNG/JSON в локальный docs/evidence. Он не запускается в CI без настройки Edge.

Исходный прототип, силлабус, ZIP/ODT/текст ТЗ и локальный отчет не публикуются по решению пользователя. Ссылки на docs относятся к локальному комплекту проекта.


## Авторизация

Подробные контракты и настройки: backend/AUTH.md. Нет ключа JWT и паролей по умолчанию. Создание ADMIN — только через python -m app.cli со скрытым вводом пароля. COOKIE_SECURE=false допускается только для localhost; production требует HTTPS и Secure cookie. Access хранится в памяти, refresh — HttpOnly cookie. Logout отзывает refresh, скопированный access может действовать до 15 минут.

В наборе проверок: 64 backend-теста, 18 frontend-тестов и 22 Playwright-сценария авторизации, каталога, записи, кабинетов, тем и доступности. Playwright запускается отдельно: из frontend npx playwright test (требуются работающие API, одноразовая тестовая БД с наполнителем scripts.seed_browser, приватный случайный BROWSER_TEST_PASSWORD и frontend на адресах из playwright.config.mjs). Подробности: frontend/BOOKING.md и frontend/ACCESSIBILITY.md.

## Бизнес-API

Контракты: backend/BUSINESS_API.md, живая схема /openapi.json и /docs. Применить alembic upgrade head (включая новую 004 timezone snapshot). POST /api/v1/bookings требует CLIENT и UUID Idempotency-Key. Свободное время берется из /masters/{id}/availability, значения цены/длительности сохраняются сервером. Тесты PostgreSQL проверяют записи двух клиентов, повторные запросы, конфликт графика, отмену, владение, DST, отзывы, избранное, SQL-пагинацию и отсутствие N+1.

## Каталог

Страницы /masters, /services и /masters/:id подключены к API. Поиск, фильтры и пагинация сохраняются в URL. В профиле доступны услуги, работы, отзывы и просмотр свободного времени с часовым поясом мастера. Полное описание и проверка: frontend/CATALOG.md.

## Запись и кабинеты

CLIENT оформляет запись через /book/:masterId и видит результат на /bookings/:id. Кабинеты включают посещения/отмену, избранное и отзывы клиента; профиль/услуги/график/портфолио мастера; каталог/пользователей/видимость/посещения администратора. Неподтвержденная попытка записи восстанавливается после потери ответа и reload, POST повторяется с прежним ключом операции. Ограничения и сценарии проверки: frontend/BOOKING.md. Production-деплой пока не выполнен.

## Темы и доступность

В шапке доступны светлая, темная и системная темы. Выбор сохраняется и синхронизируется между вкладками. Интерфейс поддерживает клавиатуру, видимый фокус, Escape для меню/галереи/подтверждений и уменьшенное движение. Подробности анимаций, загрузки, axe-проверок и ограничений автоматического аудита: frontend/ACCESSIBILITY.md.

## Совместимые выпуски

Проверка схемы, миграционные таймауты и порядок безопасного обновления описаны в [docs/deployment/RELEASES.md](docs/deployment/RELEASES.md). Эта ветка — выпуск A: прежняя логика API, поддержка схем 004/005 и неизмененная миграция 005. Production-деплой требует отдельного разрешения.
