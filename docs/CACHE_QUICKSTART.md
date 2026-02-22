#!/bin/bash
# Quick Start Guide - Cache Implementation

# ========================================
# OPÇÃO 1: Ver Documentation
# ========================================

# Leia a documentação completa:
cat CACHE_DOCUMENTATION.md

# ========================================
# OPÇÃO 2: Ver Summary
# ========================================

# Leia o resumo executivo:
cat CACHE_IMPLEMENTATION_SUMMARY.md

# ========================================
# OPÇÃO 3: Testar o Cache
# ========================================

# 1. Certifique que backend está rodando:
#    cd infra && .\start.ps1
#    (Or: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8005 --reload)

# 2. Em outro terminal/PowerShell, rode os testes:
python test_cache.py

# Output esperado:
# ============================================================
#   🚀 CACHE TESTING SUITE
# ============================================================
# → Checking if backend is running...
# ✓ Backend is responding
# 
# ============================================================
#   TEST 1: Basic Cache Hit/Miss
# ============================================================
# 
# ✓ SUCCESS: Cache HIT was 1000.5x faster!
# 
# ============================================================
#   TEST 2: Different Parameters = Different Cache Entries
# ============================================================
# 
# ✓ SUCCESS: Different parameters handled correctly!
# 
# ============================================================
#   TEST 3: Query Normalization (Case Insensitive)
# ============================================================
# 
# ✓ SUCCESS: Query normalization working!
# 
# ============================================================
#   TEST 4: Cache Management Endpoints
# ============================================================
# 
# ✓ SUCCESS: Management endpoints working!
# 
# ============================================================
#   ✅ ALL TESTS PASSED!
# ============================================================

# ========================================
# OPÇÃO 4: Usar via cURL
# ========================================

# Fazer uma busca (será cacheada automaticamente):
curl "http://localhost:8005/api/search?q=inteligência&top_k=10"

# Ver estatísticas de cache:
curl "http://localhost:8005/api/cache/stats"

# Limpar cache:
curl -X POST "http://localhost:8005/api/cache/clear"

# Resetar estatísticas:
curl -X POST "http://localhost:8005/api/cache/reset-stats"

# ========================================
# OPÇÃO 5: Usar via Python (dentro do projeto)
# ========================================

# Acessar o cache manualmente (se necessário):
# ---

python << 'EOF'
from backend.app.core.cache import search_cache

# Ver estatísticas
stats = search_cache.get_stats()
print(f"Hit rate: {stats['hit_rate_percent']:.1f}%")
print(f"Cached entries: {stats['cached_entries']}")

# Limpar cache
search_cache.clear()

# Resetar stats
search_cache.reset_stats()
EOF

# ========================================
# OPÇÃO 6: Verificar Cache via Logs
# ========================================

# Quando você faz buscas, vê logs como:
# [CACHE] MISS - Query: 'python' (caching 15 results, TTL: 600s)
# [CACHE] HIT - Query: 'python' (expires in 595.3s)
# [CACHE] Cleared 3 entries
# [CACHE] Statistics reset

# ========================================
# PRÓXIMAS ETAPAS
# ========================================

# 1. Deploy para produção
#    - Cache está pronto (zero deps)
#    - Teste em staging primeiro
#    - Monitor hit rates

# 2. Tuning (opcional)
#    - Aumentar TTL se hit rate baixo
#    - Aumentar max_entries se faltar espaço
#    - Use GET /cache/stats para monitorar

# 3. Integração (futura)
#    - Redis: Para cache distribuído
#    - Memcached: Alternativa leve
#    - Analytics: Dashboard de hit rates

# ========================================
# TROUBLESHOOTING
# ========================================

# Q: Cache não funciona?
# A: Verifique se backend está rodando em localhost:8005
#    curl http://localhost:8005/api/cache/stats

# Q: Hit rate muito baixo?
# A: Aumentar TTL (padrão 600s, tentar 1800s)
#    Ver: CACHE_DOCUMENTATION.md - Configuração

# Q: Cache ocupando muita memória?
# A: Reduzir max_entries ou aumentar LRU eviction
#    Ver: CACHE_DOCUMENTATION.md - LRU Eviction

# Q: Dados no cache estão desatualizados?
# A: Limpar cache: curl -X POST http://localhost:8005/api/cache/clear
#    Ou reduzir TTL para dados mudarem mais rápido

# ========================================
# DOCUMENTAÇÃO REFERÊNCIA
# ========================================

# 📄 CACHE_IMPLEMENTATION_SUMMARY.md
#    - Visão geral da implementação
#    - Requisitos cumpridos
#    - Quick reference

# 📖 CACHE_DOCUMENTATION.md
#    - Documentação técnica completa
#    - Exemplos de uso
#    - API REST endpoints
#    - Performance analysis
#    - Manutenção

# 🧪 test_cache.py
#    - Suite de testes (4 testes)
#    - Run: python test_cache.py
#    - Valida funcionamento completo

# ========================================
# ARQUIVOS DO CACHE
# ========================================

# backend/app/core/cache.py
#   ├─ SimpleCache (classe principal)
#   ├─ CacheEntry (dataclass)
#   └─ search_cache (instância global)

# backend/app/services/search_service.py
#   ├─ Importa cache
#   ├─ cache.get() antes de buscar
#   └─ cache.set() depois de buscar

# backend/app/api/search.py
#   ├─ GET  /cache/stats
#   ├─ POST /cache/clear
#   └─ POST /cache/reset-stats
