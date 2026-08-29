# SUDAN MINING HUB
# DOMAIN CONTRACT V1
# CLEAN START — NO LEGACY MODELS

## 0. CONTRACT STATUS

This document defines the approved domain structure before database
implementation.

No entity in this document becomes a database model until its contract
passes the architectural audit.

Previous project models, relationships, routers, services, or database
tables are NOT architectural inputs.

---

# 1. GLOBAL ENTITY RULES

Every persistent entity MUST have:

- explicit primary key
- explicit owner when ownership exists
- explicit lifecycle
- explicit status when state exists
- explicit creation timestamp
- explicit relationship direction
- explicit delete behavior

Rules:

1. No implicit foreign keys.
2. No duplicated identity records.
3. No parallel user/account tables.
4. No business module may own another module's internal entity.
5. Cross-module relationships must be explicit.
6. A relationship must have a business reason.
7. UI identifiers do not define database relationships.
8. Database relationships do not automatically define authorization.
9. Authorization is enforced by application/domain services.
10. Soft deletion is used only where business history must survive.

---

# 2. IDENTITY DOMAIN

## 2.1 User

Purpose:
Central identity representing one platform account.

Primary key:
user_id

Owner:
Self / platform identity domain.

Foreign keys:
None.

Relationships:
- User 1:N Listings
- User 1:N Buyer Requests
- User 1:N Offers
- User 1:N Negotiation Memberships
- User 1:N Notifications
- User 1:N Subscriptions
- User 1:N Advertisements

These relationships are logical domain relationships and are not all
implemented until the target entities are approved.

Lifecycle:
REGISTERED → APPROVED/ACTIVE → SUSPENDED/DEACTIVATED

Status:
ACTIVE
SUSPENDED
DEACTIVATED

Required fields:
- user_id
- email
- password credential representation
- role
- created_at

Optional fields:
- full_name
- phone_number
- profile metadata
- approved_at
- deactivated_at

Delete behavior:
User records are NOT hard-deleted when business history depends on them.
Deactivation preserves historical ownership.

Dependencies:
Foundation only.

---

## 2.2 UserRole

Purpose:
Defines the controlled role values used by the Identity domain.

Type:
ENUM / SUPPORTING TYPE — NOT A DATABASE ENTITY.

Values:
- ADMIN
- MERCHANT
- BUYER
- AGENT

Lifecycle:
Managed by the Identity domain.

Dependencies:
User.

Implementation rule:
UserRole MUST NOT receive its own primary key, foreign keys,
database table, ownership model, or delete behavior.


# 3. MARKETPLACE DOMAIN

## 3.1 Listing

Purpose:
Commercial presentation of an asset, equipment item, or service offered
through the marketplace.

Primary key:
listing_id

Owner:
Merchant / authorized listing owner.

Foreign keys:
owner_user_id → User

Relationship:
User 1:N Listing

Lifecycle:
DRAFT → ACTIVE → RESERVED → SOLD/COMPLETED
                    └→ ARCHIVED

Status:
DRAFT
ACTIVE
PAUSED
RESERVED
SOLD
ARCHIVED

Required fields:
- listing_id
- owner_user_id
- title
- listing_type
- description
- status
- created_at

Optional fields:
- price
- currency
- negotiable flag
- location
- media
- specifications
- category
- published_at
- expires_at

Delete behavior:
Hard deletion is prohibited after publication if the listing has
business history. Archive instead.

Dependencies:
User.

---

## 3.2 ListingCategory

Purpose:
Controlled classification of marketplace listings.

Primary key:
category_id

Owner:
Platform.

Foreign keys:
parent_category_id → ListingCategory (optional)

Relationship:
Category 1:N child categories
Category 1:N Listings

Lifecycle:
ACTIVE → DISABLED

Status:
ACTIVE / DISABLED

Required fields:
- category_id
- name
- status

Optional fields:
- parent_category_id
- description
- sort_order

Delete behavior:
Disable instead of deleting categories referenced by listings.

Dependencies:
None initially.

---

## 3.3 ListingLocation

Purpose:
Represents the geographic location attached to a listing.

Primary key:
location_id

Owner:
Listing owner / platform-controlled location data.

Foreign keys:
listing_id → Listing

Relationship:
Listing 1:N ListingLocation

Lifecycle:
ACTIVE → REMOVED

Status:
ACTIVE / REMOVED

Required fields:
- location_id
- listing_id
- locality / geographic reference

Optional fields:
- state_province
- coordinates
- address detail

Delete behavior:
Remove/archive relationship without deleting the listing.

Dependencies:
Listing.

---

# 4. REQUESTS DOMAIN

## 4.1 BuyerRequest

Purpose:
A buyer's structured commercial requirement seeking a product,
asset, equipment, or service.

