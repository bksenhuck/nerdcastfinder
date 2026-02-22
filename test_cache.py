#!/usr/bin/env python3
"""
Cache testing script - Demonstrates cache hit/miss behavior

Run from: python test_cache.py

Requirements:
- Backend running on http://localhost:8005
- Database with indexed episodes
"""

import requests
import time
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8005/api"
SEARCH_ENDPOINT = f"{BASE_URL}/search"
CACHE_STATS_ENDPOINT = f"{BASE_URL}/cache/stats"
CACHE_CLEAR_ENDPOINT = f"{BASE_URL}/cache/clear"


def print_section(title: str) -> None:
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_stats(stats: Dict[str, Any]) -> None:
    """Pretty print cache statistics"""
    print(f"  Hits:             {stats['hits']}")
    print(f"  Misses:           {stats['misses']}")
    print(f"  Total Requests:   {stats['total_requests']}")
    print(f"  Hit Rate:         {stats['hit_rate_percent']:.2f}%")
    print(f"  Cached Entries:   {stats['cached_entries']}/{stats['max_entries']}")
    print(f"  TTL:              {stats['ttl_seconds']} seconds")
    print()


def test_cache_hit_miss() -> None:
    """Test basic cache hit/miss behavior"""
    print_section("TEST 1: Basic Cache Hit/Miss")
    
    # Clear cache first
    print("Clearing cache...")
    requests.post(CACHE_CLEAR_ENDPOINT)
    print("✓ Cache cleared\n")
    
    # Get initial stats
    resp = requests.get(CACHE_STATS_ENDPOINT)
    initial_stats = resp.json()
    print("Initial stats:")
    print_stats(initial_stats)
    
    # Search 1: MISS
    print("→ Search 1: 'inteligência artificial' (MISS expected)")
    start = time.time()
    result1 = requests.get(
        SEARCH_ENDPOINT,
        params={"q": "inteligência artificial", "top_k": 5}
    )
    time1 = time.time() - start
    results1_count = len(result1.json())
    print(f"  ✓ {results1_count} results in {time1:.3f}s\n")
    
    # Check stats after MISS
    resp = requests.get(CACHE_STATS_ENDPOINT)
    stats_after_miss = resp.json()
    print("After search 1 (should have 1 MISS):")
    print_stats(stats_after_miss)
    
    # Search 2: HIT (identical query)
    print("→ Search 2: 'inteligência artificial' (HIT expected)")
    start = time.time()
    result2 = requests.get(
        SEARCH_ENDPOINT,
        params={"q": "inteligência artificial", "top_k": 5}
    )
    time2 = time.time() - start
    results2_count = len(result2.json())
    print(f"  ✓ {results2_count} results in {time2:.3f}s\n")
    
    # Check stats after HIT
    resp = requests.get(CACHE_STATS_ENDPOINT)
    stats_after_hit = resp.json()
    print("After search 2 (should have 1 HIT):")
    print_stats(stats_after_hit)
    
    # Validate
    assert stats_after_hit['hits'] == 1, "Expected 1 hit"
    assert stats_after_hit['misses'] == 1, "Expected 1 miss"
    assert time2 < time1, f"Cache hit should be faster ({time2:.3f}s vs {time1:.3f}s)"
    print(f"✓ SUCCESS: Cache HIT was {time1/time2:.1f}x faster!\n")


def test_different_params() -> None:
    """Test that different parameters create different cache entries"""
    print_section("TEST 2: Different Parameters = Different Cache Entries")
    
    # Clear cache
    requests.post(CACHE_CLEAR_ENDPOINT)
    print("✓ Cache cleared\n")
    
    # Search A: top_k=5
    print("→ Search A: 'podcast' with top_k=5 (MISS)")
    requests.get(SEARCH_ENDPOINT, params={"q": "podcast", "top_k": 5})
    resp = requests.get(CACHE_STATS_ENDPOINT)
    stats_a = resp.json()
    print(f"  Stats: {stats_a['misses']} misses, {stats_a['hits']} hits\n")
    
    # Search B: Same query, different top_k
    print("→ Search B: 'podcast' with top_k=10 (MISS expected - different param)")
    requests.get(SEARCH_ENDPOINT, params={"q": "podcast", "top_k": 10})
    resp = requests.get(CACHE_STATS_ENDPOINT)
    stats_b = resp.json()
    print(f"  Stats: {stats_b['misses']} misses, {stats_b['hits']} hits\n")
    
    # Search C: Same as A
    print("→ Search C: 'podcast' with top_k=5 again (HIT expected)")
    requests.get(SEARCH_ENDPOINT, params={"q": "podcast", "top_k": 5})
    resp = requests.get(CACHE_STATS_ENDPOINT)
    stats_c = resp.json()
    print(f"  Stats: {stats_c['misses']} misses, {stats_c['hits']} hits\n")
    
    # Validate
    assert stats_c['misses'] == 2, f"Expected 2 misses, got {stats_c['misses']}"
    assert stats_c['hits'] == 1, f"Expected 1 hit, got {stats_c['hits']}"
    print("✓ SUCCESS: Different parameters handled correctly!\n")


