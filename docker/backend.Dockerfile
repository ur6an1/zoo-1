FROM python:3.11-slim AS base

WORKDIR /app

COPY constraints.txt .

COPY shared/ shared/
RUN pip install --no-cache-dir -c constraints.txt -e shared/

COPY backend/ backend/
RUN pip install --no-cache-dir -c constraints.txt -e backend/

COPY alembic/ alembic/
COPY alembic.ini .

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core curl && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
