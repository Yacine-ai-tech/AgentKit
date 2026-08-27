import os
import sys

from agentkit_mcp.web_app import build_app

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
app = build_app()
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
