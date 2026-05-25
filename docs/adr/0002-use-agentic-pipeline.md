# ADR 0002: Use Fully Agentic Pipeline Architecture

**Date:** 2026-05-25
**Status:** Accepted

## Context

Clipper Agency needs a content generation pipeline with 7+ specialized agents. We need to decide between a monolithic pipeline, a structured pipeline with limited flexibility, or a fully agentic architecture where each agent is independently configurable and observable.

## Decision

Use **Fully Agentic Architecture (Approach B)** with a database-driven orchestrator and gated state machine.

## Alternatives Considered

### Approach A: Monolithic Pipeline

- Single script calling functions in sequence.
- **Pros:** Simple to start.
- **Cons:** No independent agent configuration. No observability per agent. Hard to test individual agents. Doesn't scale.

### Approach C: Structured Pipeline with Limited Flexibility

- Predefined stages with some configuration.
- **Pros:** More structure than monolith.
- **Cons:** Limited agent customization. Harder to add new agents. Limited per-agent observability.

## Rationale

- Each agent independently testable, configurable, and observable.
- Scales naturally to microservices if needed.
- DB-driven state enables restartability at any stage.
- Orchestrator coordinates via state, not hardcoded sequence.
- Agents can be swapped, added, or removed without pipeline changes.
- Creative Director can be added in Stage 2 without restructuring.

## Consequences

- Each agent needs clear input/output contract.
- Orchestrator needs gate logic to enforce safety/cost rules.
- Dashboard can show per-agent state.
- More upfront design work, but pays off at scale.
