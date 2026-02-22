## 🚀 CACHE IMPLEMENTATION - TECHNICAL REFERENCE

---

### **ARQUITETURA GERAL**

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT REQUEST                        │
│              GET /search?q=inteligência                  │
└──────────────────────────┬────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    API ROUTE                             │
│         @router.get("/search", response_model=...)      │
│                  (search.py)                             │
└──────────────────────────┬────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                SEARCH SERVICE                            │
│            SearchService.search()                        │
│         (services/search_service.py)                     │
└──────┬───────────────────────────┬──────────────────────┘
       │                           │
       ▼                           ▼
┌─────────────────┐      ┌──────────────────────────┐
│   CACHE CHECK   │      │   FAISS SEARCH (MISS)   │
│  cache.get()    │      │  + Database lookups     │
└────────┬────────┘      │  + Formatting results   │
         │               └───────────┬──────────────┘
    HIT │ MISS                      │
    ─┬─ │ ─────┬─────────────────────┘
     │  │      │
    [✓]│    cache.set()
     │  │      │
     │  ▼      ▼
     │  ┌──────────────────────────────┐
     │  │  CACHE STORAGE               │
     │  │  SimpleCache._cache[key]     │
     │  │  CacheEntry(data, timestamp) │
     └─►└───────────┬──────────────────┘
                    │
                    ▼
            ┌───────────────────┐
            │  RETURN RESULTS   │
            │  ~1ms (HIT) OR    │
            │  ~1000ms (MISS)   │
            └───────────────────┘
```

---

### **COMPONENTES PRINCIPAIS**

#### **1. SimpleCache (backend/app/core/cache.py)**

```python
class SimpleCache:
    def __init__(self, ttl_seconds: int = 600, max_entries: int = 1000):
        """Initialize cache with 10 minute TTL, max 1000 entries"""
        
    def get(...) -> Optional[List[Dict]]:
        """Retrieve result if hit and not expired"""
        
    def set(...) -> None:
        """Store result in cache"""
        
    def clear() -> None:
        """Remove all entries"""
        
    def get_stats() -> Dict:
        """Return {hits, misses, total_requests, hit_rate_percent, ...}"""
        
    def reset_stats() -> None:
        """Reset hit/miss counters"""
```

**Thread-Safety**: `threading.Lock` protege `_cache` e `_access_times`

**Normalização**: Query normalizada com `.lower().strip()` + MD5 hash

**TTL Check**: Verifica `time.time() - entry.timestamp > ttl` ao acessar

**LRU Eviction**: Remove entrada menos recentemente usada quando `len(_cache) >= max_entries`

---

#### **2. CacheEntry (dataclass)**

```python
@dataclass
class CacheEntry:
    data: Any          # O resultado cacheado (List[Dict])
    timestamp: float   # time.time() quando foi criado
    
    def is_expired(self, ttl: int) -> bool:
        return (time.time() - self.timestamp) > ttl
```

---

#### **3. Integração (search_service.py)**

```python
def search(...) -> List[Dict]:
    # 1. CHECK CACHE (antes de processar)
    cached_result = search_cache.get(
        query=query,
        top_k=top_k,
        podcast_source=podcast_source,
        program_name=program_name,
        min_confidence=min_confidence
    )
    
    if cached_result is not None:
        return cached_result  # ✓ HIT
    
    # 2. CACHE MISS - executar busca normal
    # ... FAISS search, database lookups, formatting ...
    
    # 3. STORE RESULT
    search_cache.set(
        query=query,
        result=results,
        top_k=top_k,
        podcast_source=podcast_source,
        program_name=program_name,
        min_confidence=min_confidence
    )
    
    return results
```

---

#### **4. API Endpoints (search.py)**

| Endpoint | Método | Descrição | Exemplo |
|----------|--------|-----------|---------|
| `/search` | GET | Busca semântica (cacheada automaticamente) | `?q=python&top_k=10` |
| `/cache/stats` | GET | Ver estatísticas (hits/misses/rate) | `curl http://localhost:8005/api/cache/stats` |
| `/cache/clear` | POST | Limpar todas as entradas | `curl -X POST http://localhost:8005/api/cache/clear` |
| `/cache/reset-stats` | POST | Resetar contadores | `curl -X POST http://localhost:8005/api/cache/reset-stats` |

