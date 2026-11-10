# 🏥 Smart Health Assistant Platform

An AI-powered health monitoring application that helps users manage medications, track fitness activities, record health measurements, set health goals, review health insights, and get simple risk estimates through a web dashboard.

## 📌 Project Information

| Detail | Description |
|---|---|
| Project | Smart Health Assistant Platform |
| Track | Track A – Core Features + Track B – Advanced Foundation |
| Domain | Smart Healthcare |
| AI Framework | LangChain |
| AI Model | Google Gemini |
| Backend | FastAPI |
| Frontend | React + Vite |
| Database | SQLite |
| Deployment | Render (planned or configured, depending on deployment status) |

## 🎯 Project Objective

The objective of this project is to build a health monitoring assistant that combines AI-based interaction with structured health data management, fitness tracking, medication records, analytics, and health reporting.

The platform provides a central place to record health information, monitor progress toward personal goals, and review summaries of stored data. It is designed to support health awareness and record keeping, not to replace professional medical advice.

## 🚀 Features

### 🤖 AI Health Assistant
- Accepts health-related questions and commands through a chat interface.
- Uses Google Gemini via LangChain, with tools for medications, readings, fitness, alerts and external health information.
- Answers general health questions (for example "What is diabetes?") using the NLM Clinical Tables API and its own knowledge.

### 💊 Medication Management
- Add, view, and remove medication records.
- Log doses and review dose history.
- View today's schedule with status (taken, due, missed, upcoming).
- Adherence monitoring with per-medication and overall percentages, missed-dose counts and streaks.

### ❤️ Health Metrics
- Record heart rate, blood pressure, blood sugar, temperature, weight and other readings.
- Readings are checked against safe ranges and generate alerts when they fall outside them.
- Import readings from JSON, CSV and XML files.

### 🏃 Fitness Tracking
- Record activities with type, duration, steps, distance, calories, sleep hours and notes.
- View recorded activities and a fitness summary.

### 🎯 Health Goals and Progress
- Daily or weekly goals with "at least" or "at most" targets.
- Manual logging, or automatic tracking from fitness activities.
- Progress percentage, status, streaks, success rate, trend and history.

### 📊 Health Analytics, Insights and Reports
- Summaries of stored health information and goal progress.
- Rule-based insights with a 0-100 wellness score. Each insight includes a suggestion and a disclaimer.
- Chart-ready data and reports as JSON, CSV download, or a printable page (save as PDF).

### 🚨 Real-time Alerts (Track B)
- After each saved reading, rules check the value against safe ranges (for example blood sugar above 250 mg/dL or SpO2 below 92%).
- Alerts are stored once per rule per hour, using a dedupe key, so repeated readings do not flood the list.
- The Wellness tab shows open alerts with an Acknowledge button.

### 🧠 ML Risk Estimate (Track B)
- A scaled logistic regression model estimates a "lower", "moderate" or "higher" risk level from five features: adherence, average blood sugar, average systolic blood pressure, average sleep and average steps.
- The model is trained on a small **synthetic** dataset generated in the code. It is a learning example, not a clinically validated predictor.
- Each estimate is saved to the `ml_predictions` table with its inputs, so results can be explained.

### 👨‍👩‍👧 Family Monitoring and Caregiver Notifications
- Consent-based caregiver links. A patient chooses what a caregiver can see: medications, fitness, or readings.
- Caregivers see summaries and receive notifications about missed doses and low adherence.

### 📚 Research Summaries (Track B)
- Summarises related conditions (NLM Clinical Tables) and FDA drug label information (OpenFDA) with Gemini.
- Gemini only rewrites the fetched text. It is instructed not to add facts, doses or diagnoses.

### 💊 Medication Interaction Endpoint
- Accepts medication names for interaction review.
- The current implementation does **not** use a verified drug-interaction database. Results are marked as unverified.

### 🌐 External Health and Wellness APIs
| Service | Used for | Key needed |
|---|---|---|
| NLM Clinical Tables | Related health conditions | No |
| OpenFDA | Drug label purpose, warnings and dosage | No (light use) |
| Open-Meteo Geocoding | Converts a city name to coordinates | No |
| Open-Meteo Air Quality | PM2.5, PM10, CO and NO2 for any city | No |
| wttr.in | Current weather | No |

All external calls go through `backend/services/http_client.py`, which sets timeouts, retries once on network or server errors, and returns readable errors.

## 🏗️ System Architecture

```text
                     User
                       |
                       v
               React + Vite UI
                       |
                       v
                FastAPI Backend
                       |
          +------------+------------+------------+
          |            |            |            |
          v            v            v            v
      Gemini AI    Health Tools  External APIs  ML Risk Model
          |            |            |            |
          +------------+------------+------------+
                       |
                       v
                SQLite Database
                       |
          +------------+------------+
          |            |            |
          v            v            v
       Analytics   Alerts & Goals   Reports
```

