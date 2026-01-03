"""
Master ETL Script - Load All Restaurant Data
Loads data from all sources in the correct order
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from load_toast_data import load_toast_data
from load_doordash_data import load_doordash_data
from load_square_data import load_square_data
from etl_utils import DatabaseConnection, print_summary
from datetime import datetime


def load_all_data(clear_existing: bool = False):
    """Load all restaurant data from all sources"""
    
    print("\n" + "="*70)
    print(" " * 15 + "🚀 MASTER ETL PIPELINE 🚀")
    print("="*70)
    print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Clear Existing: {clear_existing}")
    print("="*70 + "\n")
    
    start_time = datetime.now()
    
    # Define data paths
    # In Docker, data is mounted at /app/data (from ./data on host)
    # Check Docker mount path first, then fall back to relative path
    docker_data_path = Path('/app/data/sources')
    if docker_data_path.exists():
        base_path = docker_data_path
    else:
        # Fall back to relative path (for local execution outside Docker)
        base_path = Path(__file__).parent.parent.parent / 'data' / 'sources'
    toast_path = base_path / 'toast_pos_export.json'
    doordash_path = base_path / 'doordash_orders.json'
    square_path = base_path / 'square'
    
    # Check all files exist
    print("Checking data files...")
    all_exist = True
    
    if not toast_path.exists():
        print(f"  ✗ Missing: {toast_path}")
        all_exist = False
    else:
        print(f"  ✓ Found: toast_pos_export.json")
    
    if not doordash_path.exists():
        print(f"  ✗ Missing: {doordash_path}")
        all_exist = False
    else:
        print(f"  ✓ Found: doordash_orders.json")
    
    if not square_path.exists():
        print(f"  ✗ Missing: {square_path}")
        all_exist = False
    else:
        square_files = ['catalog.json', 'locations.json', 'orders.json', 'payments.json']
        for filename in square_files:
            if not (square_path / filename).exists():
                print(f"  ✗ Missing: square/{filename}")
                all_exist = False
            else:
                print(f"  ✓ Found: square/{filename}")
    
    if not all_exist:
        print("\n✗ Some data files are missing. Aborting.")
        sys.exit(1)
    
    print("\n✓ All data files found\n")
    
    # Load data from each source
    sources_loaded = []
    sources_failed = []
    
    try:
        # 1. Toast POS
        print("\n" + "─"*70)
        print("📊 LOADING SOURCE 1/3: TOAST POS")
        print("─"*70)
        load_toast_data(str(toast_path), clear_existing=clear_existing)
        sources_loaded.append('Toast POS')
        
        # 2. DoorDash
        print("\n" + "─"*70)
        print("📊 LOADING SOURCE 2/3: DOORDASH")
        print("─"*70)
        load_doordash_data(str(doordash_path), clear_existing=False)  # Don't clear after first load
        sources_loaded.append('DoorDash')
        
        # 3. Square POS
        print("\n" + "─"*70)
        print("📊 LOADING SOURCE 3/3: SQUARE POS")
        print("─"*70)
        load_square_data(square_path, clear_existing=False)  # Don't clear after first load
        sources_loaded.append('Square POS')
        
    except Exception as e:
        print(f"\n✗ Error during ETL: {e}")
        sources_failed.append(str(e))
    
    # Get final stats
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "="*70)
    print(" " * 20 + "✅ ETL COMPLETE ✅")
    print("="*70)
    
    print(f"\n  Sources Loaded: {len(sources_loaded)}/3")
    for source in sources_loaded:
        print(f"    ✓ {source}")
    
    if sources_failed:
        print(f"\n  Sources Failed: {len(sources_failed)}")
        for error in sources_failed:
            print(f"    ✗ {error}")
    
    print(f"\n  Start Time:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  End Time:    {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Duration:    {duration.total_seconds():.2f} seconds")
    
    # Get database stats
    try:
        db = DatabaseConnection()
        db.connect()
        
        print("\n" + "─"*70)
        print("  FINAL DATABASE STATISTICS")
        print("─"*70)
        
        tables = [
            'locations',
            'categories',
            'products',
            'orders',
            'order_items',
            'payments',
            'delivery_orders',
            'toast_checks'
        ]
        
        for table in tables:
            db.cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = db.cur.fetchone()['count']
            print(f"  {table:<25} {count:>10,}")
        
        # Run validation
        print("\n" + "─"*70)
        print("  DATA VALIDATION")
        print("─"*70)
        
        db.cur.execute("SELECT * FROM validate_etl_data()")
        results = db.cur.fetchall()
        
        for row in results:
            status_icon = "✓" if row['status'] == 'OK' else "✗"
            print(f"  {status_icon} {row['check_name']:<25} {row['details']}")
        
        db.close()
        
    except Exception as e:
        print(f"\n  ⚠️  Could not retrieve final stats: {e}")
    
    print("\n" + "="*70)
    print(" " * 15 + "🎉 ALL DATA LOADED 🎉")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Parse arguments
    clear_existing = '--clear' in sys.argv or '-c' in sys.argv
    
    if clear_existing:
        print("\n⚠️  WARNING: This will DELETE all existing data!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    load_all_data(clear_existing=clear_existing)

