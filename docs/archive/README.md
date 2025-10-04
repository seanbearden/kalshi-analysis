# Architecture Documentation Archive

This directory contains exploratory architecture documents from brainstorming sessions. These documents explore **Phase 2+ features** and should be referenced when those phases are implemented.

---

## Documents in This Archive

### 1. `kalshi-hybrid-sdk-architecture.md`
**Phase**: 2+
**Topic**: Hybrid dual-SDK architecture with WebSocket real-time subscriptions

**Key Features Explored**:
- Frontend TypeScript SDK + Backend Python SDK pattern
- WebSocket real-time ticker updates
- Order book depth subscriptions
- Fill notifications (authenticated WebSocket channel)
- Automatic reconnection with exponential backoff
- Graceful fallback to GraphQL when WebSocket fails

**When to Use**: Reference when implementing Phase 2 WebSocket integration

---

### 2. `kalshi-integration-patterns.md`
**Phase**: 2+
**Topic**: Production-ready WebSocket integration patterns and best practices

**Key Patterns**:
- Real-time price display (Pattern 1)
- Order book depth visualization (Pattern 2)
- Fill notification handling (Pattern 3)
- Automatic reconnection (Pattern 4)
- Multi-market subscriptions (Pattern 5)
- Optimistic updates (Pattern 6)
- WebSocket fallback strategies (Pattern 9)
- Error handling (Pattern 10)
- Security (Pattern 13)

**When to Use**: Reference specific patterns during Phase 2+ implementation

---

### 3. `kalshi-mvp-implementation-plan.md`
**Phase**: 2+
**Topic**: 3-week implementation plan for hybrid SDK with WebSocket

**Implementation Phases**:
- Week 1: Backend Python SDK + WebSocket service
- Week 2: Frontend TypeScript SDK + WebSocket subscriptions
- Week 3: Integration, testing, error handling

**When to Use**: Adapt timeline and tasks for Phase 2 WebSocket implementation

---

### 4. `system-architecture-design.md`
**Phase**: 1 (with Phase 2 preparation)
**Topic**: First attempt at reconciling Phase 1 REST-only with Phase 2 WebSocket

**Key Sections**:
- Three-container design (API, Poller, DB)
- ADR-001: Separate poller container
- ADR-002: Repository pattern
- ADR-003: Phase 2-ready data models
- Phased evolution roadmap

**When to Use**: Historical reference; superseded by `phase-1-architecture.md`

---

## Why These Documents Are Archived

These documents were created during a brainstorming session that explored **real-time WebSocket features**. However, the **Phase 1 goal** is offline backtesting, not live trading:

- ✅ **Phase 1**: REST-only polling, 2-week MVP, backtest validation
- 🔮 **Phase 2+**: WebSocket real-time (only if Phase 1 validates strategy)

The hybrid SDK architecture is **excellent for Phase 2**, but premature for Phase 1. These docs are archived to:

1. **Prevent confusion** during Phase 1 implementation
2. **Preserve valuable work** for future phases
3. **Provide reference** when Phase 2 is justified

---

## Current Active Documentation

**For Phase 1 Implementation** (follow these):
- `../phase-1-architecture.md` - REST-only design with ADR specifications
- `../README.md` - Project overview and phased roadmap

**For Phase 2 Planning** (reference when ready):
- `../phase-2-architecture.md` - WebSocket additions to Phase 1 foundation
- This archive (patterns and detailed implementations)

---

## Decision Flow

```
Phase 1 Complete?
├─ Backtest Sharpe ratio >0.5? ✅
│  └─> Proceed to Phase 2
│     └─> Use phase-2-architecture.md
│        └─> Reference these archived docs for implementation details
│
└─ Backtest Sharpe ratio <0.5? ❌
   └─> Stay in Phase 1
      └─> Iterate on strategy in notebooks
      └─> WebSocket features not needed (yet)
```

---

## Key Insights from Exploration

### What We Learned

**WebSocket Integration Complexity**:
- Adds 40-50% implementation complexity
- Requires reconnection logic, gap detection, state synchronization
- 3-week timeline (vs. 2-week Phase 1)

**Phase 1 ADRs Enable Smooth Phase 2 Transition**:
- ADR-001 (separate poller): Add WebSocket to same container
- ADR-002 (repository pattern): No API refactoring needed
- ADR-003 (Phase 2-ready models): No schema migration needed
- **Result**: Phase 2 = 5 days instead of 2-3 weeks

**Architecture Decision Validated**:
- REST-only Phase 1 is correct for backtesting goal
- WebSocket belongs in Phase 2 (live monitoring)
- The exploration was valuable but premature

---

## Summary

These archived documents represent a **valuable exploration of Phase 2+ architecture**. They should be referenced when:

1. Phase 1 validates strategy profitability (Sharpe >0.5)
2. Real-time monitoring becomes justified
3. WebSocket integration is implemented

Until then, **follow `phase-1-architecture.md`** for the current phase implementation.
