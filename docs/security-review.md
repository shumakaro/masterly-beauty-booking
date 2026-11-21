# Security review

Актуализация 21.11.2026. Локальные изменения проверены отдельно на PostgreSQL 18. Статус CI следует проверять для точного SHA в PR; production-деплой отдельно не разрешен; это не независимый аудит.

| Пункт | Статус | Доказательство/ограничение |
|---|---|---|
| bcrypt, без plaintext/truncation | PASS | hash/limit API tests |
| JWT подпись/expiry/type | PASS | invalid/expired JWT tests |
| ADMIN не самоназначается | PASS | register 422, role PATCH 422, CLI only |
| Права на сервере и текущая роль БД | PASS | CLIENT -> master/admin 403; изменение DB role |
| Собственный профиль | PASS | /users/me из текущего user.id, /master/profile по владельцу |
| Чужие записи | PASS API | Business API и PostgreSQL tests: чужие bookings/offers/reviews/portfolio возвращают 404, списки и overview ограничены владельцем |
| Refresh hashing/rotation/replay | PASS | cookie flags + family revocation tests |
| Logout | PASS with limit | Refresh отозван, access истекает до 15 мин |
| CSRF/CORS | PASS | Origin/custom header, wildcard rejected, credentials explicit |
| Лимиты запросов | PASS single-process | 429/Retry-After; нет distributed storage |
| Ошибки не возвращают password/input/SQL | PASS API | SecretStr, sanitized 422, domain/DB/generic 500 handler; тест неразглашения внутреннего сообщения |
| Заголовки и приватный cache | PASS API | no-store для всех /api/v1 и ошибок; nosniff/DENY/no-referrer, request_id |
| HTTPS/HSTS/CSP | Реализованы | Render HTTPS; HSTS/CSP в packaged runtime. VPS + Nginx в production не заявлены |
| SQL параметризован | PASS текущие запросы | SQLAlchemy select/update; сырые SQL только фиксированные миграции/тесты |
| Нет ключей по умолчанию | PASS | JWT_SECRET private/required at auth; env ignored |
| Нет токенов в web storage | PASS | Real browser check |
| XSS | BASELINE | React escaping, нет dangerouslySetInnerHTML, изображения только HTTP/S либо локальный разрешенный путь; сервер их не скачивает. Нет независимого penetration test |
| Запросы не логируют credentials | PASS текущая конфигурация | request_id, method/path/status only |

JWT-secret CI генерируется заново и маскируется, PostgreSQL CI password относится только к уничтожаемому сервису. В рамках текущей доработки секреты production не менялись и не публиковались. В GitHub не отправляются исходные пользовательские материалы и локальный отчет.

Зависимости зафиксированы в requirements.txt/package-lock.json. Повторные локальные pip-audit и npm audit от 21.11.2026 не нашли известных уязвимостей в зафиксированных runtime-зависимостях Python и npm-дереве. Результаты текущего прогона включены в пакет исходников. Проверки включены в CI и не используют allowlist исключений. Это не гарантия отсутствия неизвестных уязвимостей.

Новый поиск доступности использует пакетные запросы и общий календарь. Отсутствие N+1 проверяется счетчиком SELECT, но массовые запросы к большому каталогу не нагрузочно тестировались. В production нужны proxy rate limits и наблюдение за задержкой. Ограничитель auth пока хранится в процессе; несколько workers требуют общего хранилища либо внешнего лимита. Публичные HTTPS/HSTS/CSP и готовность БД проверены чтением. Новая миграция не развернута; backup/restore и полный production QA текущей версии требуют отдельной проверки.


## Локальные расширения профилей

Миграция 005 не изменяет пароли или роли. `is_demo` не принимается в MasterUpdate/ReviewCreate/ReviewUpdate. Фото отзывов допускает только HTTP(S) или разрешенный локальный путь; сервер не загружает эти URL. Ownership портфолио/отзывов сохранен. Seed showcase проверяет суффикс отдельной БД до SQL и не обновляет существующие объекты. Запросы каталога агрегируют рейтинг пакетно.

Исправлена нормализация разделителей пути для SPA на Windows: неизвестные API и отсутствующие ресурсы сохраняют 404. Добавлены тесты на обратные слеши и URL ресурсов без расширения. Прямые URL изображений остаются внешними ресурсами; приложение не гарантирует доступность чужого хостинга. Это техническая проверка проекта, не независимый penetration test.
