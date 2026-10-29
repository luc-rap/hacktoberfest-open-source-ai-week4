
#!/bin/sh
set -e

exec streamlit run /app/the-house-that-remembers/app.py \
    --server.address 0.0.0.0 \
    --server.port "$PORT" \
    --server.headless true