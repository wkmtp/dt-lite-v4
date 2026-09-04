"""
DT-Lite Telemetry Service - 数据处理
负责：实时数据, 历史数据
"""
from fastapi import FastAPI

app = FastAPI(title="DT-Lite Telemetry Service", version="4.0.0")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
