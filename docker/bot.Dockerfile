FROM python:3.11-slim AS base

WORKDIR /app

COPY shared/ shared/
RUN pip install --no-cache-dir -e shared/

COPY backend/ backend/
RUN pip install --no-cache-dir -e backend/

COPY bot/ bot/
RUN pip install --no-cache-dir -e bot/

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

CMD ["python", "-m", "bot.main"]
