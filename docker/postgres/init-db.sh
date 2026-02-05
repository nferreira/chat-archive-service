#!/bin/sh
set -eu

# This script runs once when the PostgreSQL data directory is first initialised.
# It creates the application database, user, and schema using variables that
# are passed through docker-compose → environment → here.
#
# POSTGRES_USER / POSTGRES_PASSWORD are consumed by the official entrypoint to
# create the superuser.  The APP_* variables below create a least-privilege
# role that the application connects with.

: "${APP_DB_USER:?APP_DB_USER is required}"
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD is required}"
: "${APP_DB_NAME:?APP_DB_NAME is required}"
: "${APP_DB_SCHEMA:=public}"

echo "==> Creating application database '${APP_DB_NAME}' ..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-SQL
    SELECT 'CREATE DATABASE ${APP_DB_NAME}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${APP_DB_NAME}')\gexec
SQL

echo "==> Creating application user '${APP_DB_USER}' ..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${APP_DB_NAME}" <<-SQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${APP_DB_USER}') THEN
            CREATE ROLE ${APP_DB_USER} LOGIN PASSWORD '${APP_DB_PASSWORD}';
        END IF;
    END
    \$\$;
SQL

if [ "${APP_DB_SCHEMA}" != "public" ]; then
    echo "==> Creating schema '${APP_DB_SCHEMA}' ..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${APP_DB_NAME}" <<-SQL
        CREATE SCHEMA IF NOT EXISTS ${APP_DB_SCHEMA};
        ALTER ROLE ${APP_DB_USER} SET search_path TO ${APP_DB_SCHEMA}, public;
SQL
fi

echo "==> Granting privileges to '${APP_DB_USER}' on '${APP_DB_NAME}' ..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${APP_DB_NAME}" <<-SQL
    GRANT CONNECT ON DATABASE ${APP_DB_NAME} TO ${APP_DB_USER};
    GRANT USAGE  ON SCHEMA ${APP_DB_SCHEMA} TO ${APP_DB_USER};
    GRANT CREATE ON SCHEMA ${APP_DB_SCHEMA} TO ${APP_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA ${APP_DB_SCHEMA}
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${APP_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA ${APP_DB_SCHEMA}
        GRANT USAGE, SELECT ON SEQUENCES TO ${APP_DB_USER};
SQL

echo "==> Database initialisation complete."
