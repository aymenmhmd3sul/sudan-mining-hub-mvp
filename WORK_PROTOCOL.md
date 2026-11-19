# WORK PROTOCOL: Sudan Mining Hub (MVP)

## 1. Core Principles
- Single Source of Truth: Backend (FastAPI) controls data and security models.
- Role-Based Dynamic Dashboards: Redirection validated strictly server-side via JWT.
- Zero Data Leakage: Session-scoped queries anchored to `user_id`.
- Dual Language & RTL Support: Built into core schemas and UI layout from Day 1.

## 2. Role Dictionary & Naming Standards
- Roles: `ADMIN`, `MERCHANT`, `BUYER`, `GUEST`
- Enums: UPPERCASE (`BUYER`, `MERCHANT`)
- DB Fields & JSON Keys: `snake_case` (`user_id`, `created_at`)
- Classes & Models: `PascalCase` (`UserModel`, `ProductCard`)

## 3. Account Approval & Security
- `MERCHANT` accounts default to `is_approved = False`.
- Limited view access until manual review and activation by `ADMIN`.

## 4. Financial & Transaction Workflow
- Subscription & Commission validation requires proof check before status update.
- Direct contact details are masked; communications flow through the platform's order and direct negotiation workflows.

## 5. Phase-Based Backup Strategy
- Mandatory Git Tagging (`v0.1-setup`, `v0.2-auth`, etc.) upon completing each tested phase.
- Local compressed archive generated in Termux prior to phase transitions.
