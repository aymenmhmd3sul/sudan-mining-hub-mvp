# Protocol 2 — Asset Expansion Decision

## Status

ACCEPTED — 2026-09-25

## Decision

The current production MVP asset layer is sufficient as the expansion boundary for future markets and sectors.

No production schema redesign, commercial-party abstraction, or sector-specific core is required at this stage.

## Verified Capabilities

- `ListingType` supports:
  - `ASSET`
  - `EQUIPMENT`
  - `SERVICE`
  - `OPPORTUNITY`
- `ListingCategory` supports hierarchical categories through `parent_category_id`.
- `ListingSpec` provides flexible key/value/unit specifications.
- Marketplace filtering supports both `listing_type` and `category_id`.
- The existing commercial cycle remains:
  `BuyerRequest → Offer → Negotiation → Deal`.

## Architectural Boundary

Future sector expansion should initially use:

`ListingType → ListingCategory → ListingSpec → Listing`

without replacing or redesigning the existing commercial transaction flow.

## Deferred Changes

The following are deliberately deferred until a concrete business requirement proves they are necessary:

- `CommercialParty` / `Counterparty` abstraction.
- Replacing `buyer_id` / `merchant_id` in the current transaction core.
- New sector-specific transaction cores.
- Database redesign or migration solely for theoretical future expansion.

## Rule

Protocol 2 requires the minimum necessary change.

Existing generic capabilities must be reused before introducing new abstractions.

Any future change must pass:

`Problem Identification → Decisive Test → Minimal Change → Acceptance Test → Commit`

## Production Safety

This decision does not modify production data, database schema, authentication, transaction logic, or UI behavior.
