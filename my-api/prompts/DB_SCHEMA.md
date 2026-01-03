# Database Schema Reference

PostgreSQL database for restaurant analytics. Unified schema from multiple POS sources (Toast, DoorDash, Square).

## ENUMS

### OrderSourceEnum
- `TOAST`, `DOORDASH`, `SQUARE`

### OrderTypeEnum
- `DINE_IN`, `TAKEOUT`, `DELIVERY`, `PICKUP`

### OrderStatusEnum
- `PENDING`, `COMPLETED`, `CANCELLED`, `REFUNDED`

### PaymentTypeEnum
- `CARD`, `CASH`, `DIGITAL_WALLET`, `OTHER`, `UNKNOWN`

### PaymentStatusEnum
- `PENDING`, `COMPLETED`, `FAILED`, `REFUNDED`

## TABLES

### locations
**PK:** `id` (SERIAL)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | PK |
| name | VARCHAR(255) | NO | Location name |
| address_line1 | VARCHAR(255) | YES | Address line 1 |
| address_line2 | VARCHAR(255) | YES | Address line 2 |
| city | VARCHAR(100) | YES | City |
| state | VARCHAR(50) | YES | State |
| zip_code | VARCHAR(20) | YES | Zip code |
| country | VARCHAR(2) | YES | Country (default: US) |
| timezone | VARCHAR(50) | YES | Timezone (default: America/New_York) |
| source_ids | JSONB | YES | IDs by source: `{"TOAST": "id1"` |
| created_at | TIMESTAMPTZ | YES | Auto |
| updated_at | TIMESTAMPTZ | YES | Auto (trigger) |

**Relationships:**
- `orders.location_id` → `locations.id` (1:N)

**Indexes:** None explicit

**Location Mapping:**
All sources represent the same 4 physical locations. Each location has separate records per source with different `source_ids`:

| Location Name | Toast GUID | DoorDash Store ID | Square Location ID |
|---------------|------------|-------------------|---------------------|
| Downtown | loc_downtown_001 | str_downtown_001 | LCN001DOWNTOWN |
| Airport | loc_airport_002 | str_airport_002 | LCN002AIRPORT |
| Mall Location | loc_mall_003 | str_mall_003 | LCN003MALL |
| University | loc_univ_004 | str_university_004 | LCN004UNIV |

Each location record stores its source ID in `source_ids` JSONB: `{"TOAST": "loc_downtown_001"}` or `{"DOORDASH": "str_downtown_001"}` or `{"SQUARE": "LCN001DOWNTOWN"}`.

---

### categories
**PK:** `id` (SERIAL)  
**UNIQUE:** `name`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | PK |
| name | VARCHAR(255) | NO | Unique name |
| normalized_name | VARCHAR(255) | NO | Normalized name |
| parent_id | INTEGER | YES | FK → categories.id (hierarchy) |
| sort_order | INTEGER | YES | Display order |
| source_names | JSONB | YES | Names by source |
| description | TEXT | YES | Description |
| extra_data | JSONB | YES | Metadata |
| created_at | TIMESTAMPTZ | YES | Auto |
| updated_at | TIMESTAMPTZ | YES | Auto (trigger) |

**Relationships:**
- `categories.parent_id` → `categories.id` (self-ref, hierarchy)
- `products.category_id` → `categories.id` (1:N)

**Indexes:**
- `idx_categories_normalized_name` (normalized_name)

---

### products
**PK:** `id` (SERIAL)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | PK |
| name | VARCHAR(255) | NO | Product name |
| normalized_name | VARCHAR(255) | NO | Normalized name |
| category_id | INTEGER | YES | FK → categories.id |
| base_price | NUMERIC(10,2) | YES | Base price |
| description | TEXT | YES | Description |
| size | VARCHAR(50) | YES | Size/variation |
| quantity | VARCHAR(50) | YES | Quantity |
| is_active | BOOLEAN | YES | Active (default: true) |
| extra_data | JSONB | YES | Metadata |
| created_at | TIMESTAMPTZ | YES | Auto |
| updated_at | TIMESTAMPTZ | YES | Auto (trigger) |

