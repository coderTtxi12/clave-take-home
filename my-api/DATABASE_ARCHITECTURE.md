# Database Architecture - Restaurant Analytics

Documentación completa del esquema de base de datos, relaciones, funciones, triggers y procesos ETL.

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Esquema de Base de Datos](#esquema-de-base-de-datos)
3. [Tablas y Relaciones](#tablas-y-relaciones)
4. [Funciones PostgreSQL](#funciones-postgresql)
5. [Triggers](#triggers)
6. [Índices y Optimización](#índices-y-optimización)
7. [Proceso ETL](#proceso-etl)
8. [Tipos de Datos (ENUMs)](#tipos-de-datos-enums)
9. [Ejemplos de Consultas](#ejemplos-de-consultas)

---

## Visión General

### Propósito

Esta base de datos centraliza datos de ventas de múltiples sistemas POS (Point of Sale) en un esquema unificado para análisis y reporting.

### Fuentes de Datos

- **Toast POS** - Sistema principal de restaurantes
- **DoorDash** - Plataforma de delivery
- **Square POS** - Sistema alternativo de pagos

### Tecnología

- **PostgreSQL 15** - Base de datos relacional
- **Alembic** - Sistema de migraciones
- **SQLAlchemy** - ORM (Object-Relational Mapping)

---

## Esquema de Base de Datos

### Diagrama Conceptual

```
┌─────────────┐
│  locations  │◄─────┐
└─────────────┘      │
                     │
┌─────────────┐      │     ┌──────────────┐
│ categories  │      │     │    orders    │
└─────────────┘      │     └──────────────┘
       ▲             │            │
       │             │            │
       │         ┌───┴────┐       │
       │         │        │       │
┌─────────────┐  │  ┌─────▼──────▼─────┐
│  products   │  │  │   order_items    │
└─────────────┘  │  └──────────────────┘
       │         │         │
       │         │         │
       ▼         │         ▼
┌──────────────┐ │  ┌──────────────────┐
│product_      │ │  │order_item_       │
│mappings      │ │  │modifiers         │
└──────────────┘ │  └──────────────────┘
                 │
                 │  ┌──────────────────┐
                 └─►│    payments      │
                    └──────────────────┘
                    
                    ┌──────────────────┐
                    │delivery_orders   │
                    └──────────────────┘
                    
                    ┌──────────────────┐
                    │  toast_checks    │
                    └──────────────────┘
```

---

## Tablas y Relaciones

### 1. `locations` - Ubicaciones de Restaurantes

Almacena información de las ubicaciones físicas de los restaurantes.

**Importante:** Cada location se mantiene separada por fuente (source) para preservar la trazabilidad. Esto significa que si el mismo restaurante físico existe en Toast, DoorDash y Square, habrá 3 registros de location diferentes, cada uno con su propio `source_ids`.

**Columnas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | PK - ID único autoincremental |
| `name` | VARCHAR(255) | Nombre de la ubicación |
| `address_line1` | VARCHAR(255) | Dirección principal |
| `address_line2` | VARCHAR(255) | Dirección secundaria (opcional) |
| `city` | VARCHAR(100) | Ciudad |
| `state` | VARCHAR(50) | Estado/Provincia |
| `zip_code` | VARCHAR(20) | Código postal |
| `country` | VARCHAR(2) | Código de país (ISO 2) |
| `timezone` | VARCHAR(50) | Zona horaria |
| `source_ids` | JSONB | ID de la ubicación en el sistema fuente |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `updated_at` | TIMESTAMPTZ | Fecha de última actualización |

**Relaciones:**
- `orders` → `location_id` (1:N)

**source_ids Format:**
```json
{
  "TOAST": "toast-location-123"
}
```
o
```json
{
  "SQUARE": "sq0idp-abc123"
}
```

**Nota de Diseño:**
- Cada location tiene un solo `source_id` en `source_ids` (una location por fuente)
- Las orders de cada fuente apuntan a su location específica
- Esto permite rastrear exactamente qué location de qué fuente se usó para cada orden

---

### 2. `categories` - Categorías de Productos

Clasificación jerárquica de productos.

**Columnas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | PK - ID único |
| `name` | VARCHAR(255) | Nombre de la categoría (único) |
| `normalized_name` | VARCHAR(255) | Nombre normalizado para búsqueda |
| `parent_id` | INTEGER | FK - Categoría padre (jerarquía) |
| `sort_order` | INTEGER | Orden de visualización |
| `source_names` | JSONB | Nombres en cada sistema fuente |
| `description` | TEXT | Descripción |
| `extra_data` | JSONB | Metadata adicional |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `updated_at` | TIMESTAMPTZ | Fecha de última actualización |

**Relaciones:**
- Self-referencing: `parent_id` → `categories.id` (jerarquía)
- `products` → `category_id` (1:N)

**Constraints:**
- UNIQUE: `name`
- FOREIGN KEY: `parent_id` → `categories.id`

**Ejemplo de Jerarquía:**
```
Food (parent_id = NULL)
├── Appetizers (parent_id = 1)
├── Main Dishes (parent_id = 1)
└── Desserts (parent_id = 1)
```

---

### 3. `products` - Productos/Items del Menú

Catálogo unificado de productos de todos los sistemas.

**Columnas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | PK - ID único |
| `name` | VARCHAR(255) | Nombre del producto |
| `normalized_name` | VARCHAR(255) | Nombre normalizado |
| `description` | TEXT | Descripción del producto |
| `category_id` | INTEGER | FK - Categoría |
| `base_price` | DECIMAL(10,2) | Precio base |
| `cost` | DECIMAL(10,2) | Costo del producto |
| `sku` | VARCHAR(100) | SKU (Stock Keeping Unit) |
| `is_active` | BOOLEAN | Si está disponible |
| `extra_data` | JSONB | Metadata adicional |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `updated_at` | TIMESTAMPTZ | Fecha de última actualización |

**Relaciones:**
- `category_id` → `categories.id` (N:1)
- `product_mappings` → `product_id` (1:N)
- `order_items` → `product_id` (1:N)

**Índices especiales:**
- `idx_products_name_trgm` - Búsqueda de texto con trigram (GIN)
- `idx_products_normalized_name` - Búsqueda rápida normalizada
- `idx_products_category_id` - Filtrado por categoría

---

### 4. `product_mappings` - Mapeo de Productos entre Sistemas

Relaciona productos de diferentes sistemas fuente al catálogo unificado.

**Columnas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | PK - ID único |
| `product_id` | INTEGER | FK - Producto unificado |
| `source` | ENUM | Sistema fuente (toast/doordash/square) |
| `source_product_id` | VARCHAR(255) | ID del producto en el sistema fuente |
| `source_name` | VARCHAR(255) | Nombre en el sistema fuente |
| `source_price` | DECIMAL(10,2) | Precio en el sistema fuente |
| `is_active` | BOOLEAN | Si el mapeo está activo |
| `extra_data` | JSONB | Metadata adicional |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `updated_at` | TIMESTAMPTZ | Fecha de última actualización |

**Relaciones:**
- `product_id` → `products.id` (N:1)

**Constraints:**
- UNIQUE: `(source, source_product_id)`

**Ejemplo:**
```
Producto unificado: "Cheeseburger" (id=1)
├── Toast: "Classic Cheeseburger" (toast-item-123)
├── Square: "Cheese Burger" (sq0-item-456)
└── DoorDash: "Cheeseburger Deluxe" (dd-item-789)
```

---

### 5. `orders` - Órdenes/Pedidos

Tabla principal de transacciones de ventas.

**Columnas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | PK - ID único |
| `source` | ENUM | Sistema fuente (toast/doordash/square) |
| `source_order_id` | VARCHAR(255) | ID de la orden en el sistema fuente |
| `location_id` | INTEGER | FK - Ubicación del restaurante |
| `order_number` | VARCHAR(100) | Número de orden visible |
| `order_type` | ENUM | Tipo: dine_in/takeout/delivery/pickup |
| `status` | ENUM | Estado: pending/completed/cancelled/refunded |
| `business_date` | DATE | Fecha de negocio (no necesariamente fecha actual) |
| `opened_at` | TIMESTAMPTZ | Momento de apertura de la orden |
| `closed_at` | TIMESTAMPTZ | Momento de cierre/finalización |
| `subtotal_amount` | DECIMAL(10,2) | Subtotal antes de impuestos y propinas |
| `tax_amount` | DECIMAL(10,2) | Monto de impuestos |
| `tip_amount` | DECIMAL(10,2) | Propina |
| `discount_amount` | DECIMAL(10,2) | Descuentos aplicados |
| `total_amount` | DECIMAL(10,2) | Total final |
| `customer_name` | VARCHAR(255) | Nombre del cliente |
| `customer_phone` | VARCHAR(50) | Teléfono del cliente |
| `customer_email` | VARCHAR(255) | Email del cliente |
| `notes` | TEXT | Notas de la orden |
| `extra_data` | JSONB | Metadata adicional del sistema fuente |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `updated_at` | TIMESTAMPTZ | Fecha de última actualización |

**Relaciones:**
- `location_id` → `locations.id` (N:1)
- `order_items` → `order_id` (1:N)
- `payments` → `order_id` (1:N)
- `delivery_orders` → `order_id` (1:1)
- `toast_checks` → `order_id` (1:1)

**Constraints:**
- UNIQUE: `(source, source_order_id)`

**Índices importantes:**
- `idx_orders_business_date` - Análisis por fecha
- `idx_orders_location_date_status` - Reportes por ubicación y fecha
- `idx_orders_source` - Filtrado por fuente

---

### 6. `order_items` - Items de las Órdenes

Productos individuales dentro de cada orden.

**Columnas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | PK - ID único |
| `order_id` | INTEGER | FK - Orden padre |
| `product_id` | INTEGER | FK - Producto (puede ser NULL si no está mapeado) |
| `product_name` | VARCHAR(255) | Nombre del producto (para preservar histórico) |
| `category_name` | VARCHAR(255) | Categoría (para preservar histórico) |
| `quantity` | INTEGER | Cantidad |
| `unit_price` | DECIMAL(10,2) | Precio unitario |
| `gross_amount` | DECIMAL(10,2) | Monto bruto |
| `discount_amount` | DECIMAL(10,2) | Descuento en este item |
| `net_amount` | DECIMAL(10,2) | Monto neto (gross - discount) |
| `tax_amount` | DECIMAL(10,2) | Impuesto en este item |
| `notes` | TEXT | Notas especiales |
| `source_item_id` | VARCHAR(255) | ID del item en el sistema fuente |
| `source_metadata` | JSONB | Metadata del sistema fuente |
| `created_at` | TIMESTAMPTZ | Fecha de creación |

**Relaciones:**
- `order_id` → `orders.id` (N:1) CASCADE DELETE
- `product_id` → `products.id` (N:1) SET NULL
- `order_item_modifiers` → `order_item_id` (1:N)

**Constraints:**
- FOREIGN KEY: `order_id` → `orders.id` ON DELETE CASCADE

**Notas de Diseño:**
- `product_name` y `category_name` preservan el histórico aunque el producto cambie
- `product_id` puede ser NULL para productos no mapeados

---

### 7. `order_item_modifiers` - Modificadores de Items

Personalizaciones y ajustes a los items (ej: "sin cebolla", "extra queso").

**Columnas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | PK - ID único |
| `order_item_id` | INTEGER | FK - Item padre |
| `modifier_name` | VARCHAR(255) | Nombre del modificador |
| `modifier_value` | VARCHAR(255) | Valor del modificador |
| `price_adjustment` | DECIMAL(10,2) | Ajuste de precio (+/-) |
| `quantity` | INTEGER | Cantidad del modificador |
| `source_modifier_id` | VARCHAR(255) | ID en el sistema fuente |
| `extra_data` | JSONB | Metadata adicional |
| `created_at` | TIMESTAMPTZ | Fecha de creación |

**Relaciones:**
- `order_item_id` → `order_items.id` (N:1) CASCADE DELETE

**Ejemplos:**
```
Cheeseburger
├── Extra Cheese (+$1.50)
├── No Onions ($0.00)
└── Add Bacon (+$2.00)
```

---

### 8. `payments` - Pagos

Información de pagos realizados para las órdenes.

**Columnas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | PK - ID único |
| `order_id` | INTEGER | FK - Orden |
| `payment_type` | ENUM | Tipo: card/cash/digital_wallet/other |
| `status` | ENUM | Estado: pending/completed/failed/refunded |
| `amount` | DECIMAL(10,2) | Monto del pago |
| `tip_amount` | DECIMAL(10,2) | Propina incluida |
| `card_brand` | VARCHAR(50) | Marca de tarjeta (Visa, MC, etc.) |
| `last_4` | VARCHAR(4) | Últimos 4 dígitos |
| `processed_at` | TIMESTAMPTZ | Momento del procesamiento |
| `source_payment_id` | VARCHAR(255) | ID en el sistema fuente |
| `extra_data` | JSONB | Metadata adicional |
| `created_at` | TIMESTAMPTZ | Fecha de creación |

**Relaciones:**
- `order_id` → `orders.id` (N:1) CASCADE DELETE

**Índices:**
- `idx_payments_order_id` - Búsqueda por orden
- `idx_payments_payment_type` - Análisis por tipo de pago
- `idx_payments_card_brand` - Análisis por marca de tarjeta
- `idx_payments_processed_at` - Análisis temporal

**Notas:**
- Una orden puede tener múltiples pagos (split payments)
- La suma de payments.amount debería igualar orders.total_amount

---

### 9. `delivery_orders` - Órdenes de Delivery

Información específica de órdenes de entrega (principalmente DoorDash).

**Columnas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | PK - ID único |
| `order_id` | INTEGER | FK - Orden (UNIQUE) |
| `delivery_address_line1` | VARCHAR(255) | Dirección de entrega |
| `delivery_address_line2` | VARCHAR(255) | Dirección secundaria |
| `delivery_city` | VARCHAR(100) | Ciudad |
| `delivery_state` | VARCHAR(50) | Estado |
| `delivery_zip_code` | VARCHAR(20) | Código postal |
| `driver_name` | VARCHAR(255) | Nombre del repartidor |
| `driver_phone` | VARCHAR(50) | Teléfono del repartidor |
| `pickup_time` | TIMESTAMPTZ | Hora de recogida |
| `delivery_time` | TIMESTAMPTZ | Hora de entrega |
| `delivery_instructions` | TEXT | Instrucciones especiales |
| `extra_data` | JSONB | Metadata adicional |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `updated_at` | TIMESTAMPTZ | Fecha de última actualización |

**Relaciones:**
- `order_id` → `orders.id` (1:1) CASCADE DELETE

**Constraints:**
- UNIQUE: `order_id`

---

### 10. `toast_checks` - Checks de Toast POS

Información específica del sistema Toast (concepto de "check" o cuenta).

**Columnas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | SERIAL | PK - ID único |
| `order_id` | INTEGER | FK - Orden |
| `source_check_id` | VARCHAR(255) | ID del check en Toast (UNIQUE) |
| `check_number` | VARCHAR(50) | Número de check visible |
| `table_number` | VARCHAR(50) | Número de mesa |
| `guest_count` | INTEGER | Número de comensales |
| `opened_at` | TIMESTAMPTZ | Hora de apertura del check |
| `closed_at` | TIMESTAMPTZ | Hora de cierre del check |
| `server_name` | VARCHAR(255) | Nombre del mesero |
| `extra_data` | JSONB | Metadata adicional |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `updated_at` | TIMESTAMPTZ | Fecha de última actualización |

**Relaciones:**
- `order_id` → `orders.id` (N:1) CASCADE DELETE

**Constraints:**
- UNIQUE: `source_check_id`

---

## Funciones PostgreSQL

### 1. `update_updated_at_column()` - Trigger Function

**Propósito:** Actualiza automáticamente la columna `updated_at` cuando se modifica un registro.

**Definición:**
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Uso:** Se aplica mediante triggers a todas las tablas con columna `updated_at`.

---

### 2. `get_location_id_by_source()` - Helper ETL

**Propósito:** Encuentra el ID de location basado en el source y source_id.

**Ubicación:** `sql/etl_functions.sql`

**Definición:**
```sql
CREATE OR REPLACE FUNCTION get_location_id_by_source(
    p_source VARCHAR,
    p_source_id VARCHAR
)
RETURNS INTEGER AS $$
DECLARE
    v_location_id INTEGER;
BEGIN
    SELECT id INTO v_location_id
    FROM locations
    WHERE source_ids->>p_source = p_source_id;
    
    RETURN v_location_id;
END;
$$ LANGUAGE plpgsql;
```

**Uso en ETL:**
```python
cursor.execute("""
    SELECT get_location_id_by_source('toast', %s)
""", (toast_location_id,))
```

---

### 3. `get_or_create_category()` - Helper ETL

**Propósito:** Obtiene o crea una categoría, normalizando su nombre.

**Ubicación:** `sql/etl_functions.sql`

**Definición:**
```sql
CREATE OR REPLACE FUNCTION get_or_create_category(
    p_category_name VARCHAR
)
RETURNS INTEGER AS $$
DECLARE
    v_category_id INTEGER;
    v_normalized_name VARCHAR;
BEGIN
    v_normalized_name := LOWER(TRIM(p_category_name));
    
    SELECT id INTO v_category_id
    FROM categories
    WHERE normalized_name = v_normalized_name;
    
    IF v_category_id IS NULL THEN
        INSERT INTO categories (name, normalized_name)
        VALUES (p_category_name, v_normalized_name)
        RETURNING id INTO v_category_id;
    END IF;
    
    RETURN v_category_id;
END;
$$ LANGUAGE plpgsql;
```

**Uso en ETL:**
```python
cursor.execute("""
    SELECT get_or_create_category(%s)
""", (category_name,))
category_id = cursor.fetchone()[0]
```

---

### 4. `validate_etl_data()` - Validación Post-ETL

**Propósito:** Valida la integridad de los datos después de cargar.

**Ubicación:** `sql/etl_functions.sql`

**Definición:**
```sql
CREATE OR REPLACE FUNCTION validate_etl_data()
RETURNS TABLE(
    check_name VARCHAR,
    status VARCHAR,
    details TEXT
) AS $$
BEGIN
    -- Check 1: Orders without location
    RETURN QUERY
    SELECT 
        'Orders without location'::VARCHAR,
        CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END::VARCHAR,
        'Found ' || COUNT(*) || ' orders'::TEXT
    FROM orders WHERE location_id IS NULL;
    
    -- Check 2: Order items without order
    RETURN QUERY
    SELECT 
        'Orphan order items'::VARCHAR,
        CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END::VARCHAR,
        'Found ' || COUNT(*) || ' items'::TEXT
    FROM order_items oi
    WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.id = oi.order_id);
    
    -- More checks...
END;
$$ LANGUAGE plpgsql;
```

**Uso:**
```sql
SELECT * FROM validate_etl_data();
```

---

## Triggers

Todos los triggers usan la función `update_updated_at_column()` para mantener actualizada la columna `updated_at`.

### Lista de Triggers

| Tabla | Trigger | Evento | Función |
|-------|---------|--------|---------|
| `locations` | `update_locations_updated_at` | BEFORE UPDATE | `update_updated_at_column()` |
| `categories` | `update_categories_updated_at` | BEFORE UPDATE | `update_updated_at_column()` |
| `products` | `update_products_updated_at` | BEFORE UPDATE | `update_updated_at_column()` |
| `product_mappings` | `update_product_mappings_updated_at` | BEFORE UPDATE | `update_updated_at_column()` |
| `orders` | `update_orders_updated_at` | BEFORE UPDATE | `update_updated_at_column()` |
| `order_items` | `update_order_items_updated_at` | BEFORE UPDATE | `update_updated_at_column()` |
| `payments` | `update_payments_updated_at` | BEFORE UPDATE | `update_updated_at_column()` |
| `delivery_orders` | `update_delivery_orders_updated_at` | BEFORE UPDATE | `update_updated_at_column()` |
| `toast_checks` | `update_toast_checks_updated_at` | BEFORE UPDATE | `update_updated_at_column()` |

### Ejemplo de Trigger

```sql
CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## Índices y Optimización

### Índices por Performance

#### Búsqueda de Texto (Trigram - pg_trgm)

```sql
-- Búsqueda fuzzy de productos por nombre
CREATE INDEX idx_products_name_trgm 
ON products USING gin (name gin_trgm_ops);
```

**Uso:**
```sql
SELECT * FROM products 
WHERE name % 'burguer';  -- Encuentra "Burger" con typo
```

#### Índices Compuestos

```sql
-- Análisis por ubicación y fecha
CREATE INDEX idx_orders_location_date_status 
ON orders (location_id, business_date, status);
```

**Uso:**
```sql
SELECT * FROM orders 
WHERE location_id = 1 
  AND business_date = '2025-12-31'
  AND status = 'completed';
```

#### Índices JSONB (GIN)

```sql
-- Búsqueda en metadata
CREATE INDEX idx_order_items_source_metadata 
ON order_items USING gin (source_metadata);
```

**Uso:**
```sql
SELECT * FROM order_items 
WHERE source_metadata @> '{"special_request": true}';
```

### Lista Completa de Índices

| Tabla | Índice | Columnas | Tipo |
|-------|--------|----------|------|
| `categories` | `idx_categories_normalized_name` | `normalized_name` | B-tree |
| `products` | `idx_products_name_trgm` | `name` | GIN (trigram) |
| `products` | `idx_products_normalized_name` | `normalized_name` | B-tree |
| `products` | `idx_products_category_id` | `category_id` | B-tree |
| `product_mappings` | `idx_product_mappings_product_id` | `product_id` | B-tree |
| `product_mappings` | `idx_product_mappings_source` | `source, source_product_id` | B-tree |
| `orders` | `idx_orders_business_date` | `business_date` | B-tree |
| `orders` | `idx_orders_created_at` | `created_at` | B-tree |
| `orders` | `idx_orders_location_id` | `location_id` | B-tree |
| `orders` | `idx_orders_location_date` | `location_id, business_date` | B-tree |
| `orders` | `idx_orders_location_date_status` | `location_id, business_date, status` | B-tree |
| `orders` | `idx_orders_source` | `source` | B-tree |
| `orders` | `idx_orders_source_created` | `source, created_at` | B-tree |
| `orders` | `idx_orders_source_order_id` | `source, source_order_id` | B-tree |
| `orders` | `idx_orders_status` | `status` | B-tree |
| `orders` | `idx_orders_order_type` | `order_type` | B-tree |
| `order_items` | `idx_order_items_order_id` | `order_id` | B-tree |
| `order_items` | `idx_order_items_product_id` | `product_id` | B-tree |
| `order_items` | `idx_order_items_order_product` | `order_id, product_id` | B-tree |
| `order_items` | `idx_order_items_category_name` | `category_name` | B-tree |
| `order_items` | `idx_order_items_source_metadata` | `source_metadata` | GIN |
| `order_item_modifiers` | `idx_order_item_modifiers_order_item_id` | `order_item_id` | B-tree |
| `payments` | `idx_payments_order_id` | `order_id` | B-tree |
| `payments` | `idx_payments_payment_type` | `payment_type` | B-tree |
| `payments` | `idx_payments_card_brand` | `card_brand` | B-tree |
| `payments` | `idx_payments_processed_at` | `processed_at` | B-tree |
| `payments` | `idx_payments_status` | `status` | B-tree |
| `delivery_orders` | `idx_delivery_orders_order_id` | `order_id` | B-tree |
| `delivery_orders` | `idx_delivery_orders_pickup_time` | `pickup_time` | B-tree |
| `delivery_orders` | `idx_delivery_orders_delivery_time` | `delivery_time` | B-tree |
| `toast_checks` | `idx_toast_checks_order_id` | `order_id` | B-tree |
| `toast_checks` | `idx_toast_checks_opened_at` | `opened_at` | B-tree |
| `toast_checks` | `idx_toast_checks_closed_at` | `closed_at` | B-tree |

---

## Proceso ETL

### Arquitectura ETL

```
┌─────────────────┐
│  Data Sources   │
└────────┬────────┘
         │
         ├──► Toast POS (toast_pos_export.json)
         ├──► DoorDash (doordash_orders.json)
         └──► Square POS (square/*.json)
         │
         ▼
┌─────────────────┐
│  ETL Scripts    │
├─────────────────┤
│ • load_toast.py │
│ • load_dd.py    │
│ • load_sq.py    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Transform     │
├─────────────────┤
│ • Normalize     │
│ • Validate      │
│ • Map IDs       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│ restaurant_     │
│ analytics       │
└─────────────────┘
```

### Scripts ETL

| Script | Fuente | Descripción |
|--------|--------|-------------|
| `load_toast_data.py` | Toast POS | Carga órdenes, checks, items, payments de Toast |
| `load_doordash_data.py` | DoorDash | Carga órdenes de delivery de DoorDash |
| `load_square_data.py` | Square POS | Carga catálogo, órdenes y pagos de Square |
| `load_all_data.py` | Todas | Ejecuta todos los scripts en orden |
| `etl_utils.py` | Helper | Funciones compartidas y utilidades |

### Flujo ETL - Toast POS

1. **Extract:** Lee `toast_pos_export.json`
2. **Transform:**
   - Normaliza tipo de orden (dine_in, takeout, etc.)
   - Calcula totales y subtotales
   - Normaliza nombres de productos
   - Corrige datos de ubicación (ej: "Jamaica, NY" → "New York, NY")
3. **Load:**
   - `locations` (una location por cada location de Toast, con `source_ids={'TOAST': 'toast-id'}`)
   - `orders` (con `source='TOAST'` y `location_id` apuntando a la location de Toast)
   - `toast_checks`
   - `order_items` con sus modifiers
   - `payments`

**Ejemplo de código:**
```python
# Cargar orden
cursor.execute("""
    INSERT INTO orders (
        source, source_order_id, location_id, 
        order_type, status, total_amount, ...
    ) VALUES (%s, %s, %s, %s, %s, %s, ...)
    RETURNING id
""", (
    'toast', toast_order_id, location_id,
    order_type, status, total_amount, ...
))
order_id = cursor.fetchone()[0]

# Cargar items
for item in toast_items:
    category_id = get_or_create_category(item['category'])
    cursor.execute("""
        INSERT INTO order_items (
            order_id, product_name, category_name,
            quantity, unit_price, ...
        ) VALUES (%s, %s, %s, %s, %s, ...)
    """, (...))
```

### Flujo ETL - DoorDash

1. **Extract:** Lee `doordash_orders.json`
2. **Transform:**
   - Mapea stores a locations
   - Normaliza direcciones de entrega
   - Calcula fees y tips
   - Corrige datos de ubicación (ej: "Jamaica, NY" → "New York, NY")
3. **Load:**
   - `locations` (una location por cada store de DoorDash, con `source_ids={'DOORDASH': 'store-id'}`)
   - `orders` (con `source='DOORDASH'` y `location_id` apuntando a la location de DoorDash)
   - `delivery_orders` (info de entrega)
   - `order_items`
   - `payments`

**Características especiales:**
- Siempre tiene `delivery_orders` entry
- Incluye información de driver

### Flujo ETL - Square POS

1. **Extract:** Lee múltiples archivos Square
   - `catalog.json` - Catálogo de productos
   - `locations.json` - Ubicaciones
   - `orders.json` - Órdenes
   - `payments.json` - Pagos
2. **Transform:**
   - Mapea catalog items a products
   - Normaliza datos de tarjetas
   - Corrige datos de ubicación (ej: "Jamaica, NY" → "New York, NY")
3. **Load:**
   - `products` (desde catalog)
   - `locations` (una location por cada location de Square, con `source_ids={'SQUARE': 'square-id'}`)
   - `orders` (con `source='SQUARE'` y `location_id` apuntando a la location de Square)
   - `order_items`
   - `payments` (con detalles de tarjeta)

### Normalización de Datos

#### Order Type Mapping

| Source | Source Value | Normalized |
|--------|-------------|------------|
| Toast | "DINE_IN" | `dine_in` |
| Toast | "TO_GO" | `takeout` |
| DoorDash | * | `delivery` |
| Square | "EAT_IN" | `dine_in` |
| Square | "TAKEOUT" | `takeout` |

#### Payment Type Mapping

| Source | Source Value | Normalized |
|--------|-------------|------------|
| Toast | "CREDIT_CARD" | `card` |
| Toast | "CASH" | `cash` |
| DoorDash | "card" | `card` |
| Square | "CARD" | `card` |
| Square | "CASH" | `cash` |

### Validación de Datos

Después de cargar datos, ejecutar:

```bash
./install_etl_functions.sh  # Instalar funciones de validación
```

```sql
-- Validar integridad
SELECT * FROM validate_etl_data();
```

Resultados esperados:
```
check_name               | status | details
-------------------------+--------+------------------
Orders without location  | PASS   | Found 0 orders
Orphan order items       | PASS   | Found 0 items
Negative amounts         | PASS   | Found 0 orders
...
```

### Manejo de Errores

**Estrategias:**

1. **Transacciones:** Todo el ETL corre en transacciones
   ```python
   try:
       conn = psycopg2.connect(...)
       cursor = conn.cursor()
       # ... cargar datos ...
       conn.commit()
   except Exception as e:
       conn.rollback()
       raise
   ```

2. **Logging:** Registra errores y warnings
   ```python
   logger.info(f"Loaded {count} orders from Toast")
   logger.warning(f"Skipped {skipped} invalid items")
   ```

3. **Clear flag:** Opción `--clear` para limpiar datos antes de cargar
   ```bash
   python load_all_data.py --clear
   ```

---

## Tipos de Datos (ENUMs)

### OrderSourceEnum

```sql
CREATE TYPE order_source_enum AS ENUM (
    'toast',
    'doordash',
    'square'
);
```

**Uso:** Identifica el sistema de origen de cada orden.

---

### OrderTypeEnum

```sql
CREATE TYPE order_type_enum AS ENUM (
    'dine_in',
    'takeout',
    'delivery',
    'pickup'
);
```

**Uso:** Clasificación normalizada del tipo de servicio.

---

### OrderStatusEnum

```sql
CREATE TYPE order_status_enum AS ENUM (
    'pending',
    'completed',
    'cancelled',
    'refunded'
);
```

**Uso:** Estado del ciclo de vida de la orden.

**Flujo típico:**
```
pending → completed
pending → cancelled
completed → refunded
```

---

### PaymentTypeEnum

```sql
CREATE TYPE payment_type_enum AS ENUM (
    'card',
    'cash',
    'digital_wallet',
    'other'
);
```

**Uso:** Tipo de método de pago.

---

### PaymentStatusEnum

```sql
CREATE TYPE payment_status_enum AS ENUM (
    'pending',
    'completed',
    'failed',
    'refunded'
);
```

**Uso:** Estado del pago.

---

## Ejemplos de Consultas

### Análisis de Ventas

#### 1. Ventas Totales por Día

```sql
SELECT 
    business_date,
    COUNT(*) as order_count,
    SUM(total_amount) as daily_revenue,
    AVG(total_amount) as avg_order_value
FROM orders
WHERE status = 'completed'
GROUP BY business_date
ORDER BY business_date DESC;
```

#### 2. Top 10 Productos Más Vendidos

```sql
SELECT 
    p.name,
    c.name as category,
    SUM(oi.quantity) as total_sold,
    SUM(oi.net_amount) as total_revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.id
LEFT JOIN categories c ON p.category_id = c.id
JOIN orders o ON oi.order_id = o.id
WHERE o.status = 'completed'
GROUP BY p.id, p.name, c.name
ORDER BY total_revenue DESC
LIMIT 10;
```

#### 3. Ventas por Fuente (Source)

```sql
SELECT 
    source,
    COUNT(*) as orders,
    SUM(total_amount) as revenue,
    AVG(total_amount) as avg_ticket,
    SUM(total_amount) / (SELECT SUM(total_amount) FROM orders) * 100 as revenue_pct
FROM orders
WHERE status = 'completed'
GROUP BY source
ORDER BY revenue DESC;
```

#### 4. Análisis por Tipo de Orden

```sql
SELECT 
    order_type,
    COUNT(*) as order_count,
    SUM(total_amount) as revenue,
    AVG(total_amount) as avg_order,
    AVG(EXTRACT(EPOCH FROM (closed_at - opened_at))/60) as avg_duration_minutes
FROM orders
WHERE status = 'completed'
  AND opened_at IS NOT NULL
  AND closed_at IS NOT NULL
GROUP BY order_type
ORDER BY revenue DESC;
```

### Análisis de Productos

#### 5. Productos Sin Ventas

```sql
SELECT 
    p.id,
    p.name,
    c.name as category,
    p.base_price,
    p.created_at
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
WHERE p.is_active = true
  AND NOT EXISTS (
      SELECT 1 FROM order_items oi 
      WHERE oi.product_id = p.id
  )
ORDER BY p.created_at DESC;
```

#### 6. Análisis de Categorías

```sql
SELECT 
    c.name as category,
    COUNT(DISTINCT p.id) as product_count,
    COUNT(oi.id) as items_sold,
    SUM(oi.net_amount) as category_revenue
FROM categories c
LEFT JOIN products p ON p.category_id = c.id
LEFT JOIN order_items oi ON oi.product_id = p.id
LEFT JOIN orders o ON oi.order_id = o.id AND o.status = 'completed'
GROUP BY c.id, c.name
ORDER BY category_revenue DESC NULLS LAST;
```

### Análisis de Pagos

#### 7. Distribución de Métodos de Pago

```sql
SELECT 
    payment_type,
    COUNT(*) as payment_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_payment,
    card_brand,
    COUNT(DISTINCT order_id) as unique_orders
FROM payments
WHERE status = 'completed'
GROUP BY payment_type, card_brand
ORDER BY total_amount DESC;
```

#### 8. Análisis de Propinas

```sql
SELECT 
    DATE(o.business_date) as date,
    COUNT(*) as orders_with_tips,
    SUM(o.tip_amount) as total_tips,
    AVG(o.tip_amount) as avg_tip,
    AVG(o.tip_amount / NULLIF(o.subtotal_amount, 0) * 100) as avg_tip_pct
FROM orders o
WHERE o.status = 'completed'
  AND o.tip_amount > 0
GROUP BY DATE(o.business_date)
ORDER BY date DESC;
```

### Análisis de Ubicaciones

#### 9. Performance por Ubicación

```sql
SELECT 
    l.name as location,
    l.city,
    l.state,
    COUNT(o.id) as order_count,
    SUM(o.total_amount) as revenue,
    AVG(o.total_amount) as avg_order_value,
    SUM(o.tip_amount) as total_tips
FROM locations l
LEFT JOIN orders o ON o.location_id = l.id AND o.status = 'completed'
WHERE l.is_active = true
GROUP BY l.id, l.name, l.city, l.state
ORDER BY revenue DESC NULLS LAST;
```

### Análisis Temporal

#### 10. Ventas por Hora del Día

```sql
SELECT 
    EXTRACT(HOUR FROM opened_at) as hour,
    COUNT(*) as order_count,
    SUM(total_amount) as hourly_revenue,
    AVG(total_amount) as avg_order
FROM orders
WHERE status = 'completed'
  AND opened_at IS NOT NULL
GROUP BY EXTRACT(HOUR FROM opened_at)
ORDER BY hour;
```

#### 11. Comparación Mes a Mes

```sql
SELECT 
    TO_CHAR(business_date, 'YYYY-MM') as month,
    COUNT(*) as orders,
    SUM(total_amount) as revenue,
    COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY TO_CHAR(business_date, 'YYYY-MM')) as order_growth,
    SUM(total_amount) - LAG(SUM(total_amount)) OVER (ORDER BY TO_CHAR(business_date, 'YYYY-MM')) as revenue_growth
FROM orders
WHERE status = 'completed'
GROUP BY TO_CHAR(business_date, 'YYYY-MM')
ORDER BY month DESC;
```

### Búsquedas Avanzadas

#### 12. Búsqueda Fuzzy de Productos (Trigram)

```sql
-- Encuentra productos incluso con typos
SELECT 
    name,
    base_price,
    similarity(name, 'burguer') as similarity_score
FROM products
WHERE name % 'burguer'  -- Operador de similitud
ORDER BY similarity_score DESC
LIMIT 10;
```

#### 13. Búsqueda en Metadata JSONB

```sql
-- Encuentra órdenes con requests especiales
SELECT 
    o.id,
    o.order_number,
    oi.product_name,
    oi.source_metadata->>'special_request' as request
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
WHERE oi.source_metadata @> '{"has_special_request": true}'
ORDER BY o.created_at DESC;
```

---

## Mantenimiento y Monitoreo

### Estadísticas de Tablas

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Índices No Utilizados

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Vacuum y Analyze

```bash
# Análisis de estadísticas
ANALYZE VERBOSE;

# Vacuum completo
VACUUM ANALYZE;
```

---

## Recursos Adicionales

- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - Guía de instalación y setup
- [ALEMBIC_GUIDE.md](./ALEMBIC_GUIDE.md) - Guía de migraciones con Alembic
- [scripts/README.md](./scripts/README.md) - Documentación de scripts ETL
- [sql/README.md](./sql/README.md) - Funciones SQL auxiliares
- [README.md](./README.md) - Documentación general del proyecto

---

## Glosario

- **POS** - Point of Sale (Sistema de punto de venta)
- **ETL** - Extract, Transform, Load (Extraer, Transformar, Cargar)
- **JSONB** - JSON Binary (formato binario de JSON en PostgreSQL)
- **Trigram** - Técnica de búsqueda de texto por similitud
- **GIN** - Generalized Inverted Index (índice invertido generalizado)
- **FK** - Foreign Key (Clave foránea)
- **PK** - Primary Key (Clave primaria)
- **ORM** - Object-Relational Mapping (Mapeo objeto-relacional)

---

**Última actualización:** 2025-12-31  
**Versión del esquema:** `8acb2927bf44` (Alembic)

