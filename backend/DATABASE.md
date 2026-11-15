# PostgreSQL и миграции MASTERLY

Требуется PostgreSQL 18 (в CI используется postgres:18). Приложение использует SQLAlchemy 2 и psycopg 3. Миграции создают btree_gist для EXCLUDE; пользователь мигратора должен иметь CREATE в базе. Миграции не требуют суперпользователя при поддержке trusted extension хостингом.

Из backend, после установки requirements-dev.txt:

```powershell
# Приватно настройте DATABASE_URL и DATABASE_URL_UNPOOLED в корневом .env.
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.db.seed
```

DATABASE_URL - подключение приложения. DATABASE_URL_UNPOOLED - прямое подключение мигратора; Neon pooler не использовать для Alembic. В исходниках нет рабочих паролей. В CI есть публичный одноразовый пароль изолированного сервиса, не production-секрет.

Ревизии: 001 identity/catalog/refresh; 002 schedules/exceptions/bookings + btree_gist; 003 reviews/favorites/portfolio. DDL заморожен в файлах ревизий и не импортирует изменяемые текущие модели. Откат: alembic downgrade -1. На рабочей базе downgrade может удалять данные: сначала резервная копия и проверка на отдельной базе. btree_gist при откате оставляется установленным: расширение может использоваться другими объектами базы.

Демоданные: три категории/услуги/профиля/предложения с устойчивыми UUID. Seed идемпотентен, не переписывает существующие записи. Демо-мастера явно маркированы; аккаунты отключены и профили не опубликованы до настройки авторизации/паролей. Hash !disabled-demo-account не является паролем для входа. Скрипт не создает администратора и не очищает базу.

## Интеграционные проверки

TEST_DATABASE_URL должен указывать исключительно на одноразовую PostgreSQL-базу с именем, заканчивающимся на _test. Тесты откатывают все миграции вплоть до base и очищают тестовые таблицы. Никогда не указывать рабочую БД. Без TEST_DATABASE_URL они явно SKIP, а не PASS.

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST/masterly_test'
..\.venv\Scripts\python.exe -m pytest -q --junitxml=test-results/pytest.xml
```

GitHub Actions создает отдельный PostgreSQL-сервис с healthcheck. Проверяются 12 таблиц, все границы downgrade/upgrade, пересечения и соседние интервалы, отмена/освобождение, некорректные данные, идемпотентный seed и реальная конкурентная вставка из двух соединений. Тест EXPLAIN заполняет 3000 одноразовых записей и сохраняет планы двух запросов, данные затем удаляются. Артефакт database-verification содержит JUnit и query-plans.json; отдельный тестовый сервис уничтожается после job.

Ограничения схемы не заменяют бизнес-сервис: права, IANA timezone, соответствие графику, переходы статусов и правила отзывов реализуются в следующих этапах. Проверки модели используют lazy=raise для связей: будущие endpoints должны явно выбирать eager loading, чтобы исключать скрытый N+1.
