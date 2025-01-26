#! /usr/bin/env bash

set -e
set -x

cd backend/

pipx install uv

uv sync

# Let the DB start
uv run app/backend_pre_start.py

# Run migrations
uv run alembic upgrade head

# Create initial data in DB
uv run app/initial_data.py

cd ../frontend

pnpm install

sudo ln -s /workspaces/full-stack-super-computer/backend/app/cli/cmd.py /usr/local/bin/runner