**Relationships:**
- `products.category_id` → `categories.id` (N:1)
- `product_mappings.product_id` → `products.id` (1:N, CASCADE)
- `order_items.product_id` → `products.id` (1:N)

**Indexes:**
- `idx_products_name_trgm` (name, GIN trigram)
- `idx_products_normalized_name` (normalized_name)
- `idx_products_category_id` (category_id) - implicit by FK

---

### product_mappings
**PK:** `id` (SERIAL)  
**UNIQUE:** `(source, source_product_id)`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | PK |
| product_id | INTEGER | NO | FK → products.id (CASCADE) |
| source | OrderSourceEnum | NO | Source |
| source_product_id | VARCHAR(255) | NO | ID in source |
| source_product_name | VARCHAR(255) | NO | Name in source |
| source_price | NUMERIC(10,2) | YES | Price in source |
| match_confidence | NUMERIC(3,2) | YES | Match confidence |
| is_manual_match | BOOLEAN | YES | Manual match |
| source_metadata | JSONB | YES | Source metadata |
| created_at | TIMESTAMPTZ | YES | Auto |
| updated_at | TIMESTAMPTZ | YES | Auto (trigger) |

**Relationships:**
- `product_mappings.product_id` → `products.id` (N:1, CASCADE)

**Indexes:**
- `idx_product_mappings_product_id` (product_id)
- `idx_product_mappings_source` (source, source_product_id)

---

### orders
**PK:** `id` (SERIAL)  
**UNIQUE:** `(source, source_order_id)`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | PK |
| source | OrderSourceEnum | NO | Source |
| source_order_id | VARCHAR(255) | NO | ID in source |
| location_id | INTEGER | NO | FK → locations.id |
| order_type | OrderTypeEnum | NO | Order type |
| status | OrderStatusEnum | YES | Status (default: completed) |
| created_at | TIMESTAMPTZ | NO | Creation date |
| closed_at | TIMESTAMPTZ | YES | Close date |
| business_date | DATE | NO | Business date |
| subtotal | NUMERIC(10,2) | NO | Subtotal (default: 0) |
| tax_amount | NUMERIC(10,2) | NO | Tax (default: 0) |
| tip_amount | NUMERIC(10,2) | NO | Tip (default: 0) |
| discount_amount | NUMERIC(10,2) | NO | Discount (default: 0) |
| total_amount | NUMERIC(10,2) | NO | Total (default: 0) |
| delivery_fee | NUMERIC(10,2) | YES | Delivery fee |
| service_fee | NUMERIC(10,2) | YES | Service fee |
| commission_fee | NUMERIC(10,2) | YES | Commission fee |
| customer_name | VARCHAR(255) | YES | Customer |
| customer_phone | VARCHAR(50) | YES | Phone |
| server_name | VARCHAR(255) | YES | Server |
| is_voided | BOOLEAN | YES | Voided |
| is_deleted | BOOLEAN | YES | Deleted |
| contains_alcohol | BOOLEAN | YES | Contains alcohol |
| is_catering | BOOLEAN | YES | Catering |
| source_metadata | JSONB | YES | Source metadata. For DoorDash: contains `merchant_payout` (actual amount deposited to business, after fees) |
| updated_at | TIMESTAMPTZ | YES | Auto (trigger) |

**Relationships:**
- `orders.location_id` → `locations.id` (N:1)
- `order_items.order_id` → `orders.id` (1:N, CASCADE)
- `payments.order_id` → `orders.id` (1:N, CASCADE)
- `delivery_orders.order_id` → `orders.id` (1:1, CASCADE, UNIQUE)
- `toast_checks.order_id` → `orders.id` (1:N, CASCADE)

**Indexes:**
- `idx_orders_location_id` (location_id)
- `idx_orders_created_at` (created_at)
- `idx_orders_business_date` (business_date)
- `idx_orders_source` (source)
- `idx_orders_source_order_id` (source, source_order_id)
- `idx_orders_status` (status)
- `idx_orders_order_type` (order_type)
- `idx_orders_location_date` (location_id, business_date)
- `idx_orders_location_date_status` (location_id, business_date, status)
- `idx_orders_source_created` (source, created_at)

---

