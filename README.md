# MASTERLY

Индивидуальный учебный проект платформы записи к мастерам красоты. Отдельный репозиторий: https://github.com/shumakaro/masterly-beauty-booking. BookNest не используется.

## Текущий статус

Этап 4: React/TypeScript/Vite и FastAPI, фирменный стиль Soft Luxury, адаптивная главная (/), бренд-страница (/brand) и 404. API имеет /api/v1/health (liveness). Каталог, БД, авторизация и бронирование еще не реализованы. Публичного рабочего сайта пока нет. CI: проверки каркаса и дизайна прошли в GitHub Actions.

Пользователь подтвердил индивидуальный формат и сохранение расширенного объема: CLIENT, MASTER, ADMIN. Разрешение преподавателя на расширение относительно силлабуса пока не подтверждено. Срок: как можно раньше, календарный дедлайн не задан.

## Локальный запуск (PowerShell, из корня)

Требуется Node.js 24 и Python 3.12. Docker понадобится на этапе контейнеризации.

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
cd backend
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

БД/ER, demo-доступы и production URL будут добавлены после реализации и проверки. Реальные локальные скриншоты интерфейса сохранены в локальном отчете. Не использовать вымышленные данные доступа. Health показывает только работоспособность процесса API, не готовность БД.

Использование AI раскрыто в AI_USAGE.md. Полный план и критерии приемки: docs/audit/02_ROUTES_AND_ACCEPTANCE.md и docs/report/14_REQUIREMENTS_CHECKLIST.md.

Официальные источники настройки: https://vite.dev/guide/ и https://fastapi.tiangolo.com/.

## Фирменный стиль и проверка дизайна

Страница /brand показывает три палитры, выбранную Soft Luxury, SVG-логотипы, шрифты и компоненты. Шрифты хранятся локально, лицензии включены в frontend/public/licenses; источники фото — frontend/ASSET_SOURCES.md.

Браузерная проверка (требует установленный Microsoft Edge): запустить frontend командой npm run dev -- --host 127.0.0.1 --port 5174 --strictPort, затем из frontend выполнить node scripts/check-design.mjs. Скрипт проверяет 7 ширин, навигацию и reduced motion и сохраняет PNG/JSON в локальный docs/evidence. Он не запускается в CI без настройки Edge.

Исходный прототип, силлабус, ZIP/ODT/текст ТЗ и локальный отчет не публикуются по решению пользователя. Ссылки на docs относятся к локальному комплекту проекта.

