#!/bin/sh
set -eu
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set=ON_ERROR_STOP=1 --set=app_password="$MASTERLY_DB_PASSWORD" <<'SQL'
CREATE ROLE masterly LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'app_password';
ALTER DATABASE masterly OWNER TO masterly;
GRANT ALL ON SCHEMA public TO masterly;
SQL
