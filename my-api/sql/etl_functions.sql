-- PostgreSQL Helper Functions for ETL
-- These functions are used by ETL scripts to load data from JSON sources
-- Run this file once after applying Alembic migrations

-- ============================================================================
-- Helper Function: Get Location ID by Source ID
-- ============================================================================

CREATE OR REPLACE FUNCTION get_location_id_by_source(
    p_source VARCHAR,
    p_source_id VARCHAR
)
RETURNS INTEGER AS $$
DECLARE
    v_location_id INTEGER;
BEGIN
    -- Normalize source name to lowercase
    p_source := LOWER(p_source);
    
    SELECT id INTO v_location_id
    FROM locations
    WHERE source_ids->>p_source = p_source_id;
    
    RETURN v_location_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_location_id_by_source IS 'Lookup location by source-specific ID';

-- Example usage:
-- SELECT get_location_id_by_source('toast', 'loc_downtown_001');
-- SELECT get_location_id_by_source('doordash', 'str_downtown_001');
-- SELECT get_location_id_by_source('square', 'LCN001DOWNTOWN');

-- ============================================================================
-- Helper Function: Get or Create Category
-- ============================================================================

CREATE OR REPLACE FUNCTION get_or_create_category(
    p_category_name VARCHAR
)
RETURNS INTEGER AS $$
DECLARE
    v_category_id INTEGER;
    v_normalized_name VARCHAR;
BEGIN
    -- Normalize the category name (lowercase, no emojis)
    -- Remove emojis and special chars, then normalize spaces and trim (important: trim after removing emojis)
    v_normalized_name := REGEXP_REPLACE(p_category_name, '[^\w\s&-]', '', 'g');
    v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\s+', ' ', 'g');
    v_normalized_name := TRIM(v_normalized_name);
    
    -- Fix typos FIRST
    v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\bappitizers\b', 'Appetizers', 'gi');
    v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\bappitizer\b', 'Appetizer', 'gi');
    
    -- Convert to lowercase for comparison
    v_normalized_name := LOWER(v_normalized_name);
    
    -- Normalize synonyms - handle compound names first
    IF v_normalized_name ~* '\bsides\s*[&and]+\s*appetizers\b' OR 
       v_normalized_name ~* '\bappetizers\s*[&and]+\s*sides\b' THEN
        v_normalized_name := 'appetizers';
    ELSIF v_normalized_name ~* '^beer\s*[&and]+\s*wine$' THEN
        v_normalized_name := 'beverages';
    ELSIF v_normalized_name IN ('drinks', 'beverages') THEN
        v_normalized_name := 'beverages';
    ELSIF v_normalized_name IN ('sides', 'appetizers') THEN
        v_normalized_name := 'appetizers';
    ELSE
        -- Word boundary replacements
        v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\bdrinks\b', 'beverages', 'gi');
        v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\bsides\b', 'appetizers', 'gi');
        v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\bbeer\s*&\s*wine\b', 'beverages', 'gi');
    END IF;
    
    -- Clean up duplicates
    v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\bappetizers\s+appetizers\b', 'appetizers', 'gi');
    v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\bbeverages\s+beverages\b', 'beverages', 'gi');
    v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\bappetizers\s*[&and]+\s*appetizers\b', 'appetizers', 'gi');
    v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\bbeverages\s*[&and]+\s*beverages\b', 'beverages', 'gi');
    
    -- Final cleanup
    v_normalized_name := REGEXP_REPLACE(v_normalized_name, '\s+', ' ', 'g');
    v_normalized_name := TRIM(v_normalized_name);
    
    -- Try to find existing category
    -- Search by normalized_name, or by source_names, or by known variants (including typos)
    SELECT id INTO v_category_id
    FROM categories
    WHERE normalized_name = v_normalized_name
       OR source_names @> to_jsonb(p_category_name)
       -- Handle typo: "appitizers" should match "appetizers"
       OR (v_normalized_name = 'appetizers' AND normalized_name = 'appitizers')
       OR (v_normalized_name = 'appitizers' AND normalized_name = 'appetizers');
    
    -- If not found, create new category
    IF v_category_id IS NULL THEN
        INSERT INTO categories (name, normalized_name, source_names)
        VALUES (
            INITCAP(v_normalized_name),
            v_normalized_name,
            jsonb_build_array(p_category_name)
        )
        RETURNING id INTO v_category_id;
    ELSE
        -- Update source_names to include this variant if not already present
        UPDATE categories
        SET source_names = source_names || to_jsonb(p_category_name)
        WHERE id = v_category_id
          AND NOT (source_names @> to_jsonb(p_category_name));
    END IF;
    
    RETURN v_category_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_or_create_category IS 'Get existing or create new category with name normalization';

-- ============================================================================
-- Validation Function
-- ============================================================================

-- Function to check data integrity after ETL load
CREATE OR REPLACE FUNCTION validate_etl_data()
RETURNS TABLE(
    check_name TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- Check locations
    RETURN QUERY
    SELECT 
        'Locations'::TEXT,
        CASE WHEN COUNT(*) > 0 THEN 'OK' ELSE 'EMPTY' END::TEXT,
        'Found ' || COUNT(*)::TEXT || ' locations'::TEXT
    FROM locations;
    
    -- Check categories
    RETURN QUERY
    SELECT 
        'Categories'::TEXT,
        CASE WHEN COUNT(*) > 0 THEN 'OK' ELSE 'EMPTY' END::TEXT,
        'Found ' || COUNT(*)::TEXT || ' categories'::TEXT
    FROM categories;
    
    -- Check products
    RETURN QUERY
    SELECT 
        'Products'::TEXT,
        CASE WHEN COUNT(*) > 0 THEN 'OK' ELSE 'EMPTY' END::TEXT,
        'Found ' || COUNT(*)::TEXT || ' products'::TEXT
    FROM products;
    
    -- Check orders
    RETURN QUERY
    SELECT 
        'Orders'::TEXT,
        CASE WHEN COUNT(*) > 0 THEN 'OK' ELSE 'EMPTY' END::TEXT,
        'Found ' || COUNT(*)::TEXT || ' orders'::TEXT
    FROM orders;
    
    -- Check orphaned order items
    RETURN QUERY
    SELECT 
        'Order Items Integrity'::TEXT,
        CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'ERROR' END::TEXT,
        'Found ' || COUNT(*)::TEXT || ' orphaned order items'::TEXT
    FROM order_items oi
    WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.id = oi.order_id);
    
    -- Check orphaned payments
    RETURN QUERY
    SELECT 
        'Payments Integrity'::TEXT,
        CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'ERROR' END::TEXT,
        'Found ' || COUNT(*)::TEXT || ' orphaned payments'::TEXT
    FROM payments p
    WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.id = p.order_id);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validate_etl_data IS 'Validates data integrity after ETL load';

-- Usage: SELECT * FROM validate_etl_data();

