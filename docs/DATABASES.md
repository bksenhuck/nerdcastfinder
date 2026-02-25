**Resumo dos Bancos e Dados**

Este documento descreve os arquivos de dados e bancos presentes no workspace, com localização, esquema básico e contagens encontradas localmente.

**SQLite (metadados)**:
- Path: `backend/data/podcast_database.db`
- Objetos (tabelas e índices):
  - Tabela `podcast_episodes`
    - Colunas (resumidas): `id`, `filename`, `title_original`, `published_date`, `duration_seconds`, `file_size_mb`, `audio_url`, `status`, `created_at`, `updated_at`, `downloaded_at`, `summary`, `image_url`, `podcast_source`, `program_name`
    - Uso: armazena metadados de episódios (um registro por episódio). `podcast_source` e `program_name` suportam multi-podcast.
  - Tabela `podcast_segments`
    - Colunas (resumidas): `id`, `episode` (arquivo/filename referenciado), `content` (texto do segmento), `embedding_id`, `embedding` (blob numpy), `podcast_source`
    - Uso: segmentos/textos gerados a partir do episódio com embeddings (armazenados como bytes).
  - Índices relevantes:
    - `ix_nerdcast_episodes_filename` (unique index em `podcast_episodes.filename`)
    - `ix_nerdcast_segments_embedding_id` (unique index em `podcast_segments.embedding_id`)
    - `ix_nerdcast_segments_episode` (index em `podcast_segments.episode`)
- Contagens (local):
  - `podcast_episodes`: 1686 registros
  - `podcast_segments`: 41162 registros

Observações:
- Arquivo do DB (SQLite) tem WAL/SHM (`podcast_database.db-wal`, `podcast_database.db-shm`) enquanto o banco está em uso.
- Antes de alterar esquema em produção, faça backup: copie `backend/data/podcast_database.db` para outro local.

**FAISS (índice vetorial)**:
- Diretório: `backend/data/faiss_index/`
- Arquivos:
  - `nerdcast.index` — arquivo do índice FAISS.
  - `embedding_id_mapping.npy` — array numpy que mapeia posições do FAISS para `embedding_id` do DB.
- Informações locais:
  - `index.ntotal`: 41162 vetores
  - dimensão do índice (d): 768
  - `embedding_id_mapping.npy` length: 41162

Observações:
- O index é carregado por `SearchService` em `backend/app/services/search_service.py` (ver logs de inicialização).
- Para (re)construir o índice use o script: `python -m backend.pipelines.rebuild_index`.

**Arquivos de áudio / Podcasts**:
- Diretório: `backend/data/podcasts/`
- Feeds detectados (local):
  - `nerdcast` — 1686 arquivos `.mp3` (corresponde aproximadamente ao número de episódios na DB)
- Uso: os MP3s são a fonte dos quais o pipeline faz transcrição e segmentação.

**Scripts úteis e pipelines**:
- Rebuild FAISS: `python -m backend.pipelines.rebuild_index` (script: `backend/pipelines/rebuild_index.py`).
- Ingest (download + transcrição + index): `python -m backend.pipelines.ingest` (script: `backend/pipelines/ingest.py`).
- Atualizar metadata (summary/image): `python -m backend.pipelines.update_metadata` (script: `backend/pipelines/update_metadata.py`).

**Recomendações e ações comuns**:
- Backup: copie `backend/data/podcast_database.db` antes de alterações de esquema.
- Rebuild index: pare o backend (para evitar arquivos lockados), rode `python -m backend.pipelines.rebuild_index`, e então reinicie o backend.
- Em caso de mistura de dimensões de embedding (várias versões do modelo): o rebuild irá detectar dimensões e pular embeddings com dimensão diferente — ver logs do script para detalhes sobre `skipped_wrong_dim` e `skipped_no_emb`.

**Onde olhar no código**:
- Modelos ORM: `backend/app/db/models.py` (define `PodcastEpisode` e `PodcastSegment`).
- Sessão/URL DB: `backend/app/db/session.py` e `backend/app/core/config.py` (`get_database_path()` / `get_database_url()`).
- SearchService: `backend/app/services/search_service.py` (leitura do índice FAISS, mapeamento e montagem dos resultados).
- Pipelines: `backend/pipelines/` (contêm `ingest.py`, `rebuild_index.py`, `download.py`, `update_metadata.py`).

Se quiser, eu posso:
- adicionar um script de `backfill` para popular uma nova coluna `author` (se decidirmos estender o esquema),
- ou gerar um relatório CSV com contagens por programa/ano por consulta SQL.

---
Arquivo gerado automaticamente com análise local do workspace.
