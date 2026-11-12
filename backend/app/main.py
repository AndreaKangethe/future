from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="Deepsight API",
    version="0.1.0",
    description="Machine Learning-Driven Attack Surface Intelligence and Vulnerability Management Platform.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "deepsight-backend"}


@app.get("/readyz")
async def readyz():
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    return "# HELP deepsight_up Backend health\n# TYPE deepsight_up gauge\ndeepsight_up 1\n"
