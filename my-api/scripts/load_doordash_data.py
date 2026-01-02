"""
ETL Script for DoorDash Orders
Loads data from doordash_orders.json into PostgreSQL
"""

import json
import sys
from pathlib import Path
from etl_utils import (DatabaseConnection, DataNormalizer, ETLDatabase, 
                       print_summary)
import psycopg2.extras


def load_doordash_data(json_path: str, clear_existing: bool = False):
    """Load DoorDash data into database"""
    
    print("\n" + "="*60)
    print("  DOORDASH DATA LOADER")
    print("="*60 + "\n")
    
    # Initialize
    db_conn = DatabaseConnection()
    db_conn.connect()
    normalizer = DataNormalizer()
    etl_db = ETLDatabase(db_conn)
    
    stats = {
        'stores': 0,
        'orders': 0,
        'order_items': 0,
        'payments': 0,
        'delivery_orders': 0,
        'errors': 0
    }
    
    try:
        # Clear existing data if requested
        if clear_existing:
            etl_db.clear_all_data()
        
        # Load JSON
        print(f"Loading JSON from: {json_path}")
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        print(f"✓ Loaded DoorDash export\n")
        
        # Process stores (locations)
        print("Processing stores...")
        store_map = {}
        for store in data.get('stores', []):
            # Apply data correction before creating location
            city = store['address'].get('city')
            state = store['address'].get('state')
            corrected_city = normalizer.correct_location_data(city, state)
            
            location_id = etl_db.get_or_create_location(
                name=store['name'],
                address={
                    'street': store['address'].get('street'),
                    'city': corrected_city,  # Use corrected city
                    'state': state,
                    'zip_code': store['address'].get('zip_code'),
                    'country': store['address'].get('country', 'US')
                },
                timezone=store.get('timezone', 'America/New_York'),
                source='DOORDASH',
                source_id=store['store_id']
            )
            store_map[store['store_id']] = location_id
            stats['stores'] += 1
        
        db_conn.commit()
        print(f"✓ Processed {stats['stores']} stores\n")
        
        # Process orders
        print("Processing orders...")
        for order_data in data.get('orders', []):
            try:
                store_id = order_data.get('store_id')
                location_id = store_map.get(store_id)
                
                if not location_id:
                    print(f"  ⚠️  Unknown store: {store_id}")
                    stats['errors'] += 1
                    continue
                
                # Map order type
                fulfillment = order_data.get('order_fulfillment_method', 'MERCHANT_DELIVERY')
                if fulfillment == 'PICKUP':
                    order_type = normalizer.map_order_type('PICKUP', 'doordash')
                else:
                    order_type = normalizer.map_order_type('DELIVERY', 'doordash')
                
                # Parse timestamps
                created_at = normalizer.parse_timestamp(order_data.get('created_at'))
                pickup_time = normalizer.parse_timestamp(order_data.get('pickup_time'))
                delivery_time = normalizer.parse_timestamp(order_data.get('delivery_time'))
                
                # Calculate totals
                order_subtotal = order_data.get('order_subtotal', 0)
                tax_amount = order_data.get('tax_amount', 0)
                dasher_tip = order_data.get('dasher_tip', 0)
                delivery_fee = order_data.get('delivery_fee', 0)
                service_fee = order_data.get('service_fee', 0)
                commission = order_data.get('commission', 0)
                total_charged = order_data.get('total_charged_to_consumer', 0)
                
                # Customer info
                customer = order_data.get('customer', {})
                customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
                customer_phone = customer.get('phone_number')
                
                # Insert order
                db_conn.cur.execute("""
                    INSERT INTO orders (
                        source, source_order_id, location_id, order_type, status,
                        created_at, closed_at, business_date,
                        subtotal, tax_amount, tip_amount, total_amount,
                        discount_amount, delivery_fee, service_fee, commission_fee,
                        customer_name, customer_phone, contains_alcohol, is_catering,
                        source_metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s::date,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    ) RETURNING id
                """, (
                    normalizer.normalize_source('doordash'),
                    order_data['external_delivery_id'],
                    location_id,
                    order_type,
                    normalizer.normalize_order_status('completed'),
                    created_at,
                    delivery_time or pickup_time,
                    str(created_at.date()) if created_at else None,
                    normalizer.cents_to_dollars(order_subtotal),
                    normalizer.cents_to_dollars(tax_amount),
                    normalizer.cents_to_dollars(dasher_tip),
                    normalizer.cents_to_dollars(total_charged),
                    0,  # discount_amount
                    normalizer.cents_to_dollars(delivery_fee),
                    normalizer.cents_to_dollars(service_fee),
                    normalizer.cents_to_dollars(commission),
                    customer_name or None,
                    customer_phone,  # NULL if not present
                    order_data.get('contains_alcohol'),  # NULL if not present
                    order_data.get('is_catering'),      # NULL if not present
                    psycopg2.extras.Json({
                        'order_status': order_data.get('order_status'),
                        'fulfillment_method': fulfillment,
                        'merchant_payout': order_data.get('merchant_payout')
                    })
                ))
                
                order_id = db_conn.cur.fetchone()['id']
                stats['orders'] += 1
                
                # Insert delivery_order if delivery
                if order_type == 'DELIVERY':
                    dropoff = order_data.get('dropoff_address', {})
                    
                    db_conn.cur.execute("""
                        INSERT INTO delivery_orders (
                            order_id,
                            pickup_time, delivery_time,
                            delivery_address_line1, delivery_city,
                            delivery_state, delivery_zip_code
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        order_id,
                        pickup_time,
                        delivery_time,
                        dropoff.get('street'),
                        dropoff.get('city'),
                        dropoff.get('state'),
                        dropoff.get('zip_code')
                    ))
                    stats['delivery_orders'] += 1
                
                # Process order items
                for idx, item in enumerate(order_data.get('order_items', [])):
                    # Get or create product
                    product_id = etl_db.get_or_create_product(
                        name=item.get('name'),
                        category_name=item.get('category', 'Unknown'),
                        price=normalizer.cents_to_dollars(item.get('unit_price', 0)),
                        source='DOORDASH',
                        source_product_id=item.get('item_id', f"dd_{order_id}_{idx}")
                    )
                    
                    # Insert order item
                    db_conn.cur.execute("""
                        INSERT INTO order_items (
                            order_id, product_id, item_name, sequence_number,
                            quantity, unit_price, total_price,
                            category_name, source_item_id,
                            special_instructions, source_metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        order_id,
                        product_id,
                        item.get('name'),
                        idx,
                        item.get('quantity', 1),
                        normalizer.cents_to_dollars(item.get('unit_price', 0)),
                        normalizer.cents_to_dollars(item.get('total_price', 0)),
                        item.get('category'),
                        item.get('item_id'),
                        item.get('special_instructions'),
                        psycopg2.extras.Json({'options': item.get('options', [])})
                    ))
                    
                    order_item_id = db_conn.cur.fetchone()['id']
                    stats['order_items'] += 1
                    
                    # Process options as modifiers
                    for option in item.get('options', []):
                        db_conn.cur.execute("""
                            INSERT INTO order_item_modifiers (
                                order_item_id, modifier_name, modifier_value,
                                price_adjustment, quantity
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (
                            order_item_id,
                            option.get('name'),
                            option.get('name'),
                            normalizer.cents_to_dollars(option.get('price', 0)),
                            1
                        ))
                
                # Create payment record (DoorDash payments are implicit)
                # Payment method not provided in JSON, using UNKNOWN
                # Note: processing_fee is NULL because DoorDash doesn't have payment processor fees
                # (commission is stored in orders.commission_fee, not here)
                db_conn.cur.execute("""
                    INSERT INTO payments (
                        order_id, source, source_payment_id,
                        payment_type, status, amount, tip_amount,
                        processing_fee, processed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    order_id,
                    normalizer.normalize_source('doordash'),
                    f"dd_pay_{order_data['external_delivery_id']}",
                    normalizer.map_payment_type('UNKNOWN'),
                    normalizer.normalize_order_status('completed'),
                    normalizer.cents_to_dollars(total_charged),
                    normalizer.cents_to_dollars(dasher_tip),
                    None,  # processing_fee is NULL - DoorDash doesn't have payment processor fees
                    delivery_time or pickup_time or created_at
                ))
                stats['payments'] += 1
                
                if stats['orders'] % 5 == 0:
                    print(f"  Processed {stats['orders']} orders...")
                    
            except Exception as e:
                print(f"  ✗ Error processing order {order_data.get('external_delivery_id')}: {e}")
                stats['errors'] += 1
                db_conn.rollback()
                continue
        
        # Commit all changes
        db_conn.commit()
        
        # Print summary
        print_summary("DOORDASH LOAD COMPLETE", stats)
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        db_conn.rollback()
        raise
    finally:
        db_conn.close()


if __name__ == "__main__":
    # Path to JSON file
    json_path = Path(__file__).parent.parent.parent / 'data' / 'sources' / 'doordash_orders.json'
    
    # Check if file exists
    if not json_path.exists():
        print(f"✗ Error: File not found: {json_path}")
        sys.exit(1)
    
    # Load data
    clear_existing = '--clear' in sys.argv
    load_doordash_data(str(json_path), clear_existing=clear_existing)

