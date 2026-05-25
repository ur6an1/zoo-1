FROM python:3.11-slim AS base

WORKDIR /app

COPY constraints.txt .

COPY shared/ shared/
RUN pip install --no-cache-dir -c constraints.txt -e shared/

COPY worker/ worker/
RUN pip install --no-cache-dir -c constraints.txt -e worker/

CMD ["python", "-m", "worker.main"]
