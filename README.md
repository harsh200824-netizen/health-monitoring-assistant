# 🏥 Smart Health Assistant Platform

An AI-powered health monitoring application that helps users manage medications, track fitness activities, record health measurements, set health goals, and review health insights through a web dashboard.

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
- Accepts health-related questions through the application's assistant interface.
- Uses the configured AI integration to help answer general health questions.
- Supports a conversational interface for interacting with the system.

### 💊 Medication Management
- Add, view, and manage medication records.
- Track medication doses and review dose history.
- View active medications and doses recorded for the current day.

### ❤️ Health Metrics
- Record measurements such as heart rate, blood pressure, blood sugar, temperature, and weight, where supported by the application.
- Store measurements in the SQLite database.
- Retrieve health metric records for analytics and reporting.

### 🏃 Fitness Tracking
- Record fitness activities with details such as activity type, duration, steps, distance, calories burned, sleep hours, and notes.
- View recorded activities.
- Retrieve a fitness summary for monitoring activity totals.

### 🎯 Health Goals and Progress
- Create health goals with measurable targets.
- Track progress against supported daily goals.
- View current values, target values, and progress percentages.

### 📊 Health Analytics
- View summaries of stored health information.
- Review medication counts, dose records, and recent health measurements.
- Combine fitness summaries and goal progress for a broader overview.

### 💡 Health Insights
- Generate basic insights from available health records.
- Help users review their recorded information and identify areas to monitor.

### 📁 Health Data Import
- Import health metric records from JSON, CSV, and XML files.
- Validate supported file formats and record fields.
- Save valid imported measurements to the database.
- Report imported and skipped record counts.

### 📄 Health Report Generation
- Generate a health report containing a health summary, analytics, fitness information, and goal progress.
- Include a report timestamp and a medical disclaimer.

### 💊 Medication Interaction Endpoint
- Provides an endpoint for submitting medication names for interaction-review handling.
- The current implementation does **not** use a verified drug-interaction database.
- Results are explicitly marked as unverified and recommend review by a pharmacist or doctor.

### 🎤 Voice Input
- Supports voice input for health queries where the existing frontend and browser support it.

### 🌐 External Integrations
- The project includes integration code for configured AI and external health-related services.
- Actual availability depends on the configured credentials, API access, and environment settings.

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
          +------------+------------+
          |            |            |
          v            v            v
      AI Services   Health Tools   API Services
          |            |            |
          +------------+------------+
                       |
                       v
                SQLite Database
                       |
          +------------+------------+
          |            |            |
          v            v            v
       Analytics   Fitness Data   Health Goals
          |
          v
      Health Reports
```

## 🛠️ Technology Stack

- **Python** — backend application logic
- **FastAPI** — REST API development
- **React** — user interface
- **Vite** — frontend development and build tooling
- **SQLite** — local health data storage
- **LangChain** — AI application framework
- **Google Gemini** — configured AI model integration

## 📂 Main Project Components

```text
project-root/
├── backend/
│   ├── main.py
│   ├── analytics.py
│   ├── insights.py
│   ├── reports.py
│   ├── database/
│   ├── services/
│   └── tools/
├── frontend-react/
│   └── src/
│       └── App.jsx
├── src/
│   └── database.py
├── data/
│   └── health.db
├── requirements.txt
└── README.md
```

*The exact folder structure may vary slightly depending on the current project version.*

## 🔌 Important API Endpoints

The following endpoints have been implemented and tested during development:

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

Interactive API documentation is available through FastAPI's Swagger interface.

## ⚙️ Setup and Installation

### Prerequisites

- Python installed
- Node.js and npm installed
- Git installed (optional, for version control)

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd YOUR_PROJECT_FOLDER
```

Replace the placeholders with your actual repository URL and folder name.

### 2. Set Up the Backend

Create and activate a virtual environment from the project root.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the backend:

```powershell
python -m uvicorn backend.main:app --reload
```

Open the API documentation:

```text
http://127.0.0.1:8000/docs
```

### 3. Set Up the Frontend

Open a separate terminal:

```powershell
cd frontend-react
npm install
npm run dev
```

Open the local URL displayed by Vite in your terminal.

*If the project requires environment variables, configure them using the provided example configuration and keep actual secrets out of GitHub.*

## 🧪 Testing and Verification

During development, the following workflows were tested successfully:

- Recording fitness activities and retrieving them.
- Importing health measurements from CSV.
- Creating health goals and retrieving their progress.
- Generating a health report containing summary, analytics, fitness, and goal information.
- Calling the medication interaction endpoint and receiving its unverified-status response.
- Testing the end-to-end monitoring workflow through the API.

JSON and XML imports are supported by the implementation and should also be tested when validating a fresh installation.

## 🔐 Safety and Privacy

- Do not commit API keys, passwords, `.env` files, or private health records.
- Exclude virtual environments, `node_modules`, caches, and local database files from version control where appropriate.
- Health summaries and generated insights are informational and are not a medical diagnosis.
- The medication interaction endpoint does not currently verify drug interactions against a clinical database.
- Users should consult a qualified healthcare professional for medication safety questions or serious health concerns.

## 🔮 Future Improvements

- Integrate a reliable, verified medication interaction data source.
- Improve interactive health charts and dashboard customization.
- Add authentication and secure user-specific health records.
- Add automated tests for all API endpoints and file formats.
- Improve deployment configuration and production security.
- Add more advanced trends and goal-progress visualizations.

## 👨‍💻 Project Status

The core health monitoring workflow has been tested successfully, including fitness tracking, health data import, goal tracking, analytics, and report generation.

Further improvements to the frontend, testing, security, and verified medical data integrations can be made as the project develops.

---

**Disclaimer:** This project is intended for health monitoring and educational purposes. It does not replace professional medical advice, diagnosis, or treatment.