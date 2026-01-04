"""
ETL Utilities for Restaurant Analytics
Shared functions for data cleaning, normalization, and database operations
"""

import re
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
from decimal import Decimal
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# Look for .env in the project root (two levels up from my-api/scripts/)
# Project structure: project_root/.env, project_root/my-api/scripts/etl_utils.py
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class DatabaseConnection:
    """Manages PostgreSQL database connection"""
    
    def __init__(self):
        self.conn: Optional[psycopg2.extensions.connection] = None
        self.cur: Optional[psycopg2.extensions.cursor] = None
        
    def connect(self):
        """Connect to PostgreSQL database (Supabase or local)"""
        # Prefer Supabase configuration if available
        supabase_db_host = os.getenv('SUPABASE_DB_HOST')
        if supabase_db_host:
            db_host = supabase_db_host
            db_port = os.getenv('SUPABASE_DB_PORT', '5432')
            # Supabase default database name is 'postgres'
            db_name = os.getenv('SUPABASE_DB_NAME', os.getenv('DB_NAME', 'postgres'))
            db_user = os.getenv('SUPABASE_DB_USER', os.getenv('DB_USER', 'postgres'))
            db_password = os.getenv('SUPABASE_DB_PASSWORD', os.getenv('DB_PASSWORD', ''))
            if not db_password:
                raise ValueError("SUPABASE_DB_PASSWORD must be set when using Supabase")
            print(f"✓ Connecting to Supabase database: {db_name}@{db_host}:{db_port}")
        else:
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5433')  # Default to Docker port
            db_name = os.getenv('DB_NAME', os.getenv('POSTGRES_DB', 'restaurant_analytics'))
            db_user = os.getenv('DB_USER', os.getenv('POSTGRES_USER', 'postgres'))
            db_password = os.getenv('DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', 'postgres'))
            print(f"✓ Connecting to local database: {db_name}@{db_host}:{db_port}")
        
        self.conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)  # type: ignore
        print(f"✓ Connected to database: {self.conn.get_dsn_parameters()['dbname']}")
        
    def close(self):
        """Close database connection"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        print("✓ Database connection closed")
        
    def commit(self):
        """Commit transaction"""
        self.conn.commit()
        
    def rollback(self):
        """Rollback transaction"""
        self.conn.rollback()


class DataNormalizer:
    """Handles data cleaning and normalization"""
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize product/category name for matching
        - Lowercase
        - Remove emojis and special chars
        - Trim whitespace
        - Remove extra spaces
        """
        if not name:
            return ""
        
        # Remove emojis and special characters
        name = re.sub(r'[^\w\s-]', '', name)
        
        # Remove extra spaces and trim (important: trim after removing emojis)
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()
        
        # Lowercase
        name = name.lower()
        
        return name
    
    @staticmethod
    def clean_product_name(name: str) -> str:
        """
        Clean product name with typo corrections
        """
        if not name:
            return ""
        
        # Title case
        name = name.strip().title()
        
        # Fix common typos
        typo_map = {
            'Griled': 'Grilled',
            'Chiken': 'Chicken',
            'Sandwhich': 'Sandwich',
            'Expresso': 'Espresso',
            'Coffe': 'Coffee',
            'Churos': 'Churros',
            'Appitizers': 'Appetizers',
        }
        
        for typo, correct in typo_map.items():
            name = re.sub(rf'\b{typo}\b', correct, name, flags=re.IGNORECASE)
        
        return name
    
    @staticmethod
    def normalize_product_base_name(name: str) -> str:
        """
        Normalize product base name to unify variations (size, style, quantity, spelling)
        
        Examples:
        - "French Fries - Large" → "French Fries"
        - "Truffle Fries" → "French Fries"
        - "Milkshake - Chocolate" → "Milkshake"
        - "Hashbrowns" → "Hash Browns"
        - "Buffalo Wings 12Pc" → "Buffalo Wings"
        - "Fresh Fruit Cup" → "Fresh Fruit"
        """
        if not name:
            return ""
        
        name = name.strip()
        
        # Normalize spelling variations first
        spelling_map = {
            r'\bhashbrowns\b': 'Hash Browns',
            r'\bhash\s*browns\b': 'Hash Browns',
            r'\bexpresso\b': 'Espresso',
            r'\bcoffe\b': 'Coffee',
            r'\bchuros\b': 'Churros',
        }
        
        for pattern, replacement in spelling_map.items():
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
        
        # Remove size variations
        size_patterns = [
            r'\s*-\s*(small|sm|medium|med|md|large|lg|lrg|regular|reg)\s*$',
            r'\s+(small|sm|medium|med|md|large|lg|lrg|regular|reg)\s*$',
            r'^\s*(small|sm|medium|med|md|large|lg|lrg|regular|reg)\s+',
        ]
        
        for pattern in size_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Remove style/flavor variations
        style_patterns = [
            r'\s*-\s*(chocolate|vanilla|strawberry|double|dbl|single|pint|glass|bottle|slice|whole)\s*$',
            r'\s+(chocolate|vanilla|strawberry|double|dbl|single|pint|glass|bottle|slice|whole)\s*$',
            r'^\s*(chocolate|vanilla|strawberry|double|dbl|single|pint|glass|bottle|slice|whole)\s+',
        ]
        
        for pattern in style_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Remove quantity variations
        quantity_patterns = [
            r'\s*-\s*\d+\s*(pc|pcs|piece|pieces)\s*$',
            r'\s+\d+\s*(pc|pcs|piece|pieces)\s*$',
            r'\s*\(\d+\)\s*$',
            r'\s*\d+pc\s*$',
            r'\s*\d+pcs\s*$',
        ]
        
        for pattern in quantity_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Handle specific product name normalizations
        # Order matters: more specific patterns first
        product_normalizations = {
            # Fries variations - unify all fries (size and style variations)
            r'^Fries\s*-\s*Large$': 'French Fries',
            r'^Fries\s+Large$': 'French Fries',
            r'^Fries$': 'French Fries',
            r'^French\s+Fries\s*-\s*Large$': 'French Fries',
            r'^French\s+Fries\s+Large$': 'French Fries',
            r'^Truffle\s+Fries$': 'French Fries',  # Style variation, same base product
            # Note: Sweet Potato Fries kept separate (different product)
            
            # Wings variations - unify all wings to "Buffalo Wings"
            r'^Wings\s+\d+pc$': 'Buffalo Wings',
            r'^Wings\s+\d+pcs$': 'Buffalo Wings',
            r'^Wings\s+12Pc$': 'Buffalo Wings',  # Case variation
            r'^Wings\s+12pc$': 'Buffalo Wings',
            r'^Wings\s*-\s*\d+\s+piece$': 'Buffalo Wings',
            r'^Wings\s*\(\d+\)$': 'Buffalo Wings',
            r'^Wings$': 'Buffalo Wings',
            r'^Chicken\s+Wings$': 'Buffalo Wings',
            r'^Chicken\s+Wings\s+\d+pc$': 'Buffalo Wings',
            r'^Chicken\s+Wings\s+\d+pcs$': 'Buffalo Wings',
            r'^Buffalo\s+Wings\s+\d+pc$': 'Buffalo Wings',
            r'^Buffalo\s+Wings\s+\d+pcs$': 'Buffalo Wings',
            r'^Buffalo\s+Wings\s+12Pc$': 'Buffalo Wings',  # Case variation
            r'^Buffalo\s+Wings\s+12pc$': 'Buffalo Wings',
            r'^Buffalo\s+Wings\s*-\s*\d+\s+piece$': 'Buffalo Wings',
            r'^Buffalo\s+Wings\s*\(\d+\)$': 'Buffalo Wings',
            r'^Buffalo\s+Chicken\s+Wings$': 'Buffalo Wings',
            
            # Wine variations
            r'^House\s+Wine$': 'House Red Wine',
            r'^House\s+Wine\s*\(red\)$': 'House Red Wine',
            r'^House\s+Red\s+Wine\s*-\s*Glass$': 'House Red Wine',
            r'^House\s+Red\s+Wine\s*-\s*Bottle$': 'House Red Wine',
            
            # Beer variations
            r'^Pitcher\s+Of\s+Beer$': 'Craft Beer',
            r'^Pitcher\s+Of\s+Beer\s*-\s*Pint$': 'Craft Beer',
            r'^Craft\s+Beer\s*-\s*Pint$': 'Craft Beer',
            r'^Beer\s*-\s*Pint$': 'Craft Beer',
            
            # Nachos variations
            r'^Nachos\s+Grande$': 'Nachos Supreme',
            r'^Nachos\s+Grande\s*-\s*Large$': 'Nachos Supreme',
            r'^Nachos\s+Supreme\s*-\s*Large$': 'Nachos Supreme',
            
            # Milkshake variations
            r'^Chocolate\s+Milkshake$': 'Milkshake',
            r'^Milkshake\s*-\s*Chocolate$': 'Milkshake',
            
            # Espresso variations
            r'^Espresso\s*-\s*Double$': 'Espresso',
            r'^Espresso\s*-\s*Dbl\s+Shot$': 'Espresso',
            r'^Espresso\s+Doble$': 'Espresso',
            r'^Espresso\s*-\s*Single$': 'Espresso',
            
            # Pizza variations
            r'^Margherita\s+Pizza\s+Slice$': 'Margherita Pizza',
            r'^Margherita\s+Pizza\s*-\s*Slice$': 'Margherita Pizza',
            
            # Churros variations
            r'^Churros\s+\d+pc$': 'Churros',
            r'^Churros\s+\d+pcs$': 'Churros',
            r'^Churros\s*-\s*\d+\s+piece$': 'Churros',
            
            # Fruit variations
            r'^Fresh\s+Fruit\s+Cup$': 'Fresh Fruit',  # Format variation, same base product
            
            # Soft drink variations
            r'^Fountain\s+Soda\s*-\s*Lg$': 'Soft Drink',
            r'^Fountain\s+Soda$': 'Soft Drink',
            r'^Lg\s+Coke$': 'Soft Drink',
            r'^Coke$': 'Soft Drink',
            r'^Coca-Cola$': 'Soft Drink',
            r'^Soda$': 'Soft Drink',
        }
        
        for pattern, replacement in product_normalizations.items():
            if re.match(pattern, name, re.IGNORECASE):
                name = replacement
                break
        
        # Additional normalizations for generic names after removing modifiers
        # These handle cases where size/quantity was removed but base name needs fixing
        generic_normalizations = {
            r'^Fries$': 'French Fries',
            r'^Wings$': 'Buffalo Wings',
            r'^Chicken\s+Wings$': 'Buffalo Wings',
            r'^Fresh\s+Fruit$': 'Fresh Fruit',  # Keep as is, but normalize "Fresh Fruit Cup" above
        }
        
        for pattern, replacement in generic_normalizations.items():
            if re.match(pattern, name, re.IGNORECASE):
                name = replacement
                break
        
        # Clean up
        name = re.sub(r'\s+', ' ', name).strip()
        name = re.sub(r'\s*-\s*$', '', name)
        name = re.sub(r'^\s*-\s*', '', name)
        name = name.title()
        
        return name
    
    @staticmethod
    def extract_size_and_quantity(name: str) -> Tuple[Optional[str], Optional[str], str]:
        """
        Extract size and quantity from product name
        Returns: (size, quantity, cleaned_name)
        """
        original_name = name
        size = None
        quantity = None
        
        # Extract size
        size_patterns = {
            r'\b(small|sm)\b': 'small',
            r'\b(medium|med|md)\b': 'medium',
            r'\b(large|lg|lrg)\b': 'large',
            r'\b(regular|reg)\b': 'regular',
        }
        
        for pattern, size_value in size_patterns.items():
            if re.search(pattern, name, re.IGNORECASE):
                size = size_value
                name = re.sub(pattern, '', name, flags=re.IGNORECASE)
                break
        
        # Extract quantity
        quantity_patterns = [
            r'(\d+)\s*(pc|pcs|piece|pieces)',
            r'(\d+)\s*oz',
            r'(\d+)"',
        ]
        
        for pattern in quantity_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                quantity = match.group(0).lower()
                name = re.sub(pattern, '', name, flags=re.IGNORECASE)
                break
        
        # Clean up name
        name = re.sub(r'\s+', ' ', name).strip()
        name = re.sub(r'\s*-\s*$', '', name)
        
        return size, quantity, name
    
    @staticmethod
    def cents_to_dollars(cents: int) -> Decimal:
        """Convert cents to dollars"""
        return Decimal(cents) / Decimal(100)
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """
        Parse ISO 8601 timestamp to datetime
        Handles formats: 2025-01-01T10:00:00Z, 2025-01-01T10:00:00.000Z
        
        Returns:
            datetime object or None if parsing fails
        """
        if not timestamp_str:
            return None
        
        # Remove milliseconds if present
        timestamp_str = re.sub(r'\.\d+Z$', 'Z', timestamp_str)
        
        # Parse ISO 8601 format
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception as e:
            print(f"Warning: Could not parse timestamp '{timestamp_str}': {e}")
            return None
    
    @staticmethod
    def normalize_source(source: str) -> str:
        """
        Normalize source to uppercase enum value
        Returns: 'TOAST' | 'DOORDASH' | 'SQUARE'
        """
        if not source:
            return 'TOAST'
        return source.upper()
    
    @staticmethod
    def normalize_order_status(status: str) -> str:
        """
        Normalize order status to uppercase enum value
        Returns: 'PENDING' | 'COMPLETED' | 'CANCELLED' | 'REFUNDED'
        """
        if not status:
            return 'COMPLETED'
        return status.upper()
    
    @staticmethod
    def map_order_type(source_type: str, source: str) -> str:
        """
        Map source-specific order types to unified enum
        Returns: 'DINE_IN' | 'TAKEOUT' | 'DELIVERY' | 'PICKUP'
        """
        source_type = source_type.upper() if source_type else ""
        
        mapping = {
            'DINE_IN': 'DINE_IN',
            'TAKE_OUT': 'TAKEOUT',
            'TAKEOUT': 'TAKEOUT',
            'DELIVERY': 'DELIVERY',
            'PICKUP': 'PICKUP',
            'MERCHANT_DELIVERY': 'DELIVERY',
        }
        
        return mapping.get(source_type, 'DINE_IN')
    
    @staticmethod
    def map_payment_type(source_type: str) -> str:
        """
        Map source-specific payment types to unified enum
        Returns: 'CARD' | 'CASH' | 'DIGITAL_WALLET' | 'OTHER' | 'UNKNOWN'
        """
        source_type = source_type.upper() if source_type else ""
        
        if source_type in ['CREDIT', 'CARD', 'DEBIT']:
            return 'CARD'
        elif source_type == 'CASH':
            return 'CASH'
        elif source_type in ['WALLET', 'APPLE_PAY', 'GOOGLE_PAY']:
            return 'DIGITAL_WALLET'
        elif source_type in ['UNKNOWN', '']:
            return 'UNKNOWN'
        else:
            return 'OTHER'
    
    @staticmethod
    def correct_location_data(city: Optional[str], state: Optional[str]) -> str:
        """
        Correct known errors in location data.
        - Jamaica, NY → New York, NY (Jamaica is a neighborhood in Queens, NY)
        
        Args:
            city: City name (can be None)
            state: State code (e.g., 'NY', can be None)
        
        Returns:
            Corrected city name or original city if no correction needed
        """
        if not city or not state:
            return city or ""
        
        corrections = {
            ('Jamaica', 'NY'): 'New York',
            # Add more corrections here as needed
        }
        return corrections.get((city, state), city)
    
    @staticmethod
    def normalize_location_name(name: str) -> str:
        """
        Normalize location names for matching and consolidation.
        - Lowercase
        - Trim whitespace
        - Remove extra spaces
        
        Args:
            name: Location name
        
        Returns:
            Normalized name
        """
        if not name:
            return ""
        return name.lower().strip()


