# Phase 2 Domain Contracts Validation

**Status:** Foundation implemented; phase remains in progress.

## Added contracts

- provider-neutral message roles and content blocks;
- text, image, document, tool-use, and tool-result validation;
- usage accounting with non-negative invariants;
- typed Product API error envelope;
- recursive secret redaction for error details;
- canonical stream event vocabulary;
- monotonic sequence and exactly-one-terminal-event validation.

## Tests

`tests/test_domain_contracts.py` covers round-trip serialization, invalid content, negative usage, nested secret redaction, missing terminal events, duplicate/post-terminal events, and non-monotonic sequences.

## Compatibility

The new package is additive and does not change existing CLI behavior. It imports no provider SDK and requires no credential or network access.

## Remaining Phase 2 work

- model descriptors and capabilities;
- conversation identifiers and pagination;
- stop-reason contract;
- job and approval state machines;
- unknown-field/backward-compatibility policy;
- adoption by Product API, client, services, persistence, and provider adapters.

Phase 2 must not be marked complete until those contracts are added and consumed across at least one end-to-end API slice.
