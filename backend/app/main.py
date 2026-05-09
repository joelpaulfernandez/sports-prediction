import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import predictions, accuracy, bracket
from app.api.routes import f1 as f1_routes
from app.config import get_settings
from app.services.prediction_engine import get_prediction_engine
from app.services import nba_data


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
        from app.api.routes.accuracy import update_accuracy
        data = await update_accuracy()
        if data.get("updated", 0) > 0:
            print(f"[startup] Accuracy update: {data['message']}")
    except Exception:
        pass


async def _refresh_predictions():
    """
    Rebuild the prediction cache for today and resolve any newly finished games
    against accuracy_log. Called at startup and every 5 min.
    """
    try:
        from app.api.routes.predictions import warm_predictions
        from app.api.routes.accuracy import update_accuracy
        import datetime as dt
        await warm_predictions(str(dt.date.today()))
        result = await update_accuracy()
        if result.get("updated", 0) > 0:
            print(f"[warming] Resolved {result['updated']} prediction(s) into accuracy_log.")
    except Exception as exc:
        print(f"[warming] Refresh failed: {exc}")


async def _resolve_f1_accuracy():
    """Score completed F1 races against stored predictions."""
    try:
        from app.api.routes.f1 import resolve_f1_accuracy
        n = await asyncio.to_thread(resolve_f1_accuracy)
        if n > 0:
            print(f"[startup] F1 accuracy: resolved {n} race(s).")
    except Exception as exc:
        print(f"[startup] F1 accuracy resolution failed: {exc}")


async def _auto_train_f1():
    """Train F1 ranker in background if no model file present (~5 min)."""
    try:
        from app.services.f1_model_trainer import train_f1_and_save, get_f1_model_path
        import os
        if os.path.exists(get_f1_model_path()):
            return
        print("[startup] Starting F1 model training (~5 min)…")
        result = await asyncio.to_thread(train_f1_and_save)
        if result:
            from app.services.f1_prediction_engine import get_f1_prediction_engine
            get_f1_prediction_engine().reload_model()
            metrics = result.get("validation_metrics", {})
            print(
                f"[startup] F1 training done — "
                f"winner_acc: {metrics.get('winner_accuracy', '?')}, "
                f"spearman: {metrics.get('avg_spearman', '?')}"
            )
    except Exception as exc:
        print(f"[startup] F1 training failed: {exc}")


async def _nightly_retrain():
    """Retrain XGBoost on historical seasons + current season completed games."""
    print("[retrain] Nightly retrain starting…")
    try:
        from app.services.model_trainer import train_and_save, TRAINING_SEASONS
        seasons = TRAINING_SEASONS + [nba_data.CURRENT_SEASON]
        result = await asyncio.to_thread(train_and_save, None, seasons)
        if result:
            get_prediction_engine().reload_model()
            print(
                f"[retrain] Done — CV accuracy: {result['cv_accuracy']:.3f} "
                f"over {result['n_games']} games across {len(seasons)} seasons."
            )
        else:
            print("[retrain] Training returned no result — model unchanged.")
    except Exception as exc:
        print(f"[retrain] Failed: {exc}")


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

    asyncio.create_task(_resolve_yesterday())
    asyncio.create_task(_auto_train_f1())
    asyncio.create_task(_resolve_f1_accuracy())

    # Pre-warm the prediction cache so the first user request is instant
    asyncio.create_task(_refresh_predictions())

    # Schedule periodic jobs
    scheduler = None
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
        scheduler = AsyncIOScheduler()
        scheduler.add_job(_refresh_predictions, IntervalTrigger(minutes=5))
        scheduler.add_job(_nightly_retrain, CronTrigger(hour=8, minute=0, timezone="UTC"))
        scheduler.start()
        print("[startup] Scheduler started — predictions refresh every 5 min, retrain at 04:00 ET.")
    except Exception as exc:
        print(f"[startup] Scheduler setup failed: {exc}")

    yield

    if scheduler and scheduler.running:
        scheduler.shutdown()


app = FastAPI(
    title="StatCast — Sports Prediction API",
    description="NBA game predictions powered by XGBoost and real-time NBA stats.",
    version="2.0.0",
    lifespan=lifespan,
)

_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_settings = get_settings()
if _settings.frontend_url and _settings.frontend_url not in _origins:
    _origins.append(_settings.frontend_url)

# Restrict to deploying account's Vercel previews only.
# Override via ALLOWED_ORIGIN_REGEX env var for other deployments.
_origin_regex = (
    _settings.allowed_origin_regex
    or r"https://sports-prediction-[a-z0-9]+-joelpaulfernandezs-projects\.vercel\.app"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router)
app.include_router(accuracy.router)
app.include_router(bracket.router)
app.include_router(f1_routes.router)


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
