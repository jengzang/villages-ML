"""
Test script to verify regional aggregates endpoints work after optimization
"""
import sqlite3
import sys
from api.regional.aggregates_realtime import (
    compute_city_aggregates,
    compute_county_aggregates
)

def test_city_aggregates():
    """Test city aggregates computation"""
    print("Testing city aggregates...")
    conn = sqlite3.connect('data/villages.db')
    conn.row_factory = sqlite3.Row

    try:
        # Test all cities
        results = compute_city_aggregates(conn)
        print(f"[OK] Found {len(results)} cities")

        # Test specific city
        results = compute_city_aggregates(conn, city_name='广州市')
        if results:
            print(f"[OK] Guangzhou: {results[0]['total_villages']} villages")
            print(f"  - Avg name length: {results[0]['avg_name_length']:.2f}")
            print(f"  - Mountain: {results[0]['sem_mountain_pct']:.2f}%")
            print(f"  - Water: {results[0]['sem_water_pct']:.2f}%")

        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def test_county_aggregates():
    """Test county aggregates computation"""
    print("\nTesting county aggregates...")
    conn = sqlite3.connect('data/villages.db')
    conn.row_factory = sqlite3.Row

    try:
        # Test specific county
        results = compute_county_aggregates(conn, county_name='天河区')
        if results:
            print(f"[OK] Tianhe: {results[0]['total_villages']} villages")
            print(f"  - Avg name length: {results[0]['avg_name_length']:.2f}")

        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = True
    success = test_city_aggregates() and success
    success = test_county_aggregates() and success

    if success:
        print("\n[OK] All tests passed!")
        sys.exit(0)
    else:
        print("\n[ERROR] Some tests failed")
        sys.exit(1)
