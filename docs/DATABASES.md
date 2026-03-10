# Bancos de Dados e Dados do Pipeline

> Última atualização: 2026-03-06

Este documento descreve o estado atual dos dados e bancos presentes no projeto, com esquema, contagens reais e observações sobre tamanho e crescimento.

---

## SQLite — `backend/data/podcast_database.db`

Banco principal da aplicação. Usado pelo frontend, API, scripts de pipeline e monitoramento.

**Tamanho atual:** ~110 MB (WAL incluído)

### Tabela `podcast_episodes`

Metadados de cada episódio (um registro por episódio).

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PK | Chave primária autoincrement |
| `podcast_source` | VARCHAR(100) | Identificador do podcast (`nerdcast`, `pelada_na_net`, …) |
| `stable_id` | TEXT | ID estável derivado do número do episódio (ex: `nerdcast_454`) |
| `program_name` | VARCHAR(100) | Sub-programa dentro do feed (ex: `Nerdcast`, `Emprecast`) |
| `filename` | VARCHAR(255) | Nome do arquivo MP3 — chave única |
| `title_original` | VARCHAR(500) | Título original do RSS |
| `summary` | TEXT | Descrição/resumo do RSS |
| `image_url` | TEXT | URL da capa do episódio |
| `published_date` | DATETIME | Data de publicação |
| `duration_seconds` | INTEGER | Duração em segundos |
| `file_size_mb` | FLOAT | Tamanho do MP3 em MB |
| `audio_url` | TEXT | URL do áudio no feed RSS |
| `status` | VARCHAR(50) | Status do episódio (`downloaded`) |
| `created_at` / `updated_at` / `downloaded_at` | DATETIME | Timestamps |

**Contagens atuais:**

| Podcast | Episódios | Intervalo de datas |
|---|---|---|
| `nerdcast` | 1.686 | 2006-04-02 → 2026-02-13 |
| `pelada_na_net` | 765 | 2012-01-27 → 2026-02-23 |
| **Total** | **2.451** | |

---

### Tabela `podcast_segments`

Segmentos de texto gerados pela transcrição (Whisper) de cada episódio. É a maior tabela do banco — contém o texto transcrito na coluna `content`.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PK | Chave primária autoincrement |
| `podcast_source` | VARCHAR(100) | Identificador do podcast |
| `stable_id` | TEXT | Mesmo `stable_id` do episódio correspondente |
| `episode` | VARCHAR(500) | Filename do episódio (campo legado, usado como fallback) |
| `content` | TEXT | Texto transcrito do segmento (~720 chars médios) |
| `embedding_id` | INTEGER | ID único que mapeia para a posição no índice FAISS |

**Contagens atuais:**

| Podcast | Segmentos | Média de chars/seg | Tamanho estimado do content |
|---|---|---|---|
| `nerdcast` | 61.541 | ~713 chars | ~43 MB |
| `pelada_na_net` | 33.932 | ~741 chars | ~25 MB |
| **Total** | **95.473** | ~723 chars | **~66 MB** |

> A coluna `content` representa ~60% do tamanho total do arquivo `.db`. O restante são índices, metadados e overhead do SQLite.

---

## FAISS — `backend/data/faiss_index/`

Índice vetorial para busca semântica. **Não cresce de forma crítica** — cada vetor ocupa espaço fixo (dimensão × 4 bytes).

| Arquivo | Descrição |
|---|---|
| `podcasts.index` | Índice FAISS consolidado (todos os podcasts) |
| `embedding_id_mapping.npy` | Array numpy: posição no FAISS → `embedding_id` do DB |

**Estado atual:**
- Vetores indexados: ~95.473
- Dimensão dos vetores: 768 (modelo `intfloat/multilingual-e5-base`)
- Tamanho estimado do índice: ~280 MB em memória, muito menor em disco (FlatL2)

---

## Arquivos de Áudio — `backend/data/podcasts/`

MP3s baixados pelo pipeline. São a fonte para transcrição e **não são enviados para o GCS nem para produção**.

| Podcast | Arquivos MP3 |
|---|---|
| `nerdcast` | ~1.686 |
| `pelada_na_net` | ~765 |

---

## Crescimento estimado por novo podcast

Com base nos dados atuais (média de ~56 segs/episódio × ~725 chars):

| Escala do podcast | Episódios | Segmentos estimados | Crescimento no DB |
|---|---|---|---|
| Pequeno (< 100 eps) | 100 | ~5.600 | +4 MB |
| Médio (100-500 eps) | 300 | ~16.800 | +12 MB |
| Grande (500+ eps) | 800 | ~44.800 | +32 MB |

> Com 5-6 podcasts de escala média/grande, o banco pode chegar a **300-500 MB**.

---

## Qualidade dos dados

| Verificação | Resultado |
|---|---|
| Episódios sem `stable_id` | ✅ 0 (todos preenchidos) |
| Segmentos sem `stable_id` | ✅ 0 (todos preenchidos) |
| Segmentos órfãos (sem episódio correspondente) | ✅ 0 |
| Episódios sem segmentos | Esperado para eps ainda não transcritos |

---

## Onde olhar no código

| Componente | Caminho |
|---|---|
| Modelos ORM | `backend/app/db/models.py` |
| Sessão / URL do banco | `backend/app/db/session.py`, `backend/app/core/config.py` |
| `get_stable_id()` | `backend/app/utils/path_utils.py` |
| Pipeline de ingest | `backend/pipelines/ingest/ingest.py` |
| Pipeline de download | `backend/pipelines/ingest/download.py` |
| Serviço de busca (FAISS) | `backend/app/services/search_service.py` |
| Script de monitoramento | `scripts/monitoring/check_pipeline_status.py` |
| Migração de `stable_id` | `scripts/db/migrate_to_stable_id.py` |

---

## Operações comuns

```bash
# Ver status do pipeline por episódio
python scripts/monitoring/check_pipeline_status.py

# Migrar stable_id em registros antigos
python scripts/db/migrate_to_stable_id.py

# Inspecionar o banco diretamente
python scripts/db/db_inspect.py

# Backup antes de alterações de esquema
cp backend/data/podcast_database.db backend/data/podcast_database.db.bak
```
