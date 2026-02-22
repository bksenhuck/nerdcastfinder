# Sistema de Cache - Documentação

## Visão Geral

Sistema de cache em memória para resultados de busca semântica, implementado com thread-safety, TTL configurável e zero dependências externas (apenas stdlib).

## Arquitetura

```
API Route (/search)
    ↓
SearchService.search()
    ↓
cache.get() ← Verifica cache
    ↓
[HIT] → Retorna resultado cacheado
[MISS] → Executa busca FAISS
            ↓
        cache.set() ← Armazena resultado
            ↓
        Retorna resultado
```

## Características

### 1. **Normalização de Query**
- Lowercase: `"CHINA"` → `"china"`
- Trim whitespace: `" china "` → `"china"`
- Hash MD5 da chave para mantê-la pequena

### 2. **TTL (Time To Live)**
- Padrão: 10 minutos (600 segundos)
- Configurável na inicialização
- Verificação automática de expiração ao acessar

### 3. **Thread-Safe**
- Usa `threading.Lock` para sincronização
- Múltiplas requisições simultâneas funcionam corretamente
- Sem race conditions

### 4. **LRU Eviction**
- Máximo de 1000 entradas por padrão
- Remove entrada menos recentemente usada quando cheio
- Rastreamento de tempo de acesso

### 5. **Estatísticas**
- Conta hits e misses
- Calcula hit rate (%)
- Monitora tamanho do cache

## Uso

### No Código Backend

```python
from backend.app.core.cache import search_cache

# O cache é automático na SearchService
# Nada precisa ser feito - a integração é transparente

# Mas você pode acessar manualmente se precisar:
result = search_cache.get(
    query="china",
    top_k=10,
    podcast_source="nerdcast",
    program_name="Nerdcast",
    min_confidence=0.5
)

if result is not None:
    return result  # Cache hit
else:
    # Executar busca e cachear
    result = do_search()  # Sua lógica de busca
    search_cache.set(
        query="china",
        result=result,
        top_k=10,
        ...
    )
    return result
```

### Via API REST

#### 1. **Ver Estatísticas de Cache**
```bash
curl http://localhost:8005/api/cache/stats

# Resposta:
{
  "hits": 42,
  "misses": 15,
  "total_requests": 57,
  "hit_rate_percent": 73.68,
  "cached_entries": 12,
  "max_entries": 1000,
  "ttl_seconds": 600
}
```

#### 2. **Limpar Cache**
```bash
curl -X POST http://localhost:8005/api/cache/clear

# Resposta:
{
  "message": "Cache limpo com sucesso",
  "status": "success"
}
```

#### 3. **Resetar Estatísticas**
```bash
curl -X POST http://localhost:8005/api/cache/reset-stats

# Resposta:
{
  "message": "Estatísticas de cache resetadas",
  "status": "success"
}
```

#### 4. **Fazer Busca (Automáticamente Cacheada)**
```bash
# Primeira requisição - MISS, processa busca
curl "http://localhost:8005/api/search?q=china&top_k=10"

# Segunda requisição idêntica - HIT, retorna do cache
curl "http://localhost:8005/api/search?q=china&top_k=10"
```

## Configuração

### Alterar TTL e Limite de Entradas

Em `backend/app/core/cache.py`, linha final:

```python
# Padrão: 10 minutos, 1000 entradas
search_cache = SimpleCache(ttl_seconds=600, max_entries=1000)

# Customizar:
search_cache = SimpleCache(ttl_seconds=1800, max_entries=5000)  # 30 min, 5000 entradas
```

## Logs

O cache gera logs informativos:

```
[CACHE] HIT - Query: 'china' (expires in 595.3s)
[CACHE] MISS - Query: 'inteligência artificial' (caching 15 results, TTL: 600s)
[CACHE] Expired entry removed for query: 'old query'
[CACHE] LRU eviction: removed oldest entry
```

## Performance

### Benefícios

- **Reduz latência**: HIT = ~1ms vs MISS = ~500ms-2s (dependendo do índice)
- **Reduz CPU**: Evita re-embedding da query
- **Reduz I/O**: Evita acesso desnecessário ao FAISS

### Exemplo de Melhoria

Sem cache:
```
100 requisições idênticas = 100 × 1000ms = 100s
```

Com cache (90% hit rate):
```
1 MISS (1000ms) + 99 HIT (1ms) = ~1100ms total
Speedup: 91x faster!
```

## Casos de Uso

### Quando Cache Ajuda

✅ Buscas repetidas do mesmo usuário
✅ Trends (queries populares do dia)
✅ Buscas de usuários diferentes com mesma query
✅ Período de pico (economia de CPU)

### Quando Cache Não Ajuda Muito

❌ Cada usuário faz busca única
❌ Índice muda frequentemente (ingestão ativa)
❌ Precisão é crítica (cache pode estar expirado)

## Manutenção

### Limpar Cache Periodicamente

```python
# Via script
from backend.app.core.cache import search_cache

search_cache.clear()  # Remove tudo
search_cache.reset_stats()  # Reseta contadores
```

### Monitorar Saúde

Verifique o endpoint `/api/cache/stats` regularmente:

```bash
# Hit rate baixa? Aumentar TTL ou max_entries
# Hit rate alta? Cache está funcionando bem

# Muitas entradas? Aumentar max_entries ou reduzir TTL
```

## Garantias

✅ **Thread-safe**: Múltiplas threads acessando simultaneamente  
✅ **Memory-safe**: LRU eviction evita crescimento ilimitado  
✅ **API-safe**: Não muda assinatura das funções existentes  
✅ **Typed**: Type hints em toda interface  
✅ **Tested**: Logs detalhadosPermitem debugging fácil  

## Implementação Interna

### Classe `CacheEntry`
```python
@dataclass
class CacheEntry:
    data: Any                    # O resultado cacheado
    timestamp: float             # Quando foi cacheado
    
    def is_expired(self, ttl):  # Verifica se expirou
        return (time.time() - self.timestamp) > ttl
```

### Classe `SimpleCache`
```python
class SimpleCache:
    _cache: Dict[str, CacheEntry]      # Armazena dados
    _access_times: Dict[str, float]    # Rastreia LRU
    _lock: threading.Lock              # Sincronização
    hits: int                          # Contador
    misses: int                        # Contador
```

## Futuros Melhoramentos

💡 Persistência (Redis, Memcached)  
💡 Cache distribuído para multi-process  
💡 Políticas de eviction customizáveis  
💡 Compressão de resultados grandes  
💡 Analytics dashboard de cache hits  