---

### **CACHE KEY GENERATION**

```python
def _make_cache_key(query, top_k, podcast_source, program_name, min_confidence):
    # 1. Normaliza query
    normalized_query = query.lower().strip()
    
    # 2. Constrói tuple com todos os parâmetros
    key_parts = (
        normalized_query,
        str(top_k or ""),
        str(podcast_source or ""),
        str(program_name or ""),
        str(min_confidence or ""),
    )
    
    # 3. Junta e faz hash MD5
    key_string = "|".join(key_parts)
    cache_key = md5(key_string.encode()).hexdigest()
    
    return cache_key  # "abc123def456..." (32 chars)
```

**Exemplo:**
```
Query: "PYTHON"
Top K: 10
Podcast: "nerdcast"
Program: None
Confidence: None

Normalized: "python|10|nerdcast||"
Hash: "7d8f2c3a4b1e9f5c8d2a6e1b4f9c3e7a"
```

---

### **HIT/MISS BEHAVIOR**

#### **CACHE HIT**
```
Query: "python" + top_k=10
├─ _make_cache_key() → "abc123..."
├─ Procura em _cache["abc123..."]
├─ Encontra CacheEntry
├─ Verifica: time.time() - entry.timestamp ≤ 600
├─ ✓ NÃO EXPIROU
├─ Atualiza _access_times["abc123..."] = time.time() (LRU)
├─ hits += 1
└─ Retorna entry.data

Tempo: ~1 ms
Log: [CACHE] HIT - Query: 'python' (expires in 595.1s)
```

#### **CACHE MISS - ENTRADA NÃO EXISTE**
```
Query: "java" + top_k=5
├─ _make_cache_key() → "def456..."
├─ Procura em _cache["def456..."]
├─ Não encontra
├─ misses += 1
└─ Retorna None

Tempo: ~0.1 ms
Log: [CACHE] MISS - Query 'java'
```

#### **CACHE MISS - ENTRADA EXPIRADA**
```
Query: "golang" + top_k=10
├─ _make_cache_key() → "ghi789..."
├─ Procura em _cache["ghi789..."]
├─ Encontra CacheEntry
├─ Verifica: time.time() - entry.timestamp > 600
├─ ✓ EXPIROU (cacheado há 610 segundos)
├─ Del _cache["ghi789..."]
├─ Del _access_times["ghi789..."]
├─ misses += 1
└─ Retorna None

Tempo: ~1 ms
Log: [CACHE] Expired entry removed for query: 'golang'
```

---

### **THREAD-SAFETY**

```python
self._lock = threading.Lock()

# TODA operação de leitura/escrita usa:
with self._lock:
    # Operação atômica em _cache, _access_times
    # Múltiplas threads ficam em fila, uma executa por vez
    
# Exemplo:
with self._lock:
    if cache_key not in self._cache:
        self.misses += 1
        return None
    
    entry = self._cache[cache_key]  # ✓ Thread-safe
    if entry.is_expired(self.ttl_seconds):
        del self._cache[cache_key]  # ✓ Thread-safe
        
    self.hits += 1  # ✓ Atomic counter
```

---

### **LRU EVICTION**

```python
if len(self._cache) >= self.max_entries:  # Default: 1000
    # Encontra entrada menos recentemente acessada
    oldest_key = min(
        (k for k in self._cache.keys()),
        key=lambda k: self._access_times[k]
    )
    
    # Remove
    del self._cache[oldest_key]
    del self._access_times[oldest_key]
    
    # LOG: [CACHE] LRU eviction: removed oldest entry
```

---

### **PERFORMANCE ANALYSIS**

#### **Latência**

| Operação | Tempo | Detalhe |
|----------|-------|---------|
| CACHE HIT | ~1 ms | Dict lookup + timestamp check |
| CACHE MISS (não existe) | ~0.1 ms | Dict lookup falha |
| MISS (gerado embedding + FAISS) | ~500-2000 ms | Depende do índice |
| Speedup com cache | 500-2000x | Com 95% hit rate |

#### **Memória**

