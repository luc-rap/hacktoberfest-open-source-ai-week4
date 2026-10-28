
FROM ollama/ollama:0.35.1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv curl\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
    && /opt/venv/bin/pip install --no-cache-dir Pillow

COPY the-house-that-remembers/ ./the-house-that-remembers/
COPY start.sh ./start.sh
RUN chmod +x /app/start.sh

ENV PATH="/opt/venv/bin:$PATH" \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_KEEP_ALIVE=-1 \
    OLLAMA_CONTEXT_LENGTH=4096 \
    PORT=10000

EXPOSE 10000

CMD ["/bin/sh", "/app/start.sh"]