class ETLDatabase:
    """Database operations for ETL"""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.normalizer = DataNormalizer()
        
        # Caches
        self._location_cache = {}
        self._category_cache = {}
        self._product_cache = {}
        
    def get_or_create_location(self, name: str, address: Dict, timezone: str, 
                                source: str, source_id: str) -> int:
        """
        Get or create location by source and source_id.
        
        Each location is kept separate per source to maintain traceability.
        This ensures that orders from different sources can reference their
        specific location even if they represent the same physical restaurant.
        
        Args:
            name: Location name
            address: Dictionary with address data
            timezone: IANA timezone (e.g., 'America/New_York')
            source: Data source ('TOAST', 'DOORDASH', 'SQUARE')
            source_id: Unique location ID in the source
        
        Returns:
            location_id
        """
        # Check cache
        cache_key = f"{source}:{source_id}"
        if cache_key in self._location_cache:
            return self._location_cache[cache_key]
        
        # Normalize source
        source = self.normalizer.normalize_source(source)
        
        # Check if exists by source_id (one location per source+source_id)
        self.db.cur.execute("""
            SELECT id FROM locations 
            WHERE source_ids->>%s = %s
        """, (source, source_id))
        
        result = self.db.cur.fetchone()
        if result:
            location_id = result['id']
            self._location_cache[cache_key] = location_id
            return location_id
        
        # Apply data corrections
        city = address.get('city') or address.get('locality')
        state = address.get('state') or address.get('administrative_district_level_1')
        corrected_city = self.normalizer.correct_location_data(city, state)
        
        # Prepare address fields
        address_line1 = address.get('address_line1') or address.get('line1') or address.get('street')
        zip_code = address.get('zip_code') or address.get('zip') or address.get('postal_code')
        country = address.get('country', 'US')
        
        # Create new location (one per source+source_id)
        source_ids = {source: source_id}
        
        self.db.cur.execute("""
            INSERT INTO locations (name, address_line1, city, state, zip_code, 
                                  country, timezone, source_ids)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            name,
            address_line1,
            corrected_city,  # Use corrected city
            state,
            zip_code,
            country,
            timezone,
            psycopg2.extras.Json(source_ids)
        ))
        
        location_id = self.db.cur.fetchone()['id']
        self._location_cache[cache_key] = location_id
        
        print(f"  ✓ Created location: {name} ({source}) (ID: {location_id})")
        return location_id
    
    def get_or_create_category(self, category_name: str) -> int:
        """
        Get or create category using the database function
        Returns category_id
        """
        if not category_name:
            return None
        
        # Check cache
        normalized = self.normalizer.normalize_name(category_name)
        if normalized in self._category_cache:
            return self._category_cache[normalized]
        
        # Use database function
        self.db.cur.execute("""
            SELECT get_or_create_category(%s) as id
        """, (category_name,))
        
        category_id = self.db.cur.fetchone()['id']
        self._category_cache[normalized] = category_id
        
        return category_id
    
    def get_or_create_product(self, name: str, category_name: str, 
                              price: Decimal, source: str, 
                              source_product_id: str) -> int:
        """
        Get or create product with fuzzy matching
        Returns product_id
        """
        # Clean product name
        clean_name = self.normalizer.clean_product_name(name)
        
        # Normalize product base name to unify variations (size, style, quantity)
        normalized_base_name = self.normalizer.normalize_product_base_name(clean_name)
        
        # Use normalized base name for matching
        normalized = self.normalizer.normalize_name(normalized_base_name)
        
        # Extract size and quantity from original clean name
        size, quantity, base_name = self.normalizer.extract_size_and_quantity(clean_name)
        
        # Check if mapping already exists
        self.db.cur.execute("""
            SELECT product_id FROM product_mappings 
            WHERE source = %s AND source_product_id = %s
        """, (source, source_product_id))
        
        result = self.db.cur.fetchone()
        if result:
            return result['product_id']
        
        # Try to find existing product by normalized name
        self.db.cur.execute("""
            SELECT id FROM products 
            WHERE normalized_name = %s
            LIMIT 1
        """, (normalized,))
        
        result = self.db.cur.fetchone()
        
        if result:
            product_id = result['id']
        else:
            # Create new product using normalized base name
            category_id = self.get_or_create_category(category_name)
            
            self.db.cur.execute("""
                INSERT INTO products (name, normalized_name, category_id, 
                                     base_price, size, quantity)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                normalized_base_name,  # Use normalized base name for product name
                normalized,
                category_id,
                price,
                size,
                quantity
            ))
            
            product_id = self.db.cur.fetchone()['id']
            print(f"  ✓ Created product: {normalized_base_name} (ID: {product_id})")
        
        # Create mapping
        self.db.cur.execute("""
            INSERT INTO product_mappings 
            (product_id, source, source_product_id, source_product_name, 
             source_price, match_confidence, is_manual_match)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_product_id) DO NOTHING
        """, (
            product_id,
            source,
            source_product_id,
            name,  # Original name
            price,
            1.0,  # Perfect match
            False
        ))
        
        return product_id
    
    def clear_all_data(self):
        """Clear all data from tables (for fresh load)"""
        print("\n⚠️  Clearing all existing data...")
        
        tables = [
            'toast_checks',
            'delivery_orders',
            'order_item_modifiers',
            'order_items',
            'payments',
            'orders',
            'product_mappings',
            'products',
            'categories',
            'locations'
        ]
        
        for table in tables:
            self.db.cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            print(f"  ✓ Cleared {table}")
        
        self.db.commit()
        print("✓ All data cleared\n")
        
        # Clear caches
        self._location_cache = {}
        self._category_cache = {}
        self._product_cache = {}


