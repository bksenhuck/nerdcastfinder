"""
Simple in-memory cache with TTL support for search results.
Thread-safe implementation using standard library only.
"""
import logging
import time
import threading
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from hashlib import md5

logger = logging.getLogger("uvicorn.error")


@dataclass
class CacheEntry:
    """Represents a cached entry with expiration"""
    data: Any
    timestamp: float
    
    def is_expired(self, ttl: int) -> bool:
        """Check if entry has expired based on TTL (in seconds)"""
        return (time.time() - self.timestamp) > ttl


class SimpleCache:
    """
    Thread-safe in-memory cache for search results.
    
    Features:
    - Configurable TTL (Time To Live) per entry
    - Thread-safe operations using locks
    - Query normalization (lowercase, strip whitespace)
    - Automatic expiration checking
    - Hit/miss statistics
    - Configurable max size with LRU eviction
    """
    
    def __init__(self, ttl_seconds: int = 600, max_entries: int = 1000):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Time to live for cached items (default: 10 minutes)
            max_entries: Maximum number of entries before LRU eviction (default: 1000)
        """
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._cache: Dict[str, CacheEntry] = {}
        self._access_times: Dict[str, float] = {}  # Track access time for LRU
        self._lock = threading.Lock()  # Protect cache from concurrent access
        self.hits = 0
        self.misses = 0
    
    def _normalize_query(self, query: str) -> str:
        """
        Normalize query string for cache key.
        
        Args:
            query: Raw query string
            
        Returns:
            Normalized query (lowercase, stripped)
        """
        return query.lower().strip()
    
    def _make_cache_key(
        self,
        query: str,
        top_k: Optional[int] = None,
        podcast_source: Optional[str] = None,
        program_name: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> str:
        """
        Generate a unique cache key based on search parameters.
        
        Uses MD5 hash of normalized parameters to keep key length reasonable.
        
        Args:
            query: Search query
            top_k: Number of results
            podcast_source: Optional podcast source filter
            program_name: Optional program name filter
            min_confidence: Optional confidence threshold
            
        Returns:
            Unique cache key string
        """
        # Normalize all parameters
        normalized_query = self._normalize_query(query)
        
        # Build tuple of all parameters
        key_parts = (
            normalized_query,
            str(top_k or ""),
            str(podcast_source or ""),
            str(program_name or ""),
            str(min_confidence or ""),
        )
        
        # Join and hash to create final key
        key_string = "|".join(key_parts)
        cache_key = md5(key_string.encode()).hexdigest()
        
        return cache_key
    
    def _evict_oldest(self) -> None:
        """
        Remove least recently used entry when cache is full.
        Should be called while holding lock.
        """
        if self._cache and len(self._cache) >= self.max_entries:
            # Find oldest accessed key
            oldest_key = min(
                (k for k in self._cache.keys() if k in self._access_times),
                key=lambda k: self._access_times[k],
                default=None
            )
            
            if oldest_key:
                del self._cache[oldest_key]
                del self._access_times[oldest_key]
                logger.debug(f"[CACHE] LRU eviction: removed oldest entry")
    
    def get(
        self,
        query: str,
        top_k: Optional[int] = None,
        podcast_source: Optional[str] = None,
        program_name: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> Optional[List[Dict]]:
        """
        Retrieve cached search result if available and not expired.
        
        Args:
            query: Search query
            top_k: Number of results
            podcast_source: Optional podcast source filter
            program_name: Optional program name filter
            min_confidence: Optional confidence threshold
            
        Returns:
            Cached result list if hit and valid, None otherwise
        """
        cache_key = self._make_cache_key(
            query, top_k, podcast_source, program_name, min_confidence
        )
        
        with self._lock:
            # Check if key exists in cache
            if cache_key not in self._cache:
                self.misses += 1
                return None
            
            entry = self._cache[cache_key]
            
            # Check if entry has expired
            if entry.is_expired(self.ttl_seconds):
                del self._cache[cache_key]
                del self._access_times[cache_key]
                self.misses += 1
                logger.debug(
                    f"[CACHE] Expired entry removed for query: '{self._normalize_query(query)}'"
                )
                return None
            
            # Cache hit!
            self.hits += 1
            self._access_times[cache_key] = time.time()  # Update access time
            
            logger.debug(
                f"[CACHE] HIT - Query: '{self._normalize_query(query)}' "
                f"(expires in {self.ttl_seconds - (time.time() - entry.timestamp):.1f}s)"
            )
            
            return entry.data
    
    def set(
        self,
        query: str,
        result: List[Dict],
        top_k: Optional[int] = None,
        podcast_source: Optional[str] = None,
        program_name: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> None:
        """
        Store search result in cache.
        
        Args:
            query: Search query
            result: Search results to cache
            top_k: Number of results
            podcast_source: Optional podcast source filter
            program_name: Optional program name filter
            min_confidence: Optional confidence threshold
        """
        cache_key = self._make_cache_key(
            query, top_k, podcast_source, program_name, min_confidence
        )
        
        with self._lock:
            # Check if we need to evict
            self._evict_oldest()
            
            # Store entry
            self._cache[cache_key] = CacheEntry(
                data=result,
                timestamp=time.time()
            )
            self._access_times[cache_key] = time.time()
            
            logger.debug(
                f"[CACHE] MISS - Query: '{self._normalize_query(query)}' "
                f"(caching {len(result)} results, TTL: {self.ttl_seconds}s)"
            )
    
    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._access_times.clear()
            logger.info(f"[CACHE] Cleared {count} entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats including hit rate, size, etc.
        """
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                "hits": self.hits,
                "misses": self.misses,
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
                "cached_entries": len(self._cache),
                "max_entries": self.max_entries,
                "ttl_seconds": self.ttl_seconds,
            }
    
    def reset_stats(self) -> None:
        """Reset hit/miss counters."""
        with self._lock:
            self.hits = 0
            self.misses = 0
            logger.info("[CACHE] Statistics reset")


# Global cache instance - initialized on module import
# TTL: 10 minutes, Max: 1000 entries
search_cache = SimpleCache(ttl_seconds=600, max_entries=1000)
