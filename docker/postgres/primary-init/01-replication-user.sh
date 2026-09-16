#!/bin/sh
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE ${POSTGRES_REPLICATION_USER} WITH REPLICATION LOGIN PASSWORD '${POSTGRES_REPLICATION_PASSWORD}';
SQL

echo "host replication ${POSTGRES_REPLICATION_USER} all md5" >> "$PGDATA/pg_hba.conf"
echo "host all all all md5" >> "$PGDATA/pg_hba.conf"
