-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set default locale for text search
CREATE TEXT SEARCH CONFIGURATION portuguese (COPY = pg_catalog.portuguese);

-- Create initial schema
CREATE SCHEMA IF NOT EXISTS public;

-- Grant permissions
GRANT ALL ON SCHEMA public TO jusmonitoria;
GRANT ALL ON ALL TABLES IN SCHEMA public TO jusmonitoria;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO jusmonitoria;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO jusmonitoria;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO jusmonitoria;
