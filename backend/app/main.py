import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import predictions, accuracy
from app.config import get_settings
from app.services.prediction_engine import get_prediction_engine


async def _auto_train():
    """Run model training in the background if no model file is present."""
    try:
        from app.services.model_trainer import train_and_save
        settings = get_settings()
        print("[startup] Starting model training (this takes ~3-5 min on first run)…")
        result = await asyncio.to_thread(train_and_save, settings.model_path)
        if result:
            get_prediction_engine().reload_model()
            print(
                f"[startup] Training done — CV accuracy: {result['cv_accuracy']:.3f} "
                f"over {result['n_games']} games."
            )
    except Exception as exc:
        print(f"[startup] Training failed: {exc}")


async def _resolve_yesterday():
    """Check yesterday's predictions against real results."""
    try:
        import httpx
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            r = await client.post("/api/accuracy/update")
            data = r.json()
            if data.get("updated", 0) > 0:
                print(f"[startup] Accuracy update: {data['message']}")
    except Exception:
        pass   # non-critical; server may not be reachable yet on first boot


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_prediction_engine()
    if not engine.is_trained:
        asyncio.create_task(_auto_train())
    else:
        print(
            f"[startup] Loaded {engine.model_version} "
            f"(CV accuracy: {engine.cv_accuracy:.3f})"
        )

    # Resolve yesterday's predictions in the background
    asyncio.create_task(_resolve_yesterday())

    yield


app = FastAPI(
    title="StatCast — Sports Prediction API",
    description="NBA game predictions powered by XGBoost and real-time NBA stats.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router)
app.include_router(accuracy.router)


@app.get("/", tags=["health"])
async def root():
    engine = get_prediction_engine()
    return {
        "status": "ok",
        "message": "StatCast API v2 — powered by XGBoost + nba_api",
        "model_version": engine.model_version,
        "model_cv_accuracy": engine.cv_accuracy,
    }


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}