### order_items
**PK:** `id` (SERIAL)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | PK |
| order_id | INTEGER | NO | FK → orders.id (CASCADE) |
| product_id | INTEGER | YES | FK → products.id |
| item_name | VARCHAR(255) | NO | Item name (denormalized) |
| item_description | TEXT | YES | Description |
| quantity | NUMERIC(10,3) | NO | Quantity (default: 1) |
| unit_price | NUMERIC(10,2) | NO | Unit price |
| total_price | NUMERIC(10,2) | NO | Total price |
| tax_amount | NUMERIC(10,2) | YES | Tax (default: 0) |
| discount_amount | NUMERIC(10,2) | YES | Discount (default: 0) |
| sequence_number | INTEGER | YES | Sequence order |
| category_name | VARCHAR(255) | YES | Category (denormalized) |
| source_item_id | VARCHAR(255) | YES | ID in source |
| special_instructions | TEXT | YES | Instructions |
| source_metadata | JSONB | YES | Source metadata |
| created_at | TIMESTAMPTZ | YES | Auto |
| updated_at | TIMESTAMPTZ | YES | Auto (trigger) |

**Relationships:**
- `order_items.order_id` → `orders.id` (N:1, CASCADE)
- `order_items.product_id` → `products.id` (N:1)
- `order_item_modifiers.order_item_id` → `order_items.id` (1:N, CASCADE)

**Indexes:**
- `idx_order_items_order_id` (order_id)
- `idx_order_items_product_id` (product_id)
- `idx_order_items_category_name` (category_name)
- `idx_order_items_order_product` (order_id, product_id)
- `idx_order_items_source_metadata` (source_metadata, GIN)

---

### order_item_modifiers
**PK:** `id` (SERIAL)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | PK |
| order_item_id | INTEGER | NO | FK → order_items.id (CASCADE) |
| modifier_name | VARCHAR(255) | NO | Modifier name |
| modifier_value | VARCHAR(255) | YES | Modifier value |
| price_adjustment | NUMERIC(10,2) | YES | Price adjustment (default: 0) |
| quantity | INTEGER | YES | Quantity (default: 1) |
| source_modifier_id | VARCHAR(255) | YES | ID in source |
| extra_data | JSONB | YES | Metadata |
| created_at | TIMESTAMPTZ | YES | Auto |

**Relationships:**
- `order_item_modifiers.order_item_id` → `order_items.id` (N:1, CASCADE)

**Indexes:**
- `idx_order_item_modifiers_order_item_id` (order_item_id)

---

### payments
**PK:** `id` (SERIAL)  
**UNIQUE:** `(source, source_payment_id)`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | PK |
| order_id | INTEGER | NO | FK → orders.id (CASCADE) |
| source | OrderSourceEnum | NO | Source |
| source_payment_id | VARCHAR(255) | YES | ID in source |
| payment_type | PaymentTypeEnum | NO | Payment type |
| status | PaymentStatusEnum | YES | Status (default: completed) |
| amount | NUMERIC(10,2) | NO | Amount |
| tip_amount | NUMERIC(10,2) | YES | Tip (default: 0) |
| processing_fee | NUMERIC(10,2) | YES | Processing fee (default: 0) |
| processed_at | TIMESTAMPTZ | NO | Processed date |
| card_brand | VARCHAR(50) | YES | Card brand |
| card_last4 | VARCHAR(4) | YES | Last 4 digits |
| card_entry_method | VARCHAR(50) | YES | Entry method |
| wallet_brand | VARCHAR(50) | YES | Digital wallet |
| cash_tendered | NUMERIC(10,2) | YES | Cash tendered |
| change_amount | NUMERIC(10,2) | YES | Change |
| refund_amount | NUMERIC(10,2) | YES | Refund amount (default: 0) |
| refund_date | TIMESTAMPTZ | YES | Refund date |
| refund_reason | TEXT | YES | Refund reason |
| source_metadata | JSONB | YES | Source metadata |
| created_at | TIMESTAMPTZ | YES | Auto |
| updated_at | TIMESTAMPTZ | YES | Auto (trigger) |

**Relationships:**
- `payments.order_id` → `orders.id` (N:1, CASCADE)

