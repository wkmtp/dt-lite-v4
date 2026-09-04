"""
DT-Lite IoT Service - 设备接入
负责：Device, Protocol, Connection
"""
from fastapi import FastAPI

app = FastAPI(title="DT-Lite IoT Service", version="4.0.0")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