def test_query_normalization() -> None:
    """Test that query normalization works (case-insensitive)"""
    print_section("TEST 3: Query Normalization (Case Insensitive)")
    
    # Clear cache
    requests.post(CACHE_CLEAR_ENDPOINT)
    print("✓ Cache cleared\n")
    
    # Search A: lowercase
    print("→ Search A: 'PYTHON' (uppercase, MISS)")
    requests.get(SEARCH_ENDPOINT, params={"q": "PYTHON", "top_k": 5})
    resp = requests.get(CACHE_STATS_ENDPOINT)
    stats_a = resp.json()
    print(f"  Stats: {stats_a['misses']} misses\n")
    
    # Search B: same word, different case
    print("→ Search B: 'python' (lowercase, HIT expected - normalizeed to same key)")
    requests.get(SEARCH_ENDPOINT, params={"q": "python", "top_k": 5})
    resp = requests.get(CACHE_STATS_ENDPOINT)
    stats_b = resp.json()
    print(f"  Stats: {stats_b['hits']} hits\n")
    
    # Validate
    assert stats_b['hits'] == 1, f"Expected 1 hit (normalized query), got {stats_b['hits']}"
    print("✓ SUCCESS: Query normalization working!\n")


def test_management_endpoints() -> None:
    """Test cache management endpoints"""
    print_section("TEST 4: Cache Management Endpoints")
    
    # Clear and populate cache
    print("→ Populating cache...")
    requests.post(CACHE_CLEAR_ENDPOINT)
    for i, query in enumerate(["python", "javascript", "golang"], 1):
        requests.get(SEARCH_ENDPOINT, params={"q": query, "top_k": 3})
        print(f"  Search {i}: '{query}'")
    
    # Check stats
    resp = requests.get(CACHE_STATS_ENDPOINT)
    stats = resp.json()
    print(f"\n→ Before clear: {stats['cached_entries']} entries\n")
    assert stats['cached_entries'] == 3, "Expected 3 entries"
    
    # Clear cache
    print("→ Clearing cache...")
    resp = requests.post(CACHE_CLEAR_ENDPOINT)
    print(f"  Response: {resp.json()}\n")
    
    # Verify cleared
    resp = requests.get(CACHE_STATS_ENDPOINT)
    stats = resp.json()
    print(f"→ After clear: {stats['cached_entries']} entries")
    assert stats['cached_entries'] == 0, "Expected 0 entries after clear"
    
    # Reset stats
    print("→ Resetting statistics...")
    requests.post(f"{BASE_URL}/cache/reset-stats")
    resp = requests.get(CACHE_STATS_ENDPOINT)
    stats = resp.json()
    print(f"  Hits: {stats['hits']}, Misses: {stats['misses']}\n")
    assert stats['hits'] == 0 and stats['misses'] == 0, "Stats should be reset"
    
    print("✓ SUCCESS: Management endpoints working!\n")


def main() -> None:
    """Run all tests"""
    print("\n" + "="*60)
    print("  🚀 CACHE TESTING SUITE")
    print("="*60)
    
    try:
        # Verify backend is running
        print("\n→ Checking if backend is running...")
        resp = requests.get(CACHE_STATS_ENDPOINT, timeout=2)
        if resp.status_code == 200:
            print("✓ Backend is responding\n")
        else:
            raise Exception("Backend returned non-200 status")
    except requests.exceptions.ConnectionError:
        print("✗ ERROR: Cannot connect to backend at http://localhost:8005")
        print("  Make sure the backend is running: python -m uvicorn ...\n")
        return
    except Exception as e:
        print(f"✗ ERROR: {e}\n")
        return
    
    # Run tests
    try:
        test_cache_hit_miss()
        test_different_params()
        test_query_normalization()
        test_management_endpoints()
        
        print_section("✅ ALL TESTS PASSED!")
        print("Cache is working correctly and ready for production\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        return
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    main()