| Componente | Tamanho | Nota |
|-----------|---------|------|
| CacheEntry | ~1-10 KB | Lista de 20 resultados |
| _cache dict | Até 1000 entradas | ~10-100 MB total |
| _access_times | Até 1000 floats | ~8 KB |
| _lock | ~1 KB | Threading overhead |

#### **Exemplo Real: 100 requisições**

```
Sem cache:
100 × 1000ms = 100 segundos
CPU: 100% × 100s = máximo possível

Com cache (95% hit rate):
1 MISS (1000ms) + 99 HIT (1ms) = ~1100ms total
Speedup: 91x MAIS RÁPIDO
CPU: Reduzido em 99%
```

---

### **CONFIGURAÇÃO**

**Em backend/app/core/cache.py (última linha):**

```python
# Default (atual)
search_cache = SimpleCache(ttl_seconds=600, max_entries=1000)

# Mais agressivo (10 minutos, 5000 entradas)
search_cache = SimpleCache(ttl_seconds=600, max_entries=5000)

# Mais conservador (5 minutos, 500 entradas)
search_cache = SimpleCache(ttl_seconds=300, max_entries=500)

# Muito longo (30 minutos, 2000 entradas)
search_cache = SimpleCache(ttl_seconds=1800, max_entries=2000)
```

**Recomendações:**
- TTL curto (300s) = dados sempre frescos, hit rate baixo
- TTL longo (1800s) = hit rate alto, dados podem estar velhos
- max_entries pequeno (500) = memória baixa, evictions mais frequentes
- max_entries grande (5000) = memória alta, evictions raras

---

### **LOGS**

```
[CACHE] HIT - Query: 'inteligência artificial' (expires in 595.3s)
[CACHE] MISS - Query: 'podcast' (caching 15 results, TTL: 600s)
[CACHE] Expired entry removed for query: 'old query'
[CACHE] LRU eviction: removed oldest entry
[CACHE] Cleared 42 entries
[CACHE] Statistics reset
```

---

### **TESTING**

```bash
# Rodeia suite completa
python test_cache.py

# Tests incluem:
# 1. Basic Hit/Miss behavior (timing verification)
# 2. Different parameters (top_k, feed, program, min_confidence)
# 3. Query normalization (case-insensitive)
# 4. Management endpoints (clear, reset, stats)

# Esperado: ✅ ALL TESTS PASSED!
```

---

### **FILES**

| Arquivo | Linhas | Descrição |
|---------|--------|-----------|
| `backend/app/core/cache.py` | 280+ | Implementação SimpleCache |
| `backend/app/services/search_service.py` | 183+ | Integração no search |
| `backend/app/api/search.py` | 135+ | Endpoints de cache |
| `test_cache.py` | 241 | Suite de testes |
| `CACHE_DOCUMENTATION.md` | 300+ | Doc completa com exemplos |
| `CACHE_IMPLEMENTATION_SUMMARY.md` | 250+ | Summary executivo |
| `CACHE_QUICKSTART.md` | 150+ | Quick reference |

---

### **DEPLOYMENT CHECKLIST**

- ✅ Zero dependências externas (stdlib only)
- ✅ Thread-safe (múltiplas requisições simultâneas)
- ✅ Memory-safe (LRU eviction automático)
- ✅ Tipo-completo (type hints em tudo)
- ✅ Bem-documentado (comments detalhados)
- ✅ Loggado (eventos claros)
- ✅ Testado (suite abrangente)
- ✅ Production-ready (MVP completo)

**Pronto para deploy!** 🚀

---

### **TROUBLESHOOTING**

**Q: Como saber se cache está funcionando?**  
A: `curl http://localhost:8005/api/cache/stats` → veja hit_rate_percent

**Q: Como forçar refresh de cache?**  
A: `curl -X POST http://localhost:8005/api/cache/clear`

**Q: Como resetar contadores?**  
A: `curl -X POST http://localhost:8005/api/cache/reset-stats`

**Q: Resultado do cache está desatualizado?**  
A: Reduzir TTL (default 600s) ou fazer clear manual

**Q: Hit rate muito baixo?**  
A: Aumentar TTL e max_entries
