# Scripts de Manutenção e Utilidades

Esta pasta contém scripts utilitários para manutenção do banco de dados e atualização de metadados.

## Scripts Disponíveis

### 1. `migrate_db.py`
**Propósito:** Migração de schema do banco de dados

**Quando usar:**
- Adicionar novas colunas às tabelas existentes
- Modificar estrutura do banco sem perder dados
- Após atualizar models no código

**Colunas que adiciona:**
- `downloaded_at` - Data/hora de download do episódio
- `summary` - Resumo do episódio do RSS
- `image_url` - URL da capa do episódio

**Como executar:**
```bash
python scripts/migrate_db.py
```

**Resultado:**
- ✅ Adiciona apenas colunas que não existem
- ✅ Não modifica dados existentes
- ✅ Idempotente (pode rodar múltiplas vezes)

---

### 2. `update_all_metadata.py`
**Propósito:** Atualizar TODOS os metadados do feed RSS

**Quando usar:**
- Primeira população do banco de dados
- Repopular metadados após corrupção
- Atualizar em massa após mudanças no feed

**O que faz:**
- Busca feed RSS completo (todos os episódios)
- Extrai: título, data, duração, tamanho, imagem, resumo
- Salva/atualiza TODOS os episódios

**Como executar:**
```bash
python scripts/update_all_metadata.py
```

**Aviso:** 
⚠️ Processa TODOS os episódios do feed (pode demorar)
⚠️ Sobrescreve metadados existentes

---

### 3. `update_missing_metadata.py`
**Propósito:** Preencher apenas metadados FALTANTES

**Quando usar:**
- Correção pontual de episódios sem summary ou image_url
- Após adicionar novas colunas (complementa `migrate_db.py`)
- Atualização incremental sem sobrescrever dados existentes

**O que faz:**
- Busca episódios com `summary IS NULL` ou `image_url IS NULL`
- Preenche apenas os campos faltantes do RSS
- Preserva metadados já existentes

**Como executar:**
```bash
python scripts/update_missing_metadata.py
```

**Resultado:**
- ✅ Atualiza apenas episódios com dados faltantes
- ✅ Não sobrescreve metadados existentes
- ✅ Mais rápido que `update_all_metadata.py`

---

## Fluxo de Uso Típico

### Primeira vez (setup inicial):
1. `python scripts/migrate_db.py` - Garante que banco tem todas as colunas
2. `python scripts/update_all_metadata.py` - Popula todos os metadados

### Adicionar nova coluna:
1. Modificar model em `backend/app/models/`
2. `python scripts/migrate_db.py` - Adiciona coluna
3. `python scripts/update_missing_metadata.py` - Preenche dados

### Corrigir dados faltantes:
1. `python scripts/update_missing_metadata.py` - Preenche lacunas

---

## Observações

- Todos os scripts são **idempotentes** (seguros para rodar múltiplas vezes)
- Usam logging colorido para feedback visual
- Trabalham com o banco configurado em `backend/app/config/settings.py`
- Podem ser executados em qualquer ordem (mas recomenda-se a ordem acima)
