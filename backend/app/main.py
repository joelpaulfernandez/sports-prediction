from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import predictions, accuracy

app = FastAPI(
    title="StatCast — Sports Prediction API",
    description="NBA game predictions powered by XGBoost and real-time stats.",
    version="1.0.0",
)

# Allow the Vite dev server to call the API
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
    return {"status": "ok", "message": "StatCast API is running."}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}
