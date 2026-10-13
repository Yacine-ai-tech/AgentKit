FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# CPU-only PyTorch first: the default Linux wheel bundles CUDA libraries that add several
# gigabytes and are never used here.
RUN pip install --upgrade pip uv && \
    uv pip install --system --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    uv pip install --system --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "mcp_server.py"]
