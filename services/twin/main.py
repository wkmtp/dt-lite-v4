"""
DT-Lite Twin Service - 数字孪生运行
负责：Scene, Model, Binding
"""
from fastapi import FastAPI

app = FastAPI(title="DT-Lite Twin Service", version="4.0.0")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
