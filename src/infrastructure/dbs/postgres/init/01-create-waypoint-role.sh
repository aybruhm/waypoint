#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'waypoint') THEN
            CREATE ROLE waypoint LOGIN PASSWORD '${POSTGRES_PASSWORD:-1q2w3e4r5t6y}';
        END IF;
    END
    \$\$;
EOSQL