Primary key:
request_id

Owner:
Buyer.

Foreign keys:
buyer_user_id → User

Relationship:
User 1:N BuyerRequest

Lifecycle:
DRAFT → OPEN → NEGOTIATING → FULFILLED
                         └→ CANCELLED
                         └→ EXPIRED

Status:
DRAFT
OPEN
NEGOTIATING
FULFILLED
CANCELLED
EXPIRED

Required fields:
- request_id
- buyer_user_id
- title
- description
- status
- created_at

Optional fields:
- category_id
- desired_location
- budget
- currency
- quantity
- deadline

Delete behavior:
Do not hard-delete a request after commercial activity exists.
Cancel/archive instead.

Dependencies:
User.
Optional dependency on ListingCategory.

---

# 5. OFFERS DOMAIN

## 5.1 Offer

Purpose:
A merchant's response to one BuyerRequest.

Primary key:
offer_id

Owner:
Merchant who submitted the offer.

Foreign keys:
- request_id → BuyerRequest
- merchant_user_id → User

Relationships:
BuyerRequest 1:N Offer
User 1:N Offer

Lifecycle:
SUBMITTED → ACCEPTED
         ├→ REJECTED
         ├→ WITHDRAWN
         └→ SUPERSEDED

Status:
SUBMITTED
ACCEPTED
REJECTED
WITHDRAWN
SUPERSEDED

Required fields:
- offer_id
- request_id
- merchant_user_id
- status
- created_at

Optional fields:
- price
- currency
- quantity
- delivery_terms
- message
- valid_until

Delete behavior:
Never hard-delete an offer after it participates in negotiation or
transaction history.

Dependencies:
User
BuyerRequest

---

# 6. NEGOTIATION DOMAIN

## 6.1 NegotiationRoom

Purpose:
Private controlled communication space for a specific commercial
negotiation.

Primary key:
negotiation_id

Owner:
Platform-controlled business record.

Foreign keys:
- request_id → BuyerRequest
- offer_id → Offer (required when negotiation originates from an offer)

Relationships:
BuyerRequest 1:N NegotiationRoom
Offer 1:N NegotiationRoom

Lifecycle:
OPEN → AGREED
     ├→ CLOSED
     └→ CANCELLED

Status:
OPEN
AGREED
CLOSED
CANCELLED

Required fields:
- negotiation_id
- request_id
- status
- created_at

Optional fields:
- offer_id
- agreed_at
- closed_at

Delete behavior:
Never hard-delete a negotiation containing messages or commercial
history.

Dependencies:
BuyerRequest
Offer

---

## 6.2 NegotiationParticipant

Purpose:
Explicit authorization boundary defining who may access a negotiation.

Primary key:
participant_id

Owner:
Negotiation domain.

Foreign keys:
- negotiation_id → NegotiationRoom
- user_id → User

Relationships:
NegotiationRoom 1:N Participant
User 1:N Participant

Lifecycle:
INVITED → ACTIVE → REMOVED

Status:
INVITED
ACTIVE
REMOVED

Required fields:
- participant_id
- negotiation_id
- user_id
- status

Optional fields:
- joined_at
- removed_at

Delete behavior:
Do not delete historical participation records.

Dependencies:
NegotiationRoom
User

---

## 6.3 NegotiationMessage

Purpose:
A message belonging to one private negotiation.

Primary key:
message_id

Owner:
Sender for authorship; negotiation for containment.

Foreign keys:
- negotiation_id → NegotiationRoom
- sender_user_id → User

Relationships:
NegotiationRoom 1:N Message
User 1:N Message

Lifecycle:
CREATED → HIDDEN only if moderation policy requires it.

Status:
ACTIVE
HIDDEN

Required fields:
- message_id
- negotiation_id
- sender_user_id
- body
- created_at

Optional fields:
- edited_at
- metadata

Delete behavior:
Preserve message history. Prefer moderation/hiding over hard deletion.

Dependencies:
NegotiationRoom
User

---

# 7. TRANSACTIONS DOMAIN

## 7.1 Transaction

Purpose:
Records the commercial agreement resulting from an accepted business
interaction.

Primary key:
transaction_id

Owner:
Platform transaction domain.

Foreign keys:
- buyer_user_id → User
- merchant_user_id → User
- request_id → BuyerRequest
- offer_id → Offer
- negotiation_id → NegotiationRoom

Relationships:
User 1:N buyer Transactions
User 1:N merchant Transactions
BuyerRequest 1:N Transaction
Offer 1:0..1 Transaction
NegotiationRoom 1:0..1 Transaction

Lifecycle:
PENDING → CONFIRMED → COMPLETED
                  ├→ CANCELLED
                  └→ DISPUTED

