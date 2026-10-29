
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY the-house-that-remembers/ ./the-house-that-remembers/
COPY start.sh ./start.sh
RUN chmod +x /app/start.sh

ENV MODEL_PROVIDER=openrouter \
    PORT=10000

EXPOSE 10000

ENTRYPOINT ["/bin/sh", "/app/start.sh"]
