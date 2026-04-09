# SupaWriter Deployment

This directory contains the files for deploying the SupaWriter application using Docker.

## Deployment Strategy

The deployment is managed through Docker Compose. We have two main setups:

1.  **Production (`docker-compose.yml`):**
    This is the main file for full production deployment. It defines the infrastructure (`postgres`, `redis`, `trendradar`) and the application services (`backend`, `worker`, `frontend`, `nginx`). PostgreSQL mounts `deployment/postgres/bootstrap` only, so business tables are created by Alembic rather than by legacy init SQL.

    The canonical production startup path is the serialized bootstrap script from the repo root:
    ```bash
    ./deployment/docker-start.sh
    ```

    That script:
    - builds the application images
    - starts infra services first
    - runs `repair_schema_drift.py`, Alembic, and `init_production_state.py`
    - starts the app services only after migrations complete

2.  **Development (`docker-compose.dev.yml`):**
    This file is designed for local development. It uses development-specific Dockerfiles (`.local`) and mounts the local source code into the containers, enabling hot-reloading for the `backend` and `frontend` services.

    To run the development environment:
    ```bash
    docker-compose -f docker-compose.dev.yml up --build
    ```

## Files

-   `docker-compose.yml`: Docker Compose file for **production**.
-   `docker-compose.dev.yml`: Docker Compose file for **local development**.
-   `docker-start.sh`: Canonical production bootstrap entrypoint.
-   `Dockerfile.backend`: Production Dockerfile for the FastAPI backend.
-   `Dockerfile.frontend`: Production Dockerfile for the Next.js frontend.
-   `Dockerfile.streamlit`: Production Dockerfile for the Streamlit service.
-   `Dockerfile.backend.local`: Development Dockerfile for the FastAPI backend.
-   `Dockerfile.frontend.local`: Development Dockerfile for the Next.js frontend.
-   `nginx/`: Nginx configuration files.
-   `postgres/bootstrap/`: Minimal PostgreSQL bootstrap SQL run on first database creation.
-   `postgres/init/`: Legacy SQL kept for reference only; not mounted by the production compose file.
-   `redis/`: Redis data.

## Environment Variables

Create a `.env` file in this directory with the necessary environment variables. You can use `.env.example` as a template.
Set `SUPER_ADMIN_EMAILS` explicitly if you want startup to promote specific accounts; leaving it empty disables super-admin provisioning.