**Indexes:**
- `idx_payments_order_id` (order_id)
- `idx_payments_payment_type` (payment_type)
- `idx_payments_card_brand` (card_brand)
- `idx_payments_status` (status)
- `idx_payments_processed_at` (processed_at)

---

### delivery_orders
**PK:** `id` (SERIAL)  
**UNIQUE:** `order_id`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | PK |
| order_id | INTEGER | NO | FK → orders.id (CASCADE, UNIQUE) |
| delivery_address_line1 | VARCHAR(255) | YES | Delivery address |
| delivery_address_line2 | VARCHAR(255) | YES | Address line 2 |
| delivery_city | VARCHAR(100) | YES | City |
| delivery_state | VARCHAR(50) | YES | State |
| delivery_zip_code | VARCHAR(20) | YES | Zip code |
| pickup_time | TIMESTAMPTZ | YES | Pickup time |
| delivery_time | TIMESTAMPTZ | YES | Delivery time |
| estimated_delivery_time | TIMESTAMPTZ | YES | Estimated time |
| delivery_instructions | TEXT | YES | Instructions |
| dasher_name | VARCHAR(255) | YES | Dasher name |
| dasher_id | VARCHAR(255) | YES | Dasher ID |
| delivery_fee | NUMERIC(10,2) | YES | Delivery fee |
| dasher_tip | NUMERIC(10,2) | YES | Dasher tip |
| extra_data | JSONB | YES | Metadata |
| created_at | TIMESTAMPTZ | YES | Auto |
| updated_at | TIMESTAMPTZ | YES | Auto (trigger) |

**Relationships:**
- `delivery_orders.order_id` → `orders.id` (1:1, CASCADE, UNIQUE)

**Indexes:**
- `idx_delivery_orders_order_id` (order_id)
- `idx_delivery_orders_pickup_time` (pickup_time)
- `idx_delivery_orders_delivery_time` (delivery_time)

---

### toast_checks
**PK:** `id` (SERIAL)  
**UNIQUE:** `source_check_id`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | PK |
| order_id | INTEGER | NO | FK → orders.id (CASCADE) |
| source_check_id | VARCHAR(255) | NO | Check ID in Toast (UNIQUE) |
| check_number | INTEGER | YES | Check number |
| table_name | VARCHAR(100) | YES | Table |
| opened_at | TIMESTAMPTZ | YES | Opened time |
| closed_at | TIMESTAMPTZ | YES | Closed time |
| subtotal | NUMERIC(10,2) | YES | Subtotal |
| tax_amount | NUMERIC(10,2) | YES | Tax |
| tip_amount | NUMERIC(10,2) | YES | Tip |
| total_amount | NUMERIC(10,2) | YES | Total |
| server_name | VARCHAR(255) | YES | Server |
| extra_data | JSONB | YES | Metadata |
| created_at | TIMESTAMPTZ | YES | Auto |
| updated_at | TIMESTAMPTZ | YES | Auto (trigger) |

**Relationships:**
- `toast_checks.order_id` → `orders.id` (N:1, CASCADE)

**Indexes:**
- `idx_toast_checks_order_id` (order_id)
- `idx_toast_checks_opened_at` (opened_at)
- `idx_toast_checks_closed_at` (closed_at)

## RELATIONSHIPS SUMMARY

```
locations (1) ──< (N) orders
categories (1) ──< (N) products
categories (1) ──< (N) categories (self-ref, parent_id)
products (1) ──< (N) product_mappings
products (1) ──< (N) order_items
orders (1) ──< (N) order_items
orders (1) ──< (N) payments
orders (1) ──< (1) delivery_orders
orders (1) ──< (N) toast_checks
order_items (1) ──< (N) order_item_modifiers
```

## IMPORTANT NOTES

- **CASCADE DELETE:** `order_items`, `payments`, `delivery_orders`, `toast_checks`, `order_item_modifiers`, `product_mappings` are deleted when their parent is deleted.
- **Triggers:** All tables with `updated_at` have a trigger that automatically updates it.
- **JSONB:** `source_ids`, `source_metadata`, `extra_data` are JSONB for flexible searches. Access with `->` or `->>` operators (e.g., `source_ids->>'TOAST'`).
- **Denormalization:** `order_items.item_name`, `order_items.category_name` preserve historical data even if products change. Use these for product analysis queries.
- **Locations:** Each location has a single `source_id` in `source_ids` JSONB per source. Multiple locations can represent the same physical restaurant in different sources.
- **Extensions:** `pg_trgm` enabled for fuzzy text search.

