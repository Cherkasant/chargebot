FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Data directory for SQLite
RUN mkdir -p /app/data
VOLUME ["/app/data"]

CMD ["python", "-m", "src.chargebot.main"]