def fix_appitizers_typo(db_conn: DatabaseConnection):
    """
    Fix the "Appitizers" typo by merging it with "Appetizers"
    Merges the duplicate category and updates all references
    
    Args:
        db_conn: DatabaseConnection instance
    """
    print("\n" + "="*60)
    print("  FIXING 'APPITIZERS' TYPO → 'APPETIZERS'")
    print("="*60 + "\n")
    
    try:
        # 1. Find the categories
        db_conn.cur.execute("""
            SELECT id, name, normalized_name 
            FROM categories 
            WHERE normalized_name IN ('appitizers', 'appetizers')
            ORDER BY normalized_name
        """)
        categories = db_conn.cur.fetchall()
        
        if not categories:
            print("  ✓ No categories with 'appitizers' or 'appetizers' found.")
            return
        
        print(f"  Found {len(categories)} categories:")
        for cat in categories:
            print(f"    - ID: {cat['id']}, Name: '{cat['name']}', Normalized: '{cat['normalized_name']}'")
        
        # 2. Determine which is the "master" (prefer "appetizers" if both exist)
        appetizers_cat = None
        appitizers_cat = None
        
        for cat in categories:
            if cat['normalized_name'] == 'appetizers':
                appetizers_cat = cat
            elif cat['normalized_name'] == 'appitizers':
                appitizers_cat = cat
        
        # 3. If both exist, merge appitizers into appetizers
        if appetizers_cat and appitizers_cat:
            print(f"\n  → Merging 'Appitizers' (ID: {appitizers_cat['id']}) into 'Appetizers' (ID: {appetizers_cat['id']})")
            
            # Update all products pointing to appitizers to point to appetizers
            db_conn.cur.execute("""
                UPDATE products 
                SET category_id = %s 
                WHERE category_id = %s
            """, (appetizers_cat['id'], appitizers_cat['id']))
            products_updated = db_conn.cur.rowcount
            print(f"    ✓ Updated {products_updated} products")
            
            # Update source_names in appetizers to include appitizers variants
            db_conn.cur.execute("""
                UPDATE categories
                SET source_names = source_names || (
                    SELECT source_names FROM categories WHERE id = %s
                )
                WHERE id = %s
            """, (appitizers_cat['id'], appetizers_cat['id']))
            
            # Delete the appitizers category
            db_conn.cur.execute("DELETE FROM categories WHERE id = %s", (appitizers_cat['id'],))
            print(f"    ✓ Deleted duplicate category 'Appitizers'")
            
        elif appitizers_cat and not appetizers_cat:
            # Only appitizers exists, rename it to appetizers
            print(f"\n  → Renaming 'Appitizers' (ID: {appitizers_cat['id']}) to 'Appetizers'")
            db_conn.cur.execute("""
                UPDATE categories 
                SET name = 'Appetizers', 
                    normalized_name = 'appetizers'
                WHERE id = %s
            """, (appitizers_cat['id'],))
            print(f"    ✓ Renamed category")
        
        # 4. Commit changes
        db_conn.commit()
        print("\n✓ Typo fix complete!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        db_conn.rollback()
        raise


def print_summary(title: str, stats: Dict):
    """Print formatted summary"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    for key, value in stats.items():
        print(f"  {key:<30} {value:>10}")
    print(f"{'='*60}\n")

