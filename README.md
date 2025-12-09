# SkyMate — AI Travel Assistant (Local / VSCode)

A full-stack app (React + Node proxy + Flask Python agent) for conversational flight search.
These instructions are for running locally in VSCode on Windows (PowerShell) or macOS (bash) — not Replit.

## Repo layout (important)
- server/ — Node/Express server + Vite middleware
- client/ — React app (Vite)
- python_backend/ — Flask API & agent
- script/ — build utilities
- shared/ — shared types

## Prerequisites
- Node.js >= 18 and npm
- Python 3.11
- Git (recommended)
- (Optional) PostgreSQL if you use DB features

## Environment variables

Create a `.env` in the project root with:
```
OPENAI_API_KEY=your_openai_api_key_here
AMADEUS_API_KEY=your_amadeus_api_key_here
AMADEUS_API_SECRET=your_amadeus_api_secret_here
PYTHON_BACKEND_PORT=5001
PYTHON_BACKEND_URL=http://localhost:5001
PORT=5000
DATABASE_URL=postgres://user:password@localhost:5432/travel_db
```

## Install (from project root)

### 1) Install Node deps
```powershell
npm install
```

### 2) Setup Python venv (in project root)

**PowerShell (Windows)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS (bash)**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (development)

### Option A — Single command (recommended)
```powershell
npm run dev
```
This starts the Node server + Vite dev and automatically launches the Python backend. Open http://localhost:5000 in your browser.

### Option B — Manual (two terminals)

**Terminal 1 — Python (PowerShell)**
```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHON_BACKEND_PORT=5001
python python_backend/app.py
```

**Terminal 2 — Node / Vite (PowerShell)**
```powershell
npm run dev
```

Open http://localhost:5000 (or the PORT value in env).

## Build / Production (PowerShell)
```powershell
npm run build
npm run start
```
Ensure the Python backend is reachable at `PYTHON_BACKEND_URL` (deploy separately if needed).

## Removing Replit artifacts (PowerShell)

Recommended manual items to remove (if present):
- .replit
- replit.md
- replit.nix

**Inspect then remove (PowerShell)**
```powershell
git status --porcelain
git rm --ignore-unmatch .replit replit.md replit.nix
git commit -m "chore: remove Replit artifacts"
```

## Troubleshooting
- Ports: Node default PORT (5000) and Python backend default 5001. Change in `.env` if conflict.
- Verify `PYTHON_BACKEND_URL` and that Python app is running if proxy calls fail.
- If Vite dev errors, ensure Node deps installed.
- If Python venv doesn't activate: check that `.venv` exists in the project root, or recreate it with `python -m venv .venv`

## VSCode refresh
- Click Explorer refresh icon or use Command Palette → "Developer: Reload Window" to see new files.

## Architecture & Overview

For details on the app architecture, features, and components, see [ARCHITECTURE.md](Travel-assistant/ARCHITECTURE.md).

## Next Steps

If you want a VSCode tasks.json / launch.json to run both Node and Python automatically, I can add it.
