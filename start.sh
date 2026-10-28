
#!/bin/sh
set -e

ollama serve &

until curl -sf http://127.0.0.1:11434/api/version >/dev/null; do
    sleep 1
done

ollama pull gemma4:e4b

exec streamlit run /app/the-house-that-remembers/app.py \
    --server.address 0.0.0.0 \
    --server.port "$PORT" \
    --server.headless true