Status:
PENDING
CONFIRMED
COMPLETED
CANCELLED
DISPUTED

Required fields:
- transaction_id
- buyer_user_id
- merchant_user_id
- status
- created_at

Optional fields:
- request_id
- offer_id
- negotiation_id
- total_amount
- currency
- completed_at
- cancelled_at

Delete behavior:
Never hard-delete a transaction.

Dependencies:
User
BuyerRequest
Offer
NegotiationRoom

---

## 7.2 Invoice

Purpose:
Financial document generated for a transaction.

Primary key:
invoice_id

Owner:
Transaction domain / platform.

Foreign keys:
transaction_id → Transaction

Relationship:
Transaction 1:N Invoice

Lifecycle:
DRAFT → ISSUED → PAID
               ├→ VOID
               └→ OVERDUE

Status:
DRAFT
ISSUED
PAID
VOID
OVERDUE

Required fields:
- invoice_id
- transaction_id
- invoice number
- amount
- currency
- status
- created_at

Optional fields:
- due_at
- paid_at
- metadata

Delete behavior:
Never hard-delete issued financial records.

Dependencies:
Transaction.

---

## 7.3 Commission

Purpose:
Records the platform commission associated with a transaction.

Primary key:
commission_id

Owner:
Platform.

Foreign keys:
transaction_id → Transaction

Relationship:
Transaction 1:0..1 Commission

Lifecycle:
CALCULATED → DUE → SETTLED
                  └→ WAIVED

Status:
CALCULATED
DUE
SETTLED
WAIVED

Required fields:
- commission_id
- transaction_id
- amount/rate
- status
- created_at

Optional fields:
- settled_at
- calculation metadata

Delete behavior:
Never hard-delete financial history.

Dependencies:
Transaction.

---

# 8. NOTIFICATIONS DOMAIN

## 8.1 Notification

Purpose:
User-facing record generated by a platform/domain event.

Primary key:
notification_id

Owner:
Recipient user.

Foreign keys:
recipient_user_id → User

Relationship:
User 1:N Notification

Lifecycle:
CREATED → READ / ARCHIVED

Status:
UNREAD
READ
ARCHIVED

Required fields:
- notification_id
- recipient_user_id
- notification type
- content/reference
- created_at

Optional fields:
- read_at
- source entity reference
- metadata

Delete behavior:
Archive rather than hard-delete where audit/history matters.

Dependencies:
User.

IMPORTANT:
Notifications reference business events through controlled references.
They do NOT own business entities.

---

# 9. SUBSCRIPTIONS DOMAIN

## 9.1 Subscription

Purpose:
Represents a user's commercial platform subscription/access state.

Primary key:
subscription_id

Owner:
Subscribed user/account.

Foreign keys:
user_id → User

Relationship:
User 1:N Subscription

Lifecycle:
PENDING → ACTIVE → EXPIRED
                 ├→ CANCELLED
                 └→ SUSPENDED

Status:
PENDING
ACTIVE
EXPIRED
CANCELLED
SUSPENDED

Required fields:
- subscription_id
- user_id
- plan
- status
- started_at

Optional fields:
- expires_at
- cancelled_at
- renewal information
- payment reference

Delete behavior:
Never hard-delete historical subscription records.

Dependencies:
User.

---

# 10. ADVERTISING DOMAIN

## 10.1 Advertisement

Purpose:
A commercial promotional unit displayed in approved platform
advertising spaces.

Primary key:
advertisement_id

Owner:
The verified user/business account that purchased or created the
advertisement.

Foreign keys:
- owner_user_id → User

Relationship:
User 1:N Advertisement

Lifecycle:
DRAFT → PENDING_REVIEW → APPROVED → ACTIVE → EXPIRED
                                      └→ PAUSED
                                      └→ REJECTED

Status:
DRAFT
PENDING_REVIEW
APPROVED
ACTIVE
PAUSED
EXPIRED
REJECTED

Required fields:
- advertisement_id
- owner_user_id
- title
- content/media reference
- status
- created_at

Optional fields:
- target_module
- target_category
- target_location
- start_at
- end_at
- destination reference
- budget
- campaign metadata

Delete behavior:
Do not hard-delete an advertisement after publication/payment history.
Archive it.

Dependencies:
User.

---

## 10.2 AdvertisementPlacement

Purpose:
Defines a controlled platform location where an advertisement may appear.

Primary key:
placement_id

Owner:
Platform.

Foreign keys:
None in the first contract version.

Relationship:
Advertisement N:M Placement through AdvertisementDelivery.

Lifecycle:
ACTIVE → DISABLED

Status:
ACTIVE
DISABLED

Required fields:
- placement_id
- placement key
- status

Optional fields:
- module
- display rules
- dimensions
- targeting rules

