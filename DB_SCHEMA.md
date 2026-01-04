# Database Schema Reference

PostgreSQL database for restaurant analytics. Unified schema from multiple POS sources (Toast, DoorDash, Square).

---

## 📊 Database Schema Overview & Normalization Process

### The Challenge: Unifying Three Different POS Systems

This database consolidates data from **three distinct POS systems** (Toast, DoorDash, Square), each with:
- **Different data structures**: Toast uses nested JSON, Square splits data across 4 files, DoorDash has delivery-specific fields
- **Inconsistent naming**: Same products named differently ("Hash Browns" vs "Hashbrowns", "🍔 Burgers" vs "Burgers")
- **Different identifiers**: Each system uses its own location/product IDs
- **Data quality issues**: Typos ("Griled Chiken", "expresso"), missing fields, format variations

### How the Unified Schema Was Designed

The schema design followed a **normalized relational model** approach:

1. **Core Entities Identified**: Locations, Products, Categories, Orders, Payments
2. **Source-Agnostic Design**: Created generic tables that can represent data from any POS system
3. **Mapping Strategy**: Used `product_mappings` and `source_ids` JSONB fields to maintain source-specific IDs while having unified records
4. **Denormalization for Performance**: Added `order_items.item_name` and `order_items.category_name` to preserve historical data even if products change

### Data Normalization Process

The normalization happens in **multiple layers**:

#### 1. **Python ETL Scripts** (`my-api/scripts/`)

**Key Scripts:**
- `load_all_data.py` - Master orchestrator that loads all sources
- `load_toast_data.py` - Handles Toast POS nested JSON structure
- `load_doordash_data.py` - Processes DoorDash delivery-specific data
- `load_square_data.py` - Merges Square's 4 separate files (catalog, locations, orders, payments)
- `etl_utils.py` - **Core normalization utilities**

**Normalization Functions in `etl_utils.py`:**

```python
DataNormalizer.normalize_name(name)
# - Lowercases text
# - Removes emojis and special characters
# - Normalizes whitespace
# Example: "🍔 Burgers" → "burgers"

DataNormalizer.clean_product_name(name)
# - Fixes common typos (Griled → Grilled, Chiken → Chicken)
# - Title cases properly
# Example: "Griled Chiken Sandwich" → "Grilled Chicken Sandwich"

DataNormalizer.normalize_product_base_name(name)
# - Removes size variations ("Large", "Small", "Medium")
# - Removes style/flavor variations ("Chocolate", "Vanilla")
# - Removes quantity indicators ("12Pc", "6 pieces")
# - Unifies product variations:
#   - "French Fries - Large" → "French Fries"
#   - "Truffle Fries" → "French Fries" (style variation)
#   - "Wings 12Pc" → "Buffalo Wings"
#   - "Hashbrowns" → "Hash Browns"
```

#### 2. **PostgreSQL Functions** (`my-api/sql/etl_functions.sql`)

**Key Functions:**

```sql
get_or_create_category(category_name)
# - Normalizes category names (removes emojis, fixes typos)
# - Handles synonyms ("Drinks" → "Beverages", "Sides" → "Appetizers")
# - Creates or retrieves category with normalized name
# - Stores all source variants in source_names JSONB

get_location_id_by_source(source, source_id)
# - Maps source-specific location IDs to unified location records
# - Uses JSONB source_ids field for flexible lookup
```

#### 3. **Fuzzy Matching** (PostgreSQL `pg_trgm` extension)

- **Trigram indexes** on product names enable fuzzy text search
- Handles spelling variations and typos
- Used when matching products across sources

### Normalization Flow Example

**Input (3 different sources):**
- Toast: `"Hashbrowns"` (category: `"🍔 Breakfast"`)
- Square: `"Hash Browns - Large"` (category: `"Breakfast Items"`)
- DoorDash: `"Hash Browns"` (category: `"Sides"`)

**Normalization Steps:**

1. **Product Name Normalization:**
   - `"Hashbrowns"` → `"Hash Browns"` (spelling fix)
   - `"Hash Browns - Large"` → `"Hash Browns"` (size removal)
   - `"Hash Browns"` → `"Hash Browns"` (already normalized)

2. **Category Normalization:**
   - `"🍔 Breakfast"` → `"Breakfast"` (emoji removal)
   - `"Breakfast Items"` → `"Breakfast"` (synonym handling)
   - `"Sides"` → `"Appetizers"` (synonym mapping)

3. **Result:**
   - All three map to same `products` record: `name="Hash Browns"`, `normalized_name="hash browns"`
   - Category: `"Breakfast"` (or `"Appetizers"` depending on business logic)
   - Three `product_mappings` records link source-specific IDs to unified product

### Database Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATABASE RELATIONSHIPS                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────┐
│  locations  │ (1)
│  (id, name) │
└──────┬──────┘
       │ 1:N
       │
       ▼
┌─────────────┐
│   orders    │ (N)
│  (id, ...)  │
└──────┬──────┘
       │
       ├─── 1:N ───► ┌──────────────┐
       │             │ order_items   │ (N)
       │             │ (id, ...)     │
       │             └───────┬───────┘
       │                     │
       │                     ├─── N:1 ───► ┌─────────────┐
       │                     │             │  products   │ (1)
       │                     │             │  (id, ...)   │
       │                     │             └───────┬─────┘
       │                     │                     │
       │                     │                     ├─── N:1 ───► ┌──────────────┐
       │                     │                     │             │  categories  │ (1)
       │                     │                     │             │  (id, ...)   │
       │                     │                     │             └──────────────┘
       │                     │                     │
       │                     │                     └─── 1:N ───► ┌──────────────────┐
       │                     │                                   │ product_mappings│ (N)
       │                     │                                   │  (id, ...)       │
       │                     │                                   └──────────────────┘
       │                     │
       │                     └─── 1:N ───► ┌────────────────────┐
       │                                   │order_item_modifiers│ (N)
       │                                   │  (id, ...)         │
       │                                   └────────────────────┘
       │
       ├─── 1:N ───► ┌─────────────┐
       │             │  payments   │ (N)
       │             │  (id, ...)  │
       │             └─────────────┘
       │
       ├─── 1:1 ───► ┌─────────────────┐
       │             │ delivery_orders │ (1)
       │             │  (id, ...)     │
       │             └─────────────────┘
       │
       └─── 1:N ───► ┌──────────────┐
                     │ toast_checks │ (N)
                     │  (id, ...)   │
                     └──────────────┘

┌──────────────┐
│  categories  │ (self-reference)
│  (id, ...)   │
└───────┬──────┘
        │
        └─── 1:N (parent_id) ───► ┌──────────────┐
                                   │  categories  │ (child)
                                   │  (id, ...)   │
                                   └──────────────┘

LEGEND:
(1) = One
(N) = Many
1:N = One-to-Many relationship
1:1 = One-to-One relationship
N:1 = Many-to-One relationship (reverse of 1:N)
```

### Key Design Decisions

1. **JSONB for Flexibility**: `source_ids`, `source_metadata`, `extra_data` use JSONB to store source-specific data without schema changes
2. **Denormalization**: `order_items.item_name` and `order_items.category_name` preserve historical data even if products are renamed
3. **CASCADE Deletes**: Related records (order_items, payments, etc.) are automatically deleted when parent (order) is deleted
4. **Source Mapping**: `product_mappings` table maintains links between unified products and source-specific product IDs
5. **Location Strategy**: Each physical location can have multiple records (one per source) with different `source_ids`, or a single record with all source IDs in JSONB

---

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