## 🛠️ Technology Stack

- **Python** — backend application logic
- **FastAPI** — REST API development
- **React** — user interface
- **Vite** — frontend development and build tooling
- **SQLite** — local health data storage
- **LangChain** — AI application framework
- **Google Gemini** — chat assistant and research summaries
- **scikit-learn** — logistic regression risk estimate
- **pytest** — automated tests

## 📂 Main Project Components

```text
project-root/
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── analytics.py
│   ├── reports.py
│   ├── services/
│   │   ├── http_client.py         # shared external API helper
│   │   └── api_services.py        # NLM, OpenFDA, weather, air quality
│   ├── tools/
│   │   └── health_info_tools.py   # LangChain tools for external APIs
│   ├── tests/
│   │   └── test_track_b.py        # Track B tests
│   └── wellness/
│       ├── router.py
│       ├── schema.py              # Week 5-6 tables
│       ├── schema_b.py            # Track B tables (profiles, alerts, predictions)
│       ├── adherence.py
│       ├── goals.py
│       ├── insights.py
│       ├── alerts.py              # real-time alert rules
│       ├── ml_risk.py             # logistic regression risk estimate
│       ├── research.py            # Gemini summaries
│       └── family.py
├── frontend-react/
│   └── src/
│       ├── App.jsx
│       └── WellnessTracker.jsx
├── src/
│   ├── database.py
│   └── scheduler.py
├── scripts/
│   └── seed_wellness_demo.py
├── data/
│   └── health.db
├── .env                           # API keys (not committed)
├── requirements.txt
└── README.md
```

## 🔌 Important API Endpoints

Core endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /health/summary` | Retrieve a health summary |
| `GET /analytics` | Retrieve health analytics |
| `GET /insights` | Retrieve health insights |
| `GET /medications` | Retrieve medication records |
| `GET /dose-history` | Retrieve medication dose history |
| `GET /health-metrics` | Retrieve health measurements |
| `GET /fitness-activities` | Retrieve fitness activity records |
| `POST /fitness-activities` | Record a fitness activity |
| `GET /fitness-summary` | Retrieve a fitness summary |
| `GET /health-goals` | Retrieve health goals |
| `POST /health-goals` | Create a health goal |
| `GET /health-goals/progress` | Retrieve goal progress |
| `POST /health-data/import` | Import health data files |
| `POST /medication-interactions` | Submit medication interaction checks |
| `GET /health-report` | Generate a health report |
| `POST /ask` | Ask the AI assistant |

Wellness tracker endpoints (Week 5-6, all require the Bearer token):

| Endpoint | Purpose |
|---|---|
| `GET /wellness/overview` | Score, 7-day adherence, today's doses, goals, unread notifications |
| `GET /wellness/adherence?days=30` | Adherence analytics |
| `POST /wellness/medications` | Add a medication |
| `POST /wellness/medications/{id}/dose` | Log today's dose |
| `GET /wellness/goals` / `POST /wellness/goals` | List or create goals |
| `POST /wellness/goals/{id}/log` | Log goal progress |
| `GET /wellness/visualization?days=14` | Chart datasets |
| `GET /wellness/insights` | Insights and wellness score |
| `GET /wellness/report?days=30` | Wellness report (JSON) |
| `GET /wellness/report/csv` | Report as CSV |
| `GET /wellness/report/printable` | Printable HTML report |
| `GET /wellness/family` | Caregiver links and requests |
| `GET /wellness/notifications` | Notifications |

Track B endpoints (all require the Bearer token):

| Endpoint | Purpose |
|---|---|
| `GET /wellness/alerts` | List open alerts |
| `POST /wellness/alerts/{id}/acknowledge` | Acknowledge an alert |
| `GET /wellness/risk` | ML risk estimate (saved to `ml_predictions`) |
| `GET /wellness/research?topic=diabetes` | Gemini summary of NLM and OpenFDA results |

Interactive API documentation is available through FastAPI's Swagger interface at `http://127.0.0.1:8000/docs`.

## ⚙️ Setup and Installation

### Prerequisites

- Python 3.11 or newer
- Node.js and npm
- A Google Gemini API key
- Git (optional)

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd YOUR_PROJECT_FOLDER
```

### 2. Set Up the Backend

Create and activate a virtual environment from the project root.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install scikit-learn numpy pytest
```

Create a `.env` file in the project root:

```text
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Start the backend (run this from the activated environment):

```powershell
python -m uvicorn backend.main:app --reload
```

Open the API documentation: `http://127.0.0.1:8000/docs`

