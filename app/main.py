from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import Base, engine
from .routers import classify_router, users_router, sessions_router, moderation_router, metrics_router, playground_router
from .websocket.router import router as ws_router
from .services import classifier


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Load ML model (non-fatal if missing — returns 503 on classify)
    try:
        classifier.load_model()
    except FileNotFoundError as e:
        print(f"[WARN] Model not loaded: {e}. /classify will return 503 until the model is present.")

    yield


app = FastAPI(
    title="Toxic Chat Detector",
    description="Detección de Toxicidad en Chats de Videojuegos — Universidad Militar Nueva Granada",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins in dev — tighten to your frontend URL in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"

app.include_router(classify_router, prefix=PREFIX)
app.include_router(users_router, prefix=PREFIX)
app.include_router(sessions_router, prefix=PREFIX)
app.include_router(moderation_router, prefix=PREFIX)
app.include_router(metrics_router, prefix=PREFIX)
app.include_router(ws_router)  # WebSocket routes have no prefix — /ws/...
app.include_router(playground_router, prefix=PREFIX)


@app.get(f"{PREFIX}/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "model_loaded": classifier.is_model_loaded(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {"code": "INTERNAL_ERROR", "message": str(exc)},
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
