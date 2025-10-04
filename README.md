# Kalshi Market Insights App

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/node.js-22+-green.svg)](https://nodejs.org/)
[![codecov](https://codecov.io/gh/seanbearden/kalshi-analysis/graph/badge.svg?token=4RQ1KYTXFK)](https://codecov.io/gh/seanbearden/kalshi-analysis)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![TypeScript](https://img.shields.io/badge/TypeScript-Ready-3178C6.svg)](https://www.typescriptlang.org/)

A **phased evolution** from local analytics workbench to cloud-deployed trading platform — showcasing **data science rigor**, **full-stack engineering**, and **disciplined architecture** that grows with business value.

**Current Phase:** Phase 1 (Local Analytics Workbench)

---

## 🎯 Purpose

This project demonstrates:

* **Data science depth** — backtesting, calibration analysis, and quantitative strategy development
* **Architectural discipline** — simplicity first, complexity when justified by value
* **Full-stack capability** — Python (FastAPI) backend + React/TypeScript frontend
* **Production readiness** — type safety, testing, and cloud deployment patterns (GCP)

**Portfolio Value:** Shows evolution from exploration → validation → automation → scale

**Not a Production Trading Tool** — This is for strategy research and skill demonstration.

---

## 🧩 Architecture Overview

```text
kalshi-analysis/
  frontend/                # React + Vite + TypeScript (Phase 1: REST only)
  backend/                 # FastAPI + Pydantic (REST APIs)
  notebooks/               # Data science workflows (backtesting, calibration)
  infra/                   # Docker Compose for local dev
  data/                    # Market snapshots and backtest results
```

### Core Design Principles

✅ **Phased complexity** — Start simple (REST + polling), add sophistication when value is proven
✅ **Type safety everywhere** — Pydantic (backend) + TypeScript (frontend)
✅ **Data science first** — Notebooks drive strategy development, backend productionizes
✅ **PostgreSQL foundation** — Sufficient for phases 1-3, familiar, cloud-ready
✅ **Docker from day 1** — Reproducible environments, GCP deployment readiness

---

## 🗺️ Phased Development Roadmap

### **Phase 1: Local Analytics Workbench** (Current — 2 weeks)
**Goal:** Validate strategy viability through backtesting

**Stack:**
- Backend: FastAPI + Pydantic + PostgreSQL (REST only, 5s polling)
- Frontend: React + TypeScript + Tanstack Query + shadcn/ui + Recharts
- Data Science: Jupyter notebooks + pandas/numpy + backtrader/vectorbt
- Deployment: Docker Compose (local only)

**Success Criteria:** Backtest ≥1 strategy with Sharpe ratio >0.5

---

### **Phase 2: Real-Time Monitoring** (If Phase 1 validates)
**Add:**
- WebSocket connection to Kalshi (simple append-only)
- Live order book visualization
- Real-time strategy performance dashboard

**Still:** Single-user, local-first development

---

### **Phase 3: Automated Trading Bot** (If strategies profitable)
**Add:**
- Event-driven trade execution (Cloud Tasks or Celery)
- GCP deployment (Cloud Run + Cloud SQL)
- Secret Manager for API keys
- Monitoring and alerting

**Now:** Multi-environment (local dev + GCP prod)

---

### **Phase 4: Multi-User SaaS** (If market demand exists)
**Add:**
- User authentication (Firebase Auth)
- GraphQL layer (Strawberry) for flexible querying
- Redis caching
- Horizontal scaling

---

## 🧠 Key Features (by Phase)

### Phase 1: Analytics Foundation
* ✅ Fetch Kalshi **events, markets, and order books** via REST API (5s polling)
* ✅ Store market snapshots in PostgreSQL for historical analysis
* ✅ Jupyter notebooks for **strategy development and backtesting**
* ✅ Backtesting engine (**backtrader** or **vectorbt**) with PnL, Sharpe, drawdown metrics
* ✅ Simple frontend displaying markets in **shadcn/ui** DataTable
* ✅ **Reliability diagrams** — calibration quality visualization
* ✅ Docker Compose for reproducible local development

### Phase 2: Real-Time Monitoring (Planned)
* Real-time **order book depth** and **trade tape** via WebSocket
* Interactive **candlestick charts** (Recharts) with historical data
* Live strategy performance dashboard
* Market health metrics: liquidity, spread, volatility

### Phase 3: Automated Trading (Planned)
* Event-driven trade execution on market triggers
* GCP deployment (Cloud Run + Cloud SQL + Secret Manager)
* Monitoring, alerting, and logging for bot health
* Production-grade error handling and recovery

### Phase 4: Multi-User Platform (Planned)
* GraphQL API layer (Strawberry) for flexible querying
* User authentication and authorization
* Redis caching for performance
* Horizontal scaling on GCP

### Developer Experience (All Phases)
* Type safety: Pydantic + TypeScript
* Pre-commit hooks: Ruff, ESLint, Prettier
* Hot reload for backend and frontend
* `make demo` command for one-click local launch

---

## 🧮 Tech Stack

### Phase 1 (Current)

**Frontend:**
* React + Vite + TypeScript
* **Tanstack Query** (REST data fetching)
* TailwindCSS + **shadcn/ui** components
* Recharts for basic visualizations

**Backend:**
* FastAPI (REST APIs only)
* Pydantic v2 for data models and validation
* PostgreSQL for market snapshots and backtest results
* SQLAlchemy ORM
* httpx for Kalshi API client
* Uvicorn + Docker

**Data Science:**
* Jupyter notebooks
* pandas/numpy for data analysis
* **backtrader** or **vectorbt** for backtesting
* matplotlib/seaborn for visualization

### Phase 2+ (Planned Additions)

* **WebSocket** (Kalshi real-time feeds)
* **Zustand** (WebSocket state management)
* **Framer Motion** (UI polish and animations)
* **Redis** (optional caching for order books)

### Phase 4+ (Multi-User Platform)

* **Strawberry GraphQL** (typed API layer)
* **Apollo Client** (GraphQL client)
* **Firebase Auth** (user management)
* **Cloud Tasks/Celery** (background jobs)

---

## ⚙️ Setup & Usage

### Requirements

* Python ≥ 3.11
* Node.js ≥ 22
* pnpm (frontend package manager)
* Docker + Docker Compose (recommended)
* PostgreSQL 15+ (or use Docker)

### Quick Start (Docker Compose)

```bash
git clone https://github.com/seanbearden/kalshi-analysis.git
cd kalshi-analysis
make demo  # Starts backend + frontend + PostgreSQL
```

Access frontend: **[http://localhost:5173](http://localhost:5173)**
Access backend API: **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Manual Setup

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up database
createdb kalshi  # or use Docker: docker run -p 5432:5432 -e POSTGRES_DB=kalshi postgres:15

# Run server
uvicorn api.main:app --reload
```

#### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

#### Jupyter Notebooks

```bash
cd notebooks
pip install jupyter pandas numpy matplotlib backtrader
jupyter notebook
```

---

## 🔧 Configuration

**backend/.env** (Phase 1)

```env
KALSHI_API_BASE=https://demo-api.kalshi.com/v2
DB_URL=postgresql://user:pass@localhost:5432/kalshi  # pragma: allowlist secret
POLL_INTERVAL_SECONDS=5
LOG_LEVEL=INFO
```

**frontend/.env** (Phase 1)

```env
VITE_API_URL=http://localhost:8000
```

**Phase 2+ additions:**
```env
# backend/.env
KALSHI_WS_URL=wss://demo-api.kalshi.com/trade-api/ws
REDIS_URL=redis://localhost:6379

# frontend/.env
VITE_WS_URL=ws://localhost:8000/ws
```

---

## 🧮 Data Science Highlights (Phase 1)

**Backtesting Framework:**
* Event-driven simulation using **backtrader** or **vectorbt**
* Metrics: PnL, Sharpe ratio, maximum drawdown, win rate
* Trade fees, slippage, and realistic execution modeling
* Jupyter notebooks for strategy iteration and refinement

**Calibration Analysis:**
* **Reliability diagrams** — predicted vs realized probability calibration
* Brier score and log loss for model evaluation
* Visual components for portfolio demonstration

**Strategy Signals:**
* Implied probability changes (market sentiment shifts)
* Order book imbalance detection (supply/demand asymmetry)
* Spread decay patterns (liquidity analysis)

**Notebook → API Pattern:**
* Develop strategies in notebooks first (exploration)
* Productionize validated strategies in FastAPI (execution)
* Maintain parity between research and production code

---

## 📈 REST API Examples (Phase 1)

**Get active markets:**
```bash
GET /api/markets?status=active&limit=20
```

**Get market details:**
```bash
GET /api/markets/{ticker}
```

**Get historical snapshots:**
```bash
GET /api/markets/{ticker}/snapshots?start_date=2024-01-01&end_date=2024-01-31
```

**Run backtest:**
```bash
POST /api/backtest
{
  "strategy": "fade_overreaction",
  "market_filter": "politics",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

### GraphQL API (Phase 4+)

*GraphQL layer will be added in Phase 4 for multi-user flexibility. Phase 1 uses simple REST endpoints.*

<details>
<summary>Future GraphQL Example</summary>

```graphql
query MarketDetail($ticker: String!) {
  market(ticker: $ticker) {
    ticker
    title
    yesPrice
    noPrice
    volume
    candles(interval: "1h", limit: 100) {
      open
      high
      low
      close
      startTs
    }
  }
}
```
</details>

---

## 🔬 Testing & Quality

### Phase 1 Testing
* **Pytest** for backend unit tests (Pydantic models, API routes)
* **Hypothesis** for property-based testing (data validation)
* **Type checking**: mypy (backend) + TypeScript strict mode (frontend)
* **Linting**: Ruff (Python), ESLint + Prettier (TypeScript)
* **Pre-commit hooks** for code quality enforcement

### Phase 2+ Testing (Planned)
* Deterministic WebSocket replay harness
* E2E tests via Playwright
* Vitest for frontend component testing
* Load testing for real-time performance

### Code Coverage

![Coverage Sunburst](https://codecov.io/gh/seanbearden/kalshi-analysis/graphs/sunburst.svg?token=4RQ1KYTXFK)

---

## ✅ Phase 1 Completion Checklist

**Backend:**
- [ ] FastAPI server with `/api/markets` endpoints
- [ ] Kalshi API client with 5s polling loop
- [ ] PostgreSQL models for market snapshots
- [ ] Pydantic models for type safety
- [ ] Docker Compose setup

**Frontend:**
- [ ] React app with Tanstack Query
- [ ] shadcn/ui DataTable displaying markets
- [ ] Basic Recharts visualization
- [ ] Environment configuration

**Data Science:**
- [ ] Jupyter notebook for Kalshi data exploration
- [ ] Backtesting framework integration (backtrader/vectorbt)
- [ ] At least 1 strategy with Sharpe >0.5
- [ ] Reliability diagram component

**DevOps:**
- [ ] `make demo` command working
- [ ] Pre-commit hooks configured
- [ ] README reflects actual Phase 1 scope
- [ ] Docker images build successfully

---

## 🧑‍💻 Author

**Sean R.B. Bearden, Ph.D.**
*Data Scientist | Python Developer | Entrepreneur*
[Bearden Data Solutions LLC](https://beardendatasolutionsllc.com)

---

## 🧭 License

MIT License — freely available for learning and portfolio demonstration.

---

## 🧩 Summary

This project demonstrates **disciplined architecture evolution** and **data science rigor**:

### Key Differentiators

* **Phased complexity** — proves value before adding sophistication (no premature optimization)
* **Type safety throughout** — Pydantic + TypeScript catch errors at development time
* **Notebook-driven development** — research → validation → productionization pipeline
* **Cloud-ready from day 1** — Docker, environment configs, and GCP deployment patterns

### Portfolio Value

* Shows **full-stack capability** (Python backend + React frontend)
* Demonstrates **data science depth** (backtesting, calibration, quantitative analysis)
* Exhibits **software engineering discipline** (testing, linting, CI/CD readiness)
* Proves **architectural judgment** (simplicity first, complexity when justified)

**Current Status:** Phase 1 (Local Analytics Workbench) — proving strategy viability through backtesting before investing in real-time infrastructure or multi-user features.

This is a **credible demonstration** of skills in building analytical systems that bridge **quantitative research and production engineering**.
