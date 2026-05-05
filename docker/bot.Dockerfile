FROM python:3.11-slim AS base

WORKDIR /app

COPY shared/ shared/
RUN pip install --no-cache-dir -e shared/

COPY bot/ bot/
RUN pip install --no-cache-dir -e bot/

CMD ["python", "-m", "bot.main"]
