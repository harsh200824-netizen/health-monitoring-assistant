# Quick Start — Windows 11 / VS Code

## 1. Open the project
Extract this ZIP, then open the `health-monitoring-agent-main` folder in VS Code.

## 2. Start the backend
Open a VS Code terminal at the project root and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Keep this terminal open. Check the API in your browser at `http://127.0.0.1:8000/health`.
Expected response: `{"status":"healthy"}`.

If PowerShell blocks activation, run this in the same terminal, then activate again:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Start the React frontend
Open a **second** VS Code terminal and run:

```powershell
cd frontend-react
npm install
npm run dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`).

## Notes
- Do not share `.env`, API keys, passwords, or secret tokens.
- This ZIP includes the existing app and a dependency-name correction for FastAPI file uploads.
- The frontend build could not be verified in the current execution environment because the local Vite executable returned `Permission denied`. Run `npm install` on your Windows machine before `npm run dev`.
- The app's current API code does not yet implement the authentication and per-user health-data isolation described in the separate handover notes. Do not use it with real or sensitive health records until that security work is completed and tested.
