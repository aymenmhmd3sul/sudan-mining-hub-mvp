# Sudan Mining Hub MVP
# New Architecture Contract — From Zero

## 1. Core Principle

This project is a clean architectural start.

Previous project code, models, routers, services, database structures,
or UI implementations MUST NOT be reused merely because they worked before.

Previous work may be consulted only as historical reference.

---

## 2. Architectural Layers

The system is divided into independent layers:

1. Foundation
2. Identity
3. Domain Contracts
4. Domain Modules
5. Application Services
6. HTTP/API Layer
7. UI Shell
8. Domain UI
9. Integration

Dependencies flow inward toward domain rules.

UI MUST NOT contain business rules.

Routes MUST NOT become the source of business rules.

Database models MUST represent approved domain relationships.

---

## 3. Module Isolation

Every business section is an independent module.

A module must have a clear boundary:

- entities
- schemas/contracts
- services/use-cases
- routes
- UI
- tests

A module may depend on approved shared infrastructure,
but one module must not reach directly into another module's internal implementation.

---

## 4. Database Rules

Every entity MUST have:

- one explicit primary key
- explicit ownership where ownership exists
- explicit lifecycle/status where required

Every foreign key MUST be created only after:

1. Both entities are identified.
2. Both primary keys are identified.
3. The business relationship is defined.
4. Cardinality is defined.
5. Delete/update behavior is defined.

No guessed foreign keys.

No duplicated identity fields.

No parallel User tables.

No duplicate SQLAlchemy Base.

---

## 5. Identity

The identity domain is responsible for:

- User identity
- Roles
- Authentication
- Authorization

Business modules reference identity through approved relationships.

They do not duplicate user records.

---

## 6. Initial Business Domains

The initial domain map is:

### Marketplace
Assets, equipment, services, categories, locations.

### Requests
Buyer requests and commercial requirements.

### Offers
Merchant responses to buyer requests.

### Negotiation
Private negotiation between authorized participants.

### Transactions
Agreement, invoice, commission and transaction state.

### Notifications
Events and user notifications.

### Subscriptions
Commercial access/subscription state.

### Advertising
Commercial advertisements and their verified ownership/targets.

The exact entities and relationships inside each domain are NOT approved yet.

They must be designed before implementation.

---

## 7. UI Architecture

The Gateway is a UI shell.

It must not own business logic.

The Gateway invokes independent sections.

Example:

Gateway
  -> Marketplace
  -> Requests
  -> Negotiation
  -> Services
  -> Advertising

Each section owns its own UI and behavior.

---

## 8. UI / Database Separation

Templates and JavaScript MUST NOT directly query the database.

UI communicates through application routes/services.

The UI must not assume database IDs or relationships that have not been defined
by the domain contract.

---

## 9. Language

Arabic is the default language.

English is supported.

Language selection is handled centrally by the language foundation.

Domain modules must use the shared translation mechanism.

---

## 10. Required Development Protocol

For every module:

BACKUP
→ AUDIT
→ DECISION
→ CHANGE
→ SYNTAX TEST
→ IMPORT TEST
→ DB TEST
→ RELATION TEST
→ ROUTE TEST
→ UI TEST
→ COMMIT

A failed stage blocks progression to the next stage.

---

## 11. Current State

Foundation:
IN PROGRESS / VERIFIED

UI Shell:
FOUNDATION CREATED

Business Domains:
NOT IMPLEMENTED

Database Business Schema:
NOT APPROVED

Advertising:
NOT IMPLEMENTED

Marketplace:
NOT IMPLEMENTED

Requests:
NOT IMPLEMENTED

Offers:
NOT IMPLEMENTED

Negotiation:
NOT IMPLEMENTED

Transactions:
NOT IMPLEMENTED

Notifications:
NOT IMPLEMENTED

Subscriptions:
NOT IMPLEMENTED

---

## 12. Next Architectural Step

Before implementing any business domain:

Create the Domain Contract.

For every proposed entity define:

- Entity name
- Purpose
- Primary key
- Owner
- Foreign keys
- Relationship cardinality
- Lifecycle
- Status
- Required fields
- Optional fields
- Delete behavior
- Dependencies

Only approved contracts may become database models.