Delete behavior:
Disable placement rather than delete it if historical campaigns refer
to it.

Dependencies:
None.

---

## 10.3 AdvertisementDelivery

Purpose:
Explicit association between an Advertisement and a Placement,
including delivery/targeting state.

Primary key:
delivery_id

Owner:
Advertising domain.

Foreign keys:
- advertisement_id → Advertisement
- placement_id → AdvertisementPlacement

Relationships:
Advertisement 1:N Delivery
Placement 1:N Delivery

Lifecycle:
SCHEDULED → ACTIVE → COMPLETED
                   └→ CANCELLED

Status:
SCHEDULED
ACTIVE
COMPLETED
CANCELLED

Required fields:
- delivery_id
- advertisement_id
- placement_id
- status

Optional fields:
- target_module
- target_category
- target_location
- start_at
- end_at

Delete behavior:
Preserve historical delivery records.

Dependencies:
Advertisement
AdvertisementPlacement

IMPORTANT:
The Gateway/card does NOT own Advertisement.
The Gateway requests an approved Advertisement through the advertising
application service.

---

# 11. CROSS-DOMAIN RELATIONSHIP MAP

Identity
  |
  +--> Marketplace Listing
  |
  +--> BuyerRequest
          |
          +--> Offer
                  |
                  +--> NegotiationRoom
                          |
                          +--> NegotiationParticipant
                          |
                          +--> NegotiationMessage
                          |
                          +--> Transaction
                                  |
                                  +--> Invoice
                                  |
                                  +--> Commission

Identity
  |
  +--> Notification
  |
  +--> Subscription
  |
  +--> Advertisement
          |
          +--> AdvertisementDelivery
                  |
                  +--> AdvertisementPlacement

---

# 12. RELATIONSHIP SAFETY RULES

## User → Business Records

User is the identity root.

Business records reference User.

Business records MUST NOT create duplicate user identity fields.

---

## BuyerRequest → Offer

One request may receive many offers.

An offer belongs to exactly one request.

Therefore:

BuyerRequest 1:N Offer

---

## Offer → Negotiation

An offer may result in zero or more negotiation records depending on
the business workflow.

The application service decides when negotiation is opened.

The database must not infer authorization from offer ownership alone.

---

## Negotiation → Participants

Access is determined by explicit NegotiationParticipant records.

Being a user, buyer, merchant, or agent does not automatically grant
access to every negotiation.

---

## Negotiation → Transaction

A negotiation may produce zero or one finalized transaction.

A transaction may exist without a negotiation only if the business
workflow explicitly permits direct agreement.

---

## Advertisement → Placement

Advertisement ownership and advertisement delivery are separate concepts.

Ownership answers:
"Who owns this advertisement?"

Placement answers:
"Where may this advertisement appear?"

Delivery answers:
"Is this advertisement currently authorized to appear there?"

This separation prevents the Gateway UI from becoming the advertising
authority.

---

# 13. DATABASE IMPLEMENTATION ORDER

Database models MUST NOT be created in arbitrary order.

Approved implementation sequence:

1. User
2. ListingCategory
3. Listing
4. ListingLocation
5. BuyerRequest
6. Offer
7. NegotiationRoom
8. NegotiationParticipant
9. NegotiationMessage
10. Transaction
11. Invoice
12. Commission
13. Notification
14. Subscription
15. Advertisement
16. AdvertisementPlacement
17. AdvertisementDelivery

After each group:

MODEL IMPORT TEST
→ MIGRATION TEST
→ DB RELATION TEST

---

# 14. UI ARCHITECTURE

Gateway is not a business domain.

Gateway responsibilities:

- navigation
- presentation
- module discovery
- language selection
- advertisement presentation
- session-aware entry points

Gateway MUST NOT:

- create transactions directly
- decide advertisement ownership
- query database directly
- enforce business authorization
- contain domain rules

Each module owns:

UI
→ Route
→ Application Service
→ Domain Rules
→ Persistence

---

# 15. ADVERTISING DELIVERY RULE

A displayed advertisement MUST be traceable:

Displayed Card
→ AdvertisementDelivery
→ Advertisement
→ owner_user_id
→ User

Before rendering an advertisement:

1. Advertisement exists.
2. Advertisement is approved/active.
3. Delivery is active.
4. Current time is within delivery window if one exists.
5. Placement matches requested Gateway/module placement.
6. Targeting rules are satisfied.
7. Owner identity remains valid.

The UI never decides these conditions.

---

# 16. CONTRACT GATE

No database model may be created if any of the following is undefined:

- primary key
- owner
- foreign key target
- cardinality
- lifecycle
- status
- delete behavior
- dependency

This document is the source contract for the next architectural stage.
