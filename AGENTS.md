# AI Agent Instructions (AGENTS.md)

This document provides essential guidelines, commands, and conventions for AI coding agents operating within the `realtimegamestatistics` repository. Adhere to these instructions to ensure consistency and safety.

## 🏗 Project Architecture
- **Backend**: Python (FastAPI) handling computer vision (YOLOv8, OpenCV), statistical analysis (XGBoost), and real-time WebSockets.
- **Frontend**: Next.js 15 (App Router) + TypeScript, styled with Tailwind CSS v4 and `shadcn/ui`. Also uses MUI (`@mui/material`), Recharts, and Motion.
- **Infrastructure**: Dockerized services (`docker-compose.yml`) including a `mediamtx` RTSP server.

---

## 🚀 Commands

### Backend (Python)
- **Environment**: Use a virtual environment (e.g., `backend/.venv`).
- **Install dependencies**: `pip install -r backend/requirements.txt`
- **Run local server**: `python backend/main.py` or `uvicorn backend.main:app --reload`
- **Testing**: Use `pytest`.
  - **All tests**: `pytest backend`
  - **Single file**: `pytest backend/tests/test_specific.py`
  - **Single test**: `pytest backend/tests/test_specific.py::test_function_name`
- **Linting**: `ruff check backend` or `flake8 backend`.
- **Note**: No test files currently exist; create them under `backend/tests/` when adding tests.

### Frontend (Node.js/Next.js)
- **Install dependencies**: `npm install` (within `frontend/`)
- **Run local server**: `npm run dev`
- **Build**: `npm run build`
- **Lint**: `npm run lint`
- **Type check**: `npx tsc --noEmit`
- **Testing**: No test framework is currently configured. Add `vitest` + `@testing-library/react` if tests are needed.

### Docker
- **Start all services**: `docker-compose up -d`
- **Build images**: `docker-compose build`
- **View logs**: `docker-compose logs -f`

---

## 📐 Code Style & Conventions

### Python (Backend)
- **Imports**: Absolute imports preferred (`from backend.api import ...`). Use `from __future__ import annotations` at the top of files.
- **Typing**: Mandatory type hints for all function signatures and public class members. Use `Optional`, `Union`, `list`, `dict` from `typing`.
- **Formatting**: PEP 8, 4-space indentation.
- **Naming**: `snake_case` for functions/variables; `PascalCase` for classes/Pydantic models.
- **Error Handling**: Use specific exceptions (`ValueError`, `ModuleNotFoundError`). For API errors, use FastAPI's `HTTPException`.
- **Patterns**: Use Pydantic models for request/response validation. Initialize large ML models once and share via dependency injection or global state.

### TypeScript/Next.js (Frontend)
- **Imports**: Use `@/` path alias (maps to `./src/`). Order: React/Next imports → third-party libs → `@/components` → `@/hooks` → `@/utils` → types.
- **Typing**: Strict mode enabled. Avoid `any`. Define `interface` or `type` for all props and API responses.
- **Components**: Functional components only. Use `"use client"` directive strictly for interactive components (hooks, state, events).
- **Formatting**: 2-space indentation, semicolons, single quotes, trailing commas.
- **Naming**: `PascalCase` for components/interfaces; `camelCase` for hooks/utilities/variables.
- **UI**: Use `shadcn/ui` from `@/components/ui/`. Merge Tailwind classes with `cn(...)`. MUI components are also available for complex layouts.
- **Layout**: Home page (`/`) must be pitch-centric with `h-screen overflow-hidden` for non-scrollable viewport.

---

## 🤖 Agent Execution Mandates

1. **Absolute Paths**: Always use absolute paths when calling file tools.
2. **Read Before Writing**: Always read the file and surrounding context before editing.
3. **Verify Dependencies**: Check `package.json` or `requirements.txt` before adding libraries.
4. **No Side Effects**: Do not modify `.env` files or global configs without explicit consent.
5. **Self-Verification**: After editing, run `npm run build` (frontend) or relevant lint command to catch errors.
6. **Type Safety**: Ensure `npx tsc --noEmit` passes before considering a frontend task complete.

---

## 🛡 Security & Safety
- **Secrets**: NEVER hardcode API keys, credentials, or private IPs. Use `.env` files and `os.environ.get()` / `process.env`.
- **Permissions**: Do not run destructive commands without explicit user consent.
- **No Cursor/Copilot rules**: This repo has no `.cursorrules`, `.cursor/rules/`, or `.github/copilot-instructions.md`.
