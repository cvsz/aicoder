# Phase 2 Domain State Contracts

**Status:** Contract inventory completed; cross-layer adoption remains pending.

## Added

- provider-neutral model descriptors and capabilities;
- provider-neutral stop reasons including an explicit `unknown` fallback;
- cursor pagination metadata;
- durable job state vocabulary and transition validation;
- explicit approval state vocabulary and transition validation.

## Invariants

- token limits are positive when present;
- model aliases are unique and cannot repeat the canonical model ID;
- `has_more` requires a next cursor;
- terminal job and approval states reject further transitions;
- public types import no provider SDK and contain no provider credential.

## Validation

`tests/test_domain_state_contracts.py` covers serialization, invalid model metadata, pagination consistency, valid transitions, and terminal-state rejection.

## Remaining gate

Phase 2 contracts must be consumed by the typed Product API client and at least one versioned API vertical slice before Phase 2 is considered fully complete under the execution plan.
