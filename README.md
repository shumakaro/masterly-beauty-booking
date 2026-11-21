# MASTERLY

Индивидуальный учебный проект платформы записи к мастерам красоты. Отдельный репозиторий: https://github.com/shumakaro/masterly-beauty-booking. BookNest не используется.

## Текущий статус

React/TypeScript/Vite, FastAPI и PostgreSQL, 12 таблиц и пять Alembic-миграций. Работают каталог, запись, отзывы и кабинеты CLIENT/MASTER/ADMIN. Базовая версия опубликована: https://masterly-beauty-booking.onrender.com/ . Локальные дополнения профилей, портфолио и фотографий отзывов требуют миграции 005 и отдельного согласованного деплоя; автоматически на сервер не отправляются.

Роли CLIENT, MASTER и ADMIN разделяют пользовательские сценарии и серверные права доступа.

## Локальный запуск (PowerShell, из корня)

Требуется Node.js 24, Python 3.12+ и PostgreSQL 18. Для контейнерного варианта нужен Docker.

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
- docs/deployment/RELEASES.md: совместимость схем, резервирование и безопасный выпуск.
- docs/security-review.md: реализованные меры защиты и ограничения.

Схема БД описана в backend/DATABASE.md. Базовая публичная версия доступна на Render; новый выпуск требует отдельного развертывания. Health проверяет процесс, readiness — подключение, совместимую ревизию и необходимые столбцы. Рабочих учетных данных в репозитории нет.

Использование AI раскрыто в AI_USAGE.md. Порядок выпуска и восстановления: docs/deployment/RELEASES.md.

Официальные источники настройки: https://vite.dev/guide/ и https://fastapi.tiangolo.com/.

## Фирменный стиль и проверка дизайна

Страница /brand показывает три палитры, выбранную Soft Luxury, SVG-логотипы, шрифты и компоненты. Шрифты хранятся локально, лицензии включены в frontend/public/licenses; источники фото — frontend/ASSET_SOURCES.md.

Браузерная проверка (требует установленный Microsoft Edge): запустить frontend командой npm run dev -- --host 127.0.0.1 --port 5174 --strictPort, затем из frontend выполнить node scripts/check-design.mjs. Скрипт проверяет 7 ширин, навигацию и reduced motion и сохраняет PNG/JSON в локальный docs/evidence. Он не запускается в CI без настройки Edge.

Исходные пользовательские материалы, личные документы, дампы, секреты и локальные артефакты проверок не входят в публикуемый код.


## Авторизация

Подробные контракты и настройки: backend/AUTH.md. Нет ключа JWT и паролей по умолчанию. Создание ADMIN — только через python -m app.cli со скрытым вводом пароля. COOKIE_SECURE=false допускается только для localhost; production требует HTTPS и Secure cookie. Access хранится в памяти, refresh — HttpOnly cookie. Logout отзывает refresh, скопированный access может действовать до 15 минут.

В наборе проверок: 104 backend-теста, 19 frontend-тестов и 25 основных Playwright-сценариев авторизации, каталога, записи, кабинетов, тем и доступности. Playwright запускается отдельно: из frontend npx playwright test (требуются работающие API, одноразовая тестовая БД с наполнителями scripts.seed_browser и app.db.showcase, приватный случайный BROWSER_TEST_PASSWORD и frontend на адресах из playwright.config.mjs). Подробности: frontend/BOOKING.md и frontend/ACCESSIBILITY.md.

## Бизнес-API

Контракты: backend/BUSINESS_API.md, живая схема /openapi.json и /docs. Применить alembic upgrade head (включая 005 richer profiles). POST /api/v1/bookings требует CLIENT и UUID Idempotency-Key. Свободное время берется из /masters/{id}/availability, значения цены/длительности сохраняются сервером. Тесты PostgreSQL проверяют записи двух клиентов, повторные запросы, конфликт графика, отмену, владение, DST, отзывы, избранное, SQL-пагинацию и отсутствие N+1.

## Каталог

Страницы /masters, /services и /masters/:id подключены к API. Поиск, фильтры и пагинация сохраняются в URL. В профиле доступны услуги, работы, отзывы и просмотр свободного времени с часовым поясом мастера. Полное описание и проверка: frontend/CATALOG.md.

## Запись и кабинеты

CLIENT оформляет запись через /book/:masterId и видит результат на /bookings/:id. Кабинеты включают посещения/отмену, избранное и отзывы клиента; профиль/услуги/график/портфолио мастера; каталог/пользователей/видимость/посещения администратора. Неподтвержденная попытка записи восстанавливается после потери ответа и reload, POST повторяется с прежним ключом операции. Ограничения и сценарии проверки: frontend/BOOKING.md. Базовая версия опубликована на Render; размещение VPS + Nginx не выполнялось.

## Темы и доступность

В шапке доступны светлая, темная и системная темы. Выбор сохраняется и синхронизируется между вкладками. Интерфейс поддерживает клавиатуру, видимый фокус, Escape для меню/галереи/подтверждений и уменьшенное движение. Подробности анимаций, загрузки, axe-проверок и ограничений автоматического аудита: frontend/ACCESSIBILITY.md.


## Расширенные профили и демонстрационное наполнение

Миграция 005 добавляет специализацию и стаж мастера, название/описание/категорию работы, фотографию отзыва и признак демонстрационного отзыва. Существующие записи получают безопасные значения по умолчанию. Мастера изменяют только свои профили и работы; настоящие отзывы требуют собственного завершенного посещения. Демопризнаки не назначаются через публичные формы.

Наполнитель `python -m app.db.showcase` использует только `DEMO_DATABASE_URL` или `TEST_DATABASE_URL` и отказывается работать с именем БД без суффикса `_demo`/`_test`. Сначала примените миграции на этой отдельной БД. Он добавляет восемь вымышленных профилей, услуги, график, работы и явно помеченные примеры отзывов. Повторный запуск не перезаписывает существующие объекты. Паролей по умолчанию нет. Это не команда наполнения production. Старый `app.db.seed` сохраняет совместимость с прежними отключенными fixtures.

На Windows путь к исполняемым файлам PostgreSQL и его каталогу данных должен поддерживаться кодировкой этой сборки; для локальной проверки использован ASCII-путь. Браузерные и backend-тесты должны работать на разных одноразовых базах, если запускаются одновременно: backend fixture очищает данные. Облако не требуется для изолированных тестов.

## Совместимый выпуск B

Эта ветка зависит от выпуска A. Readiness проверяет схему 005 и необходимые столбцы. Порядок обновления и возврата на A: [docs/deployment/RELEASES.md](docs/deployment/RELEASES.md). Ни эта ветка, ни PR не являются разрешением production-деплоя.
