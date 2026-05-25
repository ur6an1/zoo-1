FROM python:3.11-slim AS base

WORKDIR /app

COPY constraints.txt .

COPY shared/ shared/
RUN pip install --no-cache-dir -c constraints.txt -e shared/

COPY backend/ backend/
RUN pip install --no-cache-dir -c constraints.txt -e backend/

COPY bot/ bot/
RUN pip install --no-cache-dir -c constraints.txt -e bot/

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

CMD ["python", "-m", "bot.main"]
