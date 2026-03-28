# StatCast — NBA Sports Prediction App

StatCast predicts NBA game outcomes using an XGBoost model trained on real-time stats from the [API-Sports](https://api-sports.io) basketball API. Each prediction comes with a confidence score and three plain-English reasons explaining why the model picked that winner.

---

## Project Structure

```
sports-prediction/
├── backend/        Python + FastAPI prediction API
└── frontend/       React + TypeScript + Vite web app
```

---

## Running the Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your API keys

# Start the dev server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive API docs: `http://localhost:8000/docs`

---

## Running the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy and fill in environment variables
cp .env.example .env

# Start the Vite dev server
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable         | Description                                      |
|------------------|--------------------------------------------------|
| `SPORTS_API_KEY` | API key from [api-sports.io](https://api-sports.io) |
| `SUPABASE_URL`   | Your Supabase project URL                        |
| `SUPABASE_KEY`   | Your Supabase anon/service key                   |
| `REDIS_URL`      | Redis connection URL (default: `redis://localhost:6379`) |

### Frontend (`frontend/.env`)

| Variable        | Description                                 |
|-----------------|---------------------------------------------|
| `VITE_API_URL`  | Base URL of the backend API (default: `http://localhost:8000`) |

---

## API Endpoints

| Method | Path                              | Description                          |
|--------|-----------------------------------|--------------------------------------|
| GET    | `/api/predictions/games`          | All NBA predictions for today        |
| GET    | `/api/predictions/games/{game_id}`| Single game prediction               |
| GET    | `/api/accuracy`                   | Historical model accuracy stats      |
| GET    | `/health`                         | Health check                         |

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, XGBoost, scikit-learn, httpx, Pydantic v2
- **Frontend**: React 19, TypeScript, Vite, Axios
- **Data**: API-Sports (api-sports.io) NBA basketball data
- **Storage**: Supabase (Postgres), Redis (caching)

---

## Notes

- If no `SPORTS_API_KEY` is set, the app falls back to realistic mock data so the UI is always functional during development.
- The XGBoost model falls back to a rule-based predictor (win-percentage comparison with home-court adjustment) until enough training data is available.
- Historical prediction outcomes are stored in `backend/app/data/accuracy_log.json`.
