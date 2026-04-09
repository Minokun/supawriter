-- Minimal PostgreSQL bootstrap for fresh SupaWriter databases.
-- Business schema is owned by Alembic migrations.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
