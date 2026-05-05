FROM python:3.11-slim AS base

WORKDIR /app

COPY shared/ shared/
RUN pip install --no-cache-dir -e shared/

COPY worker/ worker/
RUN pip install --no-cache-dir -e worker/

CMD ["python", "-m", "worker.main"]