### 3. Set Up the Frontend

In a separate terminal:

```powershell
cd frontend-react
npm install
npm run dev
```

Open the local URL shown by Vite.

### 4. Try it with demo data (optional)

```powershell
python scripts/seed_wellness_demo.py
```

This creates `demo_patient` and `demo_caregiver` (password `DemoPass123`) with three weeks of data.

## 🧪 Testing and Verification

Track B tests (external API helper, alert rules, risk model):

```powershell
python -m pytest backend/tests/test_track_b.py -v
```

Week 5-6 tests:

```powershell
python -m unittest backend.tests.test_wellness -v
```

Tests run without internet access for the external API helper, because `requests` is mocked.

Manually tested during development:
- Recording and retrieving fitness activities
- Importing health measurements from CSV
- Creating goals and retrieving progress
- Generating a health report
- Chat commands for medications, readings and alerts
- Alert creation and acknowledgement in the Wellness tab
- ML risk estimate and its saved history
- Research summaries for conditions and drug labels

## ⚠️ Known Limitations

- **Chatbot user scope:** the chatbot saves readings for the user set in a module-level variable (`CURRENT_USER_ID`). Two users chatting at the same moment could mix up readings. A safe fix would pass the user ID through each request.
- **Unscoped metrics endpoint:** `GET /health-metrics` returns readings for all users. It should be filtered by the logged-in user.
- **Synthetic ML data:** the risk model is trained on generated data and is for learning purposes only.
- **Medication interactions:** not checked against a verified clinical database.
- **Authentication tokens:** tokens expire, so log in again if you see `401 Unauthorized`.

## 🔐 Safety and Privacy

- Do not commit API keys, passwords, `.env` files, or private health records.
- Exclude virtual environments, `node_modules`, caches, and local database files from version control.
- Health summaries, insights, alerts and risk estimates are informational and are not a medical diagnosis.
- Consult a qualified healthcare professional for medication safety questions or serious health concerns.

## 🔮 Future Improvements

- Pass the user ID through each chat request instead of a module-level variable.
- Filter `/health-metrics` and other shared endpoints by user.
- Use a verified drug-interaction data source.
- Add real, consented training data for the risk model, with clinical validation.
- Add voice input and image-based analysis.
- Add automated tests for all API endpoints and file formats.
- Improve deployment configuration and production security.

## 👨‍💻 Project Status

Track A (core features and Medication & Wellness Tracker) and Track B (external APIs, schema additions, real-time alerts, ML risk estimate, research summaries and tests) are implemented and tested during development.

---

**Disclaimer:** This project is intended for health monitoring and educational purposes. It does not replace professional medical advice, diagnosis, or treatment.

## Week 7 implementation (React + FastAPI + AI agent)

The existing React/Vite frontend is retained; it is not replaced by another UI framework.
The React app calls the FastAPI backend, and the authenticated `/ask` chat endpoint now
runs through `backend.workflow.health_workflow` before invoking the AI agent. `/workflow`
is also available as an authenticated alias.

Week 7 improvements:
- The chat workflow validates blank, oversized (over 500 characters), and unsupported control-character input.
- The workflow passes the authenticated user ID into the agent.
- Agent user context uses a request-local context variable instead of a shared global, avoiding cross-user context leakage during concurrent requests.
- AI/provider failures return a safe user-facing fallback instead of exposing stack traces or provider details.
- Tool failures return a safe fallback message.
- The agent system instructions treat user/tool content as untrusted and prohibit disclosure of secrets or hidden instructions.
- React API URL can be configured with `frontend-react/.env` (`VITE_API_URL`); the default remains `http://127.0.0.1:8000`.

### Verify Week 7

1. Start the backend from the project root: `python -m uvicorn backend.main:app --reload`.
2. In another terminal, go to `frontend-react`, install dependencies with `npm install`, copy `.env.example` to `.env` if you need a custom API URL, then run `npm run dev`.
3. Open the Vite URL (normally `http://localhost:5173`), register/sign in, and open **AI assistant**.
4. Ask a normal question, such as `What health readings have I saved?`. The response should come through the workflow and agent.
5. Try submitting only spaces. The API should reject it with HTTP 422. Try a question longer than 500 characters; it should also be rejected.
6. Temporarily remove/rename `GOOGLE_API_KEY` and ask a question. The chat should show a safe temporary-unavailable response rather than a traceback. Restore the key afterwards.
7. Run backend tests from the project root: `python -m pytest backend/tests -q`. Run frontend checks from `frontend-react`: `npm run build` and `npm run lint`.

The AI assistant requires a valid provider API key for live model responses. Existing medication, fitness, reports, import, and wellness features remain in place.
