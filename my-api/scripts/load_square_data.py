"""
ETL Script for Square POS Data
Loads data from Square JSON files (catalog, locations, orders, payments) into PostgreSQL
"""

import json
import sys
import re
from pathlib import Path
from etl_utils import (DatabaseConnection, DataNormalizer, ETLDatabase, 
                       print_summary)
import psycopg2.extras


def normalize_category_name(category_name: str) -> str:
    """
    Normalize category name to unify synonyms and fix typos
    
    Rules:
    - "Drinks" → "Beverages"
    - "Sides" → "Appetizers"
    - "Beer & Wine" → "Beverages"
    - "Appitizers" (typo) → "Appetizers"
    - "Sides & Appetizers" → "Appetizers"
    """
    if not category_name:
        return ""
    
    # Remove emojis and special characters
    normalized = re.sub(r'[^\w\s&-]', '', category_name)
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip()
    
    # Fix typos FIRST
    normalized = re.sub(r'\bappitizers\b', 'Appetizers', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\bappitizer\b', 'Appetizer', normalized, flags=re.IGNORECASE)
    
    # Normalize synonyms - handle compound names first
    normalized_lower = normalized.lower().strip()
    
    # Handle compound names (e.g., "Sides & Appetizers")
    if re.search(r'\bsides\s*[&and]+\s*appetizers\b', normalized_lower) or \
       re.search(r'\bappetizers\s*[&and]+\s*sides\b', normalized_lower):
        normalized = 'Appetizers'
    elif re.match(r'^beer\s*[&and]+\s*wine$', normalized_lower):
        normalized = 'Beverages'
    elif normalized_lower in ['drinks', 'beverages']:
        normalized = 'Beverages'
    elif normalized_lower in ['sides', 'appetizers']:
        normalized = 'Appetizers'
    else:
        # Word boundary replacements
        normalized = re.sub(r'\bdrinks\b', 'Beverages', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bsides\b', 'Appetizers', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bbeer\s*&\s*wine\b', 'Beverages', normalized, flags=re.IGNORECASE)
    
    # Clean up duplicates (e.g., "Appetizers Appetizers" → "Appetizers")
    normalized = re.sub(r'\bappetizers\s+appetizers\b', 'Appetizers', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\bbeverages\s+beverages\b', 'Beverages', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\bappetizers\s*[&and]+\s*appetizers\b', 'Appetizers', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\bbeverages\s*[&and]+\s*beverages\b', 'Beverages', normalized, flags=re.IGNORECASE)
    
    # Final cleanup
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    normalized = normalized.title()
    
    return normalized


# Import normalize_product_base_name from etl_utils
from etl_utils import DataNormalizer
normalize_product_base_name = DataNormalizer.normalize_product_base_name


def load_square_data(data_dir: Path, clear_existing: bool = False):
    """Load Square POS data into database"""
    
    print("\n" + "="*60)
    print("  SQUARE POS DATA LOADER")
    print("="*60 + "\n")
    
    # Initialize
    db_conn = DatabaseConnection()
    db_conn.connect()
    normalizer = DataNormalizer()
    etl_db = ETLDatabase(db_conn)
    
    stats = {
        'locations': 0,
        'catalog_items': 0,
        'orders': 0,
        'order_items': 0,
        'payments': 0,
        'errors': 0
    }
    
    try:
        # Clear existing data if requested
        if clear_existing:
            etl_db.clear_all_data()
        
        # =====================================================================
        # 1. Load Catalog (items, categories, variations)
        # =====================================================================
        print("Loading catalog...")
        catalog_path = data_dir / 'catalog.json'
        with open(catalog_path, 'r') as f:
            catalog_data = json.load(f)
        
        # Build catalog lookup
        catalog_items = {}
        catalog_categories = {}
        catalog_variations = {}
        
        for obj in catalog_data.get('objects', []):
            obj_type = obj.get('type')
            obj_id = obj.get('id')
            
            if obj_type == 'CATEGORY':
                catalog_categories[obj_id] = obj.get('category_data', {}).get('name')
            
            elif obj_type == 'ITEM':
                item_data = obj.get('item_data', {})
                catalog_items[obj_id] = {
                    'name': item_data.get('name'),
                    'category_id': item_data.get('category_id'),
                    'variations': item_data.get('variations', [])
                }
                
                # Extract variations from within items
                for variation in item_data.get('variations', []):
                    var_id = variation.get('id')
                    var_data = variation.get('item_variation_data', {})
                    if var_id:
                        catalog_variations[var_id] = {
                            'name': var_data.get('name'),
                            'item_id': var_data.get('item_id') or obj_id,  # Fallback to parent item id
                            'price': var_data.get('price_money', {}).get('amount', 0)
                        }
            
            elif obj_type == 'ITEM_VARIATION':
                # Handle standalone variations (if any)
                variation_data = obj.get('item_variation_data', {})
                catalog_variations[obj_id] = {
                    'name': variation_data.get('name'),
                    'item_id': variation_data.get('item_id'),
                    'price': variation_data.get('price_money', {}).get('amount', 0)
                }
        
        stats['catalog_items'] = len(catalog_items)
        print(f"✓ Loaded catalog: {len(catalog_items)} items, {len(catalog_categories)} categories\n")
        
        # =====================================================================
        # 2. Load Locations
        # =====================================================================
        print("Loading locations...")
        locations_path = data_dir / 'locations.json'
        with open(locations_path, 'r') as f:
            locations_data = json.load(f)
        
        location_map = {}
        for loc in locations_data.get('locations', []):
            address = loc.get('address', {})
            
            # Apply data correction before creating location
            city = address.get('locality')
            state = address.get('administrative_district_level_1')
            corrected_city = normalizer.correct_location_data(city, state)
            
            location_id = etl_db.get_or_create_location(
                name=loc.get('name'),
                address={
                    'line1': address.get('address_line_1'),
                    'city': corrected_city,  # Use corrected city
                    'state': state,
                    'zip_code': address.get('postal_code'),
                    'country': address.get('country', 'US')
                },
                timezone=loc.get('timezone', 'America/New_York'),
                source=normalizer.normalize_source('square'),
                source_id=loc['id']
            )
            location_map[loc['id']] = location_id
            stats['locations'] += 1
        
        db_conn.commit()
        print(f"✓ Processed {stats['locations']} locations\n")
        
        # =====================================================================
        # 3. Load Orders
        # =====================================================================
        print("Loading orders...")
        orders_path = data_dir / 'orders.json'
        with open(orders_path, 'r') as f:
            orders_data = json.load(f)
        
        order_map = {}
        for order_data in orders_data.get('orders', []):
            try:
                location_id = location_map.get(order_data.get('location_id'))
                
                if not location_id:
                    print(f"  ⚠️  Unknown location: {order_data.get('location_id')}")
                    stats['errors'] += 1
                    continue
                
                # Map order type
                fulfillment = order_data.get('fulfillments', [{}])[0]
                fulfillment_type = fulfillment.get('type', 'PICKUP')
                order_type = normalizer.map_order_type(fulfillment_type, 'square')
                
                # Parse timestamps
                created_at = normalizer.parse_timestamp(order_data.get('created_at'))
                updated_at = normalizer.parse_timestamp(order_data.get('updated_at'))
                closed_at = normalizer.parse_timestamp(order_data.get('closed_at'))
                
                # Calculate totals
                # Note: total_money in Square includes tax, tip, discounts, service charges
                # Subtotal should be calculated from line items, not from total_money
                total_money_obj = order_data.get('total_money', {})
                total_tax = order_data.get('total_tax_money', {})
                total_tip = order_data.get('total_tip_money', {})
                total_discount = order_data.get('total_discount_money', {})
                total_service_charge = order_data.get('total_service_charge_money', {})
                
                # Calculate subtotal by summing gross_sales_money from line_items
                subtotal = 0
                for line_item in order_data.get('line_items', []):
                    gross_sales = line_item.get('gross_sales_money', {})
                    subtotal += gross_sales.get('amount', 0)
                
                tax_amount = total_tax.get('amount', 0)
                tip_amount = total_tip.get('amount', 0)
                discount_amount = total_discount.get('amount', 0)
                service_fee = total_service_charge.get('amount', 0)
                total_amount = total_money_obj.get('amount', 0)  # Total final
                
                # Customer info
                customer_id = order_data.get('customer_id')
                
                # Insert order
                db_conn.cur.execute("""
                    INSERT INTO orders (
                        source, source_order_id, location_id, order_type, status,
                        created_at, closed_at, business_date,
                        subtotal, tax_amount, tip_amount, total_amount,
                        discount_amount, service_fee,
                        source_metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s::date,
                        %s, %s, %s, %s,
                        %s, %s, %s
                    ) RETURNING id
                """, (
                    normalizer.normalize_source('square'),
                    order_data['id'],
                    location_id,
                    order_type,
                    normalizer.normalize_order_status('completed'),
                    created_at,
                    closed_at or updated_at,
                    str(created_at.date()) if created_at else None,
                    normalizer.cents_to_dollars(subtotal),
                    normalizer.cents_to_dollars(tax_amount),
                    normalizer.cents_to_dollars(tip_amount),
                    normalizer.cents_to_dollars(total_amount),
                    normalizer.cents_to_dollars(discount_amount),
                    normalizer.cents_to_dollars(service_fee),
                    psycopg2.extras.Json({
                        'customer_id': customer_id,
                        'state': order_data.get('state'),
                        'version': order_data.get('version'),
                        'fulfillment': fulfillment
                    })
                ))
                
                order_id = db_conn.cur.fetchone()['id']
                order_map[order_data['id']] = order_id
                stats['orders'] += 1
                
                # Process line items
                for idx, line_item in enumerate(order_data.get('line_items', [])):
                    # Get catalog info
                    catalog_object_id = line_item.get('catalog_object_id')
                    variation = catalog_variations.get(catalog_object_id, {})
                    item_id = variation.get('item_id')
                    item = catalog_items.get(item_id, {})
                    
                    # Get category and normalize it
                    category_id = item.get('category_id')
                    raw_category_name = catalog_categories.get(category_id, 'Unknown')
                    category_name = normalize_category_name(raw_category_name)
                    
                    # Get item name - prioritize catalog name over line_item name
                    item_name = item.get('name') or line_item.get('name') or 'Unknown Item'
                    variation_name = variation.get('name') or line_item.get('variation_name')
                    
                    # Combine name with variation (only if variation name is meaningful)
                    if variation_name and variation_name not in ['Regular', 'reg', '']:
                        full_name = f"{item_name} - {variation_name}"
                    else:
                        full_name = item_name
                    
                    # Normalize product base name to unify variations
                    normalized_product_name = normalizer.normalize_product_base_name(full_name)
                    
                    # Calculate prices first
                    quantity = int(line_item.get('quantity', '1'))
                    total_money = line_item.get('total_money', {}).get('amount', 0)
                    total_tax = line_item.get('total_tax_money', {}).get('amount', 0)
                    
                    # Calculate unit price (total_money / quantity)
                    unit_price = total_money / quantity if quantity > 0 else total_money
                    
                    # Get or create product using normalized name
                    product_id = etl_db.get_or_create_product(
                        name=normalized_product_name,
                        category_name=category_name,
                        price=normalizer.cents_to_dollars(unit_price),
                        source=normalizer.normalize_source('square'),
                        source_product_id=catalog_object_id or f"sq_{order_id}_{idx}"
                    )
                    
                    # Insert order item
                    db_conn.cur.execute("""
                        INSERT INTO order_items (
                            order_id, product_id, item_name, sequence_number,
                            quantity, unit_price, total_price, tax_amount,
                            category_name, source_item_id, source_metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        order_id,
                        product_id,
                        full_name,
                        idx,
                        quantity,
                        normalizer.cents_to_dollars(unit_price),
                        normalizer.cents_to_dollars(total_money),
                        normalizer.cents_to_dollars(total_tax),
                        category_name,
                        line_item.get('uid'),
                        psycopg2.extras.Json({
                            'catalog_object_id': catalog_object_id,
                            'catalog_version': line_item.get('catalog_version'),
                            'variation_name': variation_name,
                            'note': line_item.get('note')
                        })
                    ))
                    
                    order_item_id = db_conn.cur.fetchone()['id']
                    stats['order_items'] += 1
                    
                    # Process modifiers
                    for modifier in line_item.get('modifiers', []):
                        db_conn.cur.execute("""
                            INSERT INTO order_item_modifiers (
                                order_item_id, modifier_name, modifier_value,
                                price_adjustment, quantity
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (
                            order_item_id,
                            modifier.get('name'),
                            modifier.get('name'),
                            normalizer.cents_to_dollars(
                                modifier.get('total_price_money', {}).get('amount', 0)
                            ),
                            int(modifier.get('quantity', '1'))
                        ))
                
                if stats['orders'] % 5 == 0:
                    print(f"  Processed {stats['orders']} orders...")
                    
            except Exception as e:
                print(f"  ✗ Error processing order {order_data.get('id')}: {e}")
                stats['errors'] += 1
                db_conn.rollback()
                continue
        
        db_conn.commit()
        print(f"✓ Processed {stats['orders']} orders with {stats['order_items']} items\n")
        
        # =====================================================================
        # 4. Load Payments
        # =====================================================================
        print("Loading payments...")
        payments_path = data_dir / 'payments.json'
        with open(payments_path, 'r') as f:
            payments_data = json.load(f)
        
        for payment_data in payments_data.get('payments', []):
            try:
                square_order_id = payment_data.get('order_id')
                order_id = order_map.get(square_order_id)
                
                if not order_id:
                    print(f"  ⚠️  Unknown order for payment: {square_order_id}")
                    stats['errors'] += 1
                    continue
                
                # Get payment details
                card_details = payment_data.get('card_details', {})
                card = card_details.get('card', {})
                
                # Use source_type directly from Square (CARD, CASH, WALLET)
                source_type = payment_data.get('source_type', 'CARD')
                payment_type = normalizer.map_payment_type(source_type)
                
                # Get amounts
                amount = payment_data.get('amount_money', {}).get('amount', 0)
                tip_amount = payment_data.get('tip_money', {}).get('amount', 0)
                processing_fee = payment_data.get('processing_fee', [{}])[0].get('amount_money', {}).get('amount', 0)
                
                # Parse timestamps
                created_at = normalizer.parse_timestamp(payment_data.get('created_at'))
                updated_at = normalizer.parse_timestamp(payment_data.get('updated_at'))
                
                # Insert payment
                db_conn.cur.execute("""
                    INSERT INTO payments (
                        order_id, source, source_payment_id,
                        payment_type, status, amount, tip_amount,
                        processing_fee, processed_at,
                        card_brand, card_last4, card_entry_method,
                        source_metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    order_id,
                    normalizer.normalize_source('square'),
                    payment_data['id'],
                    payment_type,
                    normalizer.normalize_order_status(payment_data.get('status', 'COMPLETED')),
                    normalizer.cents_to_dollars(amount),
                    normalizer.cents_to_dollars(tip_amount),
                    normalizer.cents_to_dollars(processing_fee),
                    created_at,
                    card.get('card_brand'),
                    card.get('last_4'),
                    card_details.get('entry_method'),
                    psycopg2.extras.Json({
                        'receipt_number': payment_data.get('receipt_number'),
                        'receipt_url': payment_data.get('receipt_url'),
                        'statement_description': card_details.get('statement_description')
                    })
                ))
                stats['payments'] += 1
                
            except Exception as e:
                print(f"  ✗ Error processing payment {payment_data.get('id')}: {e}")
                stats['errors'] += 1
                continue
        
        db_conn.commit()
        print(f"✓ Processed {stats['payments']} payments\n")
        
        # Print summary
        print_summary("SQUARE POS LOAD COMPLETE", stats)
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        db_conn.rollback()
        raise
    finally:
        db_conn.close()


if __name__ == "__main__":
    # Path to Square data directory
    data_dir = Path(__file__).parent.parent.parent / 'data' / 'sources' / 'square'
    
    # Check if directory exists
    if not data_dir.exists():
        print(f"✗ Error: Directory not found: {data_dir}")
        sys.exit(1)
    
    # Check required files
    required_files = ['catalog.json', 'locations.json', 'orders.json', 'payments.json']
    for filename in required_files:
        if not (data_dir / filename).exists():
            print(f"✗ Error: Missing required file: {filename}")
            sys.exit(1)
    
    # Load data
    clear_existing = '--clear' in sys.argv
    load_square_data(data_dir, clear_existing=clear_existing)

