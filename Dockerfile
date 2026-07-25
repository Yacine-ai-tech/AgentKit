FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip uv && \
    uv pip install --system --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "mcp_server.py"]
