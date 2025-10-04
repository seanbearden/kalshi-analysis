# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This repository is in **initial planning phase**. The README.md contains comprehensive architectural documentation for a Kalshi market insights application, but the implementation is not yet started. The planned directory structure includes:

- `frontend/` — React + Vite + TypeScript + Apollo GraphQL (not yet created)
- `backend/` — FastAPI + Strawberry GraphQL + Pydantic (not yet created)
- `notebooks/` — Data science workflows for backtesting and calibration (not yet created)
- `infra/` — Docker and CI configuration (not yet created)
- `data/` — Seed and demo datasets (not yet created)

## When Creating Initial Structure

Follow the architecture specified in README.md:

### Backend Setup
```bash
mkdir -p backend
cd backend
# Create requirements.txt with: FastAPI, Strawberry GraphQL, Pydantic v2, Uvicorn, PostgreSQL driver
pip install -r requirements.txt
uvicorn api.main:app --reload  # After creating api/main.py
```

### Frontend Setup
```bash
mkdir -p frontend
cd frontend
pnpm install  # After creating package.json
pnpm dev      # Runs on http://localhost:5173
```

### Environment Configuration

**backend/.env**:
- `KALSHI_API_BASE` — Kalshi demo API endpoint
- `KALSHI_WS_URL` — WebSocket URL for real-time data
- `DB_URL` — PostgreSQL connection string

**frontend/.env**:
- `VITE_API_URL` — Backend API endpoint
- `VITE_WS_URL` — WebSocket endpoint

## Technology Requirements

- **Python**: ≥ 3.11
- **Node.js**: ≥ 22
- **Package Manager**: pnpm (frontend)
- **Database**: PostgreSQL (primary), Redis (optional for caching)

## Code Quality Integration

This repository is configured with **Codacy MCP Server** integration. After editing any file:

1. Run `codacy_cli_analyze` for each modified file
2. If security vulnerabilities are found in dependencies, fix them before proceeding
3. Do not proceed without resolving critical issues

Key Codacy rules:
- Automatic analysis required after all file edits
- Security scans mandatory after dependency changes
- Use `codacy_cli_install` if CLI is not available

## 🚨 CRITICAL GIT RULES

### NEVER use `git commit --no-verify`

**Pre-commit hooks exist for a reason.** If pre-commit hooks are failing:

1. **FIX THE ISSUE** - Don't bypass it
2. **FIX THE HOOK** - If the hook is broken, fix the hook configuration
3. **NEVER BYPASS** - Using `--no-verify` defeats the entire purpose of quality gates

**If you find yourself wanting to use `--no-verify`:**
- STOP
- Identify why the hook is failing
- Fix the actual problem
- Commit properly with hooks running

This is non-negotiable. Quality gates are there to catch issues before they reach CI/CD.

## Architecture Principles from README

- **Type safety**: Pydantic (backend) + TypeScript (frontend) + GraphQL schemas
- **Incremental delivery**: REST → WebSocket → GraphQL overlay
- **Resilient real-time**: Snapshot + delta replay for order book recovery
- **Testing**: Deterministic WebSocket replay fixtures, Pytest + Hypothesis (backend), Vitest (frontend)
- **Simplified stack**: PostgreSQL first, avoid premature infrastructure complexity

## Key Features to Implement

1. **Market Data**: Kalshi events, markets, order books, trades via REST and WebSocket
2. **Real-time Visualization**: Order book depth, trade tape, candlestick charts
3. **Data Science**: Implied probabilities, calibration plots, backtesting with PnL/Sharpe/drawdown
4. **GraphQL Layer**: Typed resolvers for markets, orderbooks, candles, backtest results
5. **Reliability Diagram**: Visual calibration quality component

## Development Experience Goals

- Local-first development with Docker Compose
- Pre-commit hooks: Ruff, Black (Python), ESLint, Prettier (TypeScript)
- Hot reload for both frontend and backend
- Replayable demo data for offline showcasing
- `make demo` command for one-click local launch

## Portfolio Context

This is a **portfolio-quality demonstration** project showcasing:
- Data engineering and quantitative analytics expertise
- Modern full-stack architecture (FastAPI + React)
- Software engineering discipline (type safety, testing, CI/CD)
- Frontend craftsmanship (shadcn/ui, Framer Motion, TailwindCSS)

Not intended as a production trading tool.
