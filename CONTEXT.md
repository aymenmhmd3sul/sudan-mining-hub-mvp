# PROJECT CONTEXT: Sudan Mining Hub (منصة التعدين السودانية)

## 1. System Overview
A modular, secure digital marketplace connecting Buyers, Merchants, Agents, Admins, and Guests in Sudan's mining sector.

## 2. Infrastructure & Stack
- Backend: FastAPI (Python 3) - Single Source of Truth
- Database: Neon PostgreSQL (Isolated Database: `sudan_mining_mvp`)
- Hosting: Render (`sudan-mining-hub-3` Web Service)
- Auth: JWT Bearer / HttpOnly Cookies (JSON API Payloads ONLY)

## 3. Strict Role Definitions
- GUEST: Browse listings, view dynamic map & market statistics.
- BUYER: Place purchase orders, track order status.
- MERCHANT: Manage inventory/assets, request featured ad slots (Requires Admin Approval).
- AGENT: Verify physical assets, mediate buyer-merchant deals (Requires Admin Approval).
- ADMIN: User account approvals, ad space management, commission verification.

## 4. Architectural Rules
- API-First design separating backend logic from presentation.
- Strict schema separation per role to prevent privilege escalation.
- Explicit language localization (Arabic RTL default, English LTR ready).