## QUERY GUIDANCE

### Sales/Revenue Queries
- **Sales/Revenue** typically refers to `orders.total_amount` filtered by `status = 'completed'`
- **Sales** can also mean:
  - Revenue: `SUM(orders.total_amount)` 
  - Order count: `COUNT(orders.id)`
  - Items sold: `SUM(order_items.quantity)`
- Always filter by `orders.status = 'COMPLETED'` for actual sales (exclude PENDING, CANCELLED, REFUNDED)

### Date/Time Fields
- **`business_date`** (DATE): Use for business day analysis (e.g., "sales yesterday", "revenue on January 2nd")
- **`created_at`** (TIMESTAMPTZ): Use for precise timestamp analysis (e.g., hourly sales: `EXTRACT(HOUR FROM created_at)`)
- **`closed_at`** (TIMESTAMPTZ): Order completion time (may be NULL for pending orders)
- **`opened_at`** (TIMESTAMPTZ): Available in `toast_checks` table for Toast orders

### Location Queries
- Join `orders` with `locations` via `orders.location_id = locations.id`
- Filter by `locations.name` for location-specific queries

### Product/Item Queries
- Use `order_items.item_name` for item names (denormalized, preserves historical)
- Use `order_items.category_name` for category filtering (denormalized)
- Join with `products` via `order_items.product_id = products.id` for product details
- Join with `categories` via `products.category_id = categories.id` or use `order_items.category_name`
- Top selling items: Use `SUM(order_items.quantity)` or `SUM(order_items.total_price)`

### Order Type/Channel Queries
- Filter by `orders.order_type` (DINE_IN, TAKEOUT, DELIVERY, PICKUP)
- Filter by `orders.source` (TOAST, DOORDASH, SQUARE) for channel analysis
- DoorDash orders: `orders.source = 'DOORDASH'`
- Delivery orders: `orders.order_type = 'DELIVERY'` OR check `delivery_orders` table exists

### DoorDash Merchant Payout
- **Important:** For DoorDash orders, `orders.total_amount` represents the total charged to the customer, but the actual amount deposited to the business is stored in `orders.source_metadata->>'merchant_payout'`
- DoorDash deducts commission fees, service fees, etc. from the total before depositing to the merchant
- Example: `source_metadata` may contain `{"order_status": "DELIVERED", "merchant_payout": 1104, "fulfillment_method": "MERCHANT_DELIVERY"}`
- To get actual revenue received: `CAST(orders.source_metadata->>'merchant_payout' AS NUMERIC)` for DoorDash orders
- The difference between `total_amount` and `merchant_payout` represents fees and commissions

### Payment Queries
- Join `payments` with `orders` via `payments.order_id = orders.id`
- Filter by `payments.payment_type` (CARD, CASH, DIGITAL_WALLET, OTHER, UNKNOWN)
- Popular payment methods: `COUNT(*)` or `SUM(payments.amount)` grouped by `payment_type`

### Aggregations
- Revenue: `SUM(orders.total_amount) WHERE status = 'COMPLETED'`
- Average order value: `AVG(orders.total_amount) WHERE status = 'COMPLETED'`
- Order count: `COUNT(orders.id) WHERE status = 'COMPLETED'`
- Items sold: `SUM(order_items.quantity)`
- Hourly analysis: `EXTRACT(HOUR FROM orders.created_at)`
- Daily analysis: `orders.business_date` or `DATE(orders.created_at)`

### Common JOIN Patterns
- Orders with location: `orders JOIN locations ON orders.location_id = locations.id`
- Orders with items: `orders JOIN order_items ON orders.id = order_items.order_id`
- Items with products: `order_items LEFT JOIN products ON order_items.product_id = products.id`
- Items with categories: Use `order_items.category_name` directly OR `order_items JOIN products JOIN categories`
- Orders with payments: `orders JOIN payments ON orders.id = payments.order_id`

