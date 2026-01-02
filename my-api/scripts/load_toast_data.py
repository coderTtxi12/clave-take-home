"""
ETL Script for Toast POS Data
Loads data from toast_pos_export.json into PostgreSQL
"""

import json
import sys
from pathlib import Path
from etl_utils import (DatabaseConnection, DataNormalizer, ETLDatabase, 
                       print_summary)
import psycopg2.extras  # type: ignore


def load_toast_data(json_path: str, clear_existing: bool = False):
    """Load Toast POS data into database"""
    
    print("\n" + "="*60)
    print("  TOAST POS DATA LOADER")
    print("="*60 + "\n")
    
    # Initialize
    db_conn = DatabaseConnection()
    db_conn.connect()
    normalizer = DataNormalizer()
    etl_db = ETLDatabase(db_conn)
    
    stats = {
        'locations': 0,
        'orders': 0,
        'checks': 0,
        'order_items': 0,
        'modifiers': 0,
        'payments': 0,
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
        
        print(f"✓ Loaded Toast POS export\n")
        
        # Process locations
        print("Processing locations...")
        location_map = {}
        for loc in data.get('locations', []):
            # Apply data correction before creating location
            city = loc['address'].get('city')
            state = loc['address'].get('state')
            corrected_city = normalizer.correct_location_data(city, state)
            
            location_id = etl_db.get_or_create_location(
                name=loc['name'],
                address={
                    'line1': loc['address'].get('line1'),
                    'city': corrected_city,  # Use corrected city
                    'state': state,
                    'zip': loc['address'].get('zip'),
                    'country': loc['address'].get('country', 'US')
                },
                timezone=loc.get('timezone', 'America/New_York'),
                source='TOAST',
                source_id=loc['guid']
            )
            location_map[loc['guid']] = location_id
            stats['locations'] += 1
        
        db_conn.commit()
        print(f"✓ Processed {stats['locations']} locations\n")
        
        # Process orders
        print("Processing orders...")
        for order_data in data.get('orders', []):
            try:
                # Skip voided/deleted orders
                if order_data.get('voided') or order_data.get('deleted'):
                    continue
                
                location_id = location_map.get(order_data['restaurantGuid'])
                if not location_id:
                    print(f"  ⚠️  Unknown location: {order_data['restaurantGuid']}")
                    stats['errors'] += 1
                    continue
                
                # Map order type
                dining_option = order_data.get('diningOption', {})
                behavior = dining_option.get('behavior', 'DINE_IN')
                order_type = normalizer.map_order_type(behavior, 'toast')
                
                # Calculate totals from checks
                total_subtotal = 0
                total_tax = 0
                total_tip = 0
                total_amount = 0
                
                for check in order_data.get('checks', []):
                    if not check.get('voided') and not check.get('deleted'):
                        total_subtotal += check.get('amount', 0)
                        total_tax += check.get('taxAmount', 0)
                        total_tip += check.get('tipAmount', 0)
                        total_amount += check.get('totalAmount', 0)
                
                # Parse timestamps
                created_at = normalizer.parse_timestamp(order_data.get('openedDate'))
                closed_at = normalizer.parse_timestamp(order_data.get('closedDate'))
                business_date = order_data.get('businessDate')
                
                # Get server name
                server = order_data.get('server', {})
                server_name = None
                if server:
                    server_name = f"{server.get('firstName', '')} {server.get('lastName', '')}".strip()
                
                # Insert order
                # type: ignore
                db_conn.cur.execute("""
                    INSERT INTO orders (
                        source, source_order_id, location_id, order_type, status,
                        created_at, closed_at, business_date,
                        subtotal, tax_amount, tip_amount, total_amount,
                        discount_amount,
                        server_name, is_voided, is_deleted, source_metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s,
                        %s, %s, %s, %s
                    ) RETURNING id
                """, (
                    normalizer.normalize_source('toast'),
                    order_data['guid'],
                    location_id,
                    order_type,
                    normalizer.normalize_order_status('completed'),
                    created_at,
                    closed_at,
                    business_date,
                    normalizer.cents_to_dollars(total_subtotal),
                    normalizer.cents_to_dollars(total_tax),
                    normalizer.cents_to_dollars(total_tip),
                    normalizer.cents_to_dollars(total_amount),
                    0,  # discount_amount
                    server_name,
                    order_data.get('voided', False),
                    order_data.get('deleted', False),
                    psycopg2.extras.Json({
                        'revenue_center': order_data.get('revenueCenter'),
                        'dining_option': dining_option,
                        'external_id': order_data.get('externalId')
                    })
                ))
                
                order_id = db_conn.cur.fetchone()['id']  # type: ignore
                stats['orders'] += 1
                
                # Process checks
                for check in order_data.get('checks', []):
                    if check.get('voided') or check.get('deleted'):
                        continue
                    
                    stats['checks'] += 1
                    
                    # Insert toast_check
                    # type: ignore
                    db_conn.cur.execute("""
                        INSERT INTO toast_checks (
                            order_id, source_check_id, check_number,
                            opened_at, closed_at,
                            subtotal, tax_amount, tip_amount, total_amount
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        order_id,
                        check['guid'],
                        check.get('displayNumber'),
                        normalizer.parse_timestamp(check.get('openedDate')),
                        normalizer.parse_timestamp(check.get('closedDate')),
                        normalizer.cents_to_dollars(check.get('amount', 0)),
                        normalizer.cents_to_dollars(check.get('taxAmount', 0)),
                        normalizer.cents_to_dollars(check.get('tipAmount', 0)),
                        normalizer.cents_to_dollars(check.get('totalAmount', 0))
                    ))
                    
                    # Process selections (order items)
                    for idx, selection in enumerate(check.get('selections', [])):
                        if selection.get('voided'):
                            continue
                        
                        # Get or create product
                        item = selection.get('item', {})
                        item_group = selection.get('itemGroup', {})
                        
                        # Calculate unit price (price / quantity)
                        total_price = selection.get('price', 0)
                        quantity = selection.get('quantity', 1)
                        unit_price = total_price / quantity if quantity > 0 else total_price
                        
                        product_id = etl_db.get_or_create_product(
                            name=item.get('name', selection.get('displayName')),
                            category_name=item_group.get('name', 'Unknown'),
                            price=normalizer.cents_to_dollars(unit_price),
                            source='TOAST',
                            source_product_id=item.get('guid', f"toast_{order_id}_{idx}")
                        )
                        
                        # Insert order item
                        # type: ignore
                        db_conn.cur.execute("""
                            INSERT INTO order_items (
                                order_id, product_id, item_name, sequence_number,
                                quantity, unit_price, total_price, tax_amount,
                                category_name, source_item_id
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            order_id,
                            product_id,
                            selection.get('displayName'),
                            idx,
                            selection.get('quantity', 1),
                            normalizer.cents_to_dollars(selection.get('price', 0)) / selection.get('quantity', 1),
                            normalizer.cents_to_dollars(selection.get('price', 0)),
                            normalizer.cents_to_dollars(selection.get('tax', 0)),
                            item_group.get('name'),
                            selection.get('guid')
                        ))
                        
                        order_item_id = db_conn.cur.fetchone()['id']  # type: ignore
                        stats['order_items'] += 1
                        
                        # Process modifiers
                        for modifier in selection.get('modifiers', []):
                            # type: ignore
                            db_conn.cur.execute("""
                                INSERT INTO order_item_modifiers (
                                    order_item_id, modifier_name, modifier_value,
                                    price_adjustment, quantity
                                ) VALUES (%s, %s, %s, %s, %s)
                            """, (
                                order_item_id,
                                modifier.get('displayName'),
                                modifier.get('displayName'),
                                normalizer.cents_to_dollars(modifier.get('price', 0)),
                                1
                            ))
                            stats['modifiers'] += 1
                    
                    # Process payments
                    for payment in check.get('payments', []):
                        payment_type = normalizer.map_payment_type(payment.get('type', 'OTHER'))
                        
                        # type: ignore
                        db_conn.cur.execute("""
                            INSERT INTO payments (
                                order_id, source, source_payment_id,
                                payment_type, status, amount, tip_amount,
                                processing_fee, processed_at,
                                card_brand, card_last4, card_entry_method
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            order_id,
                            normalizer.normalize_source('toast'),
                            payment.get('guid'),
                            payment_type,
                            normalizer.normalize_order_status('completed'),
                            normalizer.cents_to_dollars(payment.get('amount', 0)),
                            normalizer.cents_to_dollars(payment.get('tipAmount', 0)),
                            normalizer.cents_to_dollars(payment.get('originalProcessingFee', 0)),
                            normalizer.parse_timestamp(payment.get('paidDate')),
                            payment.get('cardType'),
                            payment.get('last4Digits'),
                            None
                        ))
                        stats['payments'] += 1
                
                if stats['orders'] % 5 == 0:
                    print(f"  Processed {stats['orders']} orders...")
                    
            except Exception as e:
                print(f"  ✗ Error processing order {order_data.get('guid')}: {e}")
                stats['errors'] += 1
                db_conn.rollback()
                continue
        
        # Commit all changes
        db_conn.commit()
        
        # Print summary
        print_summary("TOAST POS LOAD COMPLETE", stats)
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        db_conn.rollback()
        raise
    finally:
        db_conn.close()


if __name__ == "__main__":
    # Path to JSON file
    json_path = Path(__file__).parent.parent.parent / 'data' / 'sources' / 'toast_pos_export.json'
    
    # Check if file exists
    if not json_path.exists():
        print(f"✗ Error: File not found: {json_path}")
        sys.exit(1)
    
    # Load data
    clear_existing = '--clear' in sys.argv
    load_toast_data(str(json_path), clear_existing=clear_existing)

