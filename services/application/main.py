"""
DT-Lite Application Service - 低代码应用
负责：Page, Widget, Template
"""
from fastapi import FastAPI

app = FastAPI(title="DT-Lite Application Service", version="4.0.0")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
