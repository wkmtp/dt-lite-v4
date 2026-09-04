"""
DT-Lite AI Service - 智能层
负责：Agent, Tool, RAG
"""
from fastapi import FastAPI

app = FastAPI(title="DT-Lite AI Service", version="4.0.0")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
