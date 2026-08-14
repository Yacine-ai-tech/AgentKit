import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from agentkit_mcp.web_app import build_app
app = build_app()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
