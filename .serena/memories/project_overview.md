# Kalshi Analysis Project Overview

## Project Purpose
Portfolio-quality demonstration of quantitative trading strategy development for Kalshi prediction markets. Showcases data science rigor, full-stack engineering, and disciplined architecture evolution.

## Current Phase
**Phase 1: Local Analytics Workbench** (2-week timeline)
- Goal: Validate strategy viability through backtesting
- Success Criteria: Backtest ≥1 strategy with Sharpe ratio >0.5

## Phased Development Strategy

### Phase 1: Local Analytics Workbench (Current)
- Single-user local tool
- REST API only (no GraphQL)
- 5-second polling of Kalshi API (no WebSocket)
- PostgreSQL for market snapshots
- Jupyter notebooks for strategy development
- Docker Compose deployment

### Phase 2: Real-Time Monitoring (If Phase 1 validates)
- Add WebSocket connection to Kalshi
- Live order book visualization
- Real-time strategy performance dashboard
- Still single-user, local-first

### Phase 3: Automated Trading Bot (If strategies profitable)
- Event-driven trade execution (Cloud Tasks or Celery)
- GCP deployment (Cloud Run + Cloud SQL)
- Secret Manager for API keys
- Monitoring and alerting
- Multi-environment (local dev + GCP prod)

### Phase 4: Multi-User SaaS (If market demand exists)
- User authentication (Firebase Auth)
- GraphQL layer (Strawberry)
- Redis caching
- Horizontal scaling

## Technology Stack (Phase 1)

### Backend
- FastAPI (REST APIs only)
- Pydantic v2 for data models and validation
- PostgreSQL for market snapshots and backtest results
- SQLAlchemy ORM (async)
- httpx for Kalshi API client
- Uvicorn + Docker

### Frontend
- React + Vite + TypeScript
- Tanstack Query (REST data fetching, NOT Apollo/GraphQL)
- TailwindCSS + shadcn/ui components
- Recharts for basic visualizations

### Data Science
- Jupyter notebooks
- pandas/numpy for data analysis
- backtrader or vectorbt for backtesting
- matplotlib/seaborn for visualization

## Key Design Principles
1. **Phased Complexity:** Prove value before adding sophistication
2. **Type Safety Throughout:** Pydantic + TypeScript
3. **Data Science First:** Notebooks drive strategy development
4. **Cloud-Ready from Day 1:** Docker, environment configs, GCP patterns
5. **Simplicity First, Complexity When Justified:** No premature optimization

## User Background
- Data scientist with strong Python skills
- Less familiar with FastAPI and React
- Portfolio demonstration project
- Will evolve from weekend prototype to production if profitable
