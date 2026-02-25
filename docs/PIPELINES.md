# Pipelines

Referência de todos os scripts em `backend/pipelines/`, organizados por tema.

---

## Pré-requisitos

1. Venv ativado e dependências instaladas (`pip install -r requirements.txt`)
2. Arquivo `.env` na raiz do projeto (copie de `.env.example` e preencha)
3. Todos os comandos executados a partir da **raiz do projeto** (`nerdcastfinder/`)

---

## Ingest — `backend/pipelines/ingest/`

### `download.py` — Baixar episódios via RSS

Baixa arquivos de áudio de um feed RSS para `backend/data/podcasts/<podcast>/`.
Idempotente: pula arquivos já baixados.

```powershell
# Ver podcasts disponíveis
python -m backend.pipelines.ingest.download --list

# Baixar todos os episódios de um podcast
python -m backend.pipelines.ingest.download --podcast nerdcast

# Baixar apenas os 10 mais recentes
python -m backend.pipelines.ingest.download --podcast nerdcast --limit 10

# Baixar todos os podcasts configurados
python -m backend.pipelines.ingest.download --all
```

---

### `ingest.py` — Transcrever e indexar episódios

Transcreve áudio (Whisper), gera embeddings e salva no banco + índice FAISS.
Idempotente: reprocessa o episódio se já existir no banco.

```powershell
# Ver podcasts disponíveis
python -m backend.pipelines.ingest.ingest --list

# Ingerir todos os episódios de um podcast
python -m backend.pipelines.ingest.ingest --podcast nerdcast

# Retomar a partir de um episódio específico
python -m backend.pipelines.ingest.ingest --podcast nerdcast --resume-from nerdcast_950

# Ingerir todos os podcasts configurados
python -m backend.pipelines.ingest.ingest --all
```

---

## Index — `backend/pipelines/index/`

### `rebuild_index.py` — Reconstruir índice FAISS

Reconstrói o `podcasts.index` e `embedding_id_mapping.npy` a partir dos embeddings
já armazenados no banco. Use após:
- Adicionar novos segmentos sem rebuild automático
- Trocar o modelo de embeddings
- Corrupção do índice

```powershell
python -m backend.pipelines.index.rebuild_index
```

---

## DB — `backend/pipelines/db/`

Scripts de migração do banco SQLite. Devem ser rodados **uma única vez** em ordem
cronológica quando necessário.

### `migrate_db.py` — Adicionar colunas à tabela de episódios

```powershell
python -m backend.pipelines.db.migrate_db
```

### `migrate_to_multi_podcast.py` — Migrar para estrutura multi-podcast

Renomeia tabelas (`nerdcast_*` → `podcast_*`) e adiciona coluna `podcast_source`.

```powershell
python -m backend.pipelines.db.migrate_to_multi_podcast

# Reverter (restaura backup criado automaticamente)
python -m backend.pipelines.db.migrate_to_multi_podcast --rollback
```

### `add_program_name_field.py` — Adicionar campo `program_name`

Adiciona e popula `program_name` na tabela `podcast_episodes` com base no título.

```powershell
# Simular sem aplicar
python -m backend.pipelines.db.add_program_name_field --dry-run

# Aplicar
python -m backend.pipelines.db.add_program_name_field
```

### `update_metadata.py` — Atualizar metadados faltantes

Busca `summary` e `image_url` faltantes a partir do RSS feed.

```powershell
python -m backend.pipelines.db.update_metadata
```

---

## Deploy — `backend/pipelines/deploy/`

Requerem variáveis de ambiente configuradas no `.env` (veja `.env.example`).

### `upload_to_gcs.py` — Enviar dados ao GCS

Faz checkpoint do WAL do SQLite antes de enviar (garante DB consistente).

```powershell
# Enviar DB + índice + mapping, depois fazer redeploy
python -m backend.pipelines.deploy.upload_to_gcs --deploy

# Enviar apenas o DB (ex: após corrigir metadados)
python -m backend.pipelines.deploy.upload_to_gcs --db-only

# Enviar apenas o índice FAISS + mapping (ex: após rebuild_index)
python -m backend.pipelines.deploy.upload_to_gcs --index-only

# Enviar tudo sem redeploy
python -m backend.pipelines.deploy.upload_to_gcs
```

---

### `build_and_deploy.py` — Build e deploy no Cloud Run

Constrói a imagem Docker com Cloud Build e faz deploy no Cloud Run.

```powershell
# Build + deploy completo
python -m backend.pipelines.deploy.build_and_deploy

# Apenas build (sem deploy)
python -m backend.pipelines.deploy.build_and_deploy --build-only

# Apenas redeploy (reutiliza imagem existente)
python -m backend.pipelines.deploy.build_and_deploy --deploy-only
```

---

## Fluxos comuns

### Adicionar novos episódios ao ar (sem rebuild da imagem)

```powershell
# 1. Baixar novos episódios
python -m backend.pipelines.ingest.download --podcast nerdcast

# 2. Transcrever e indexar
python -m backend.pipelines.ingest.ingest --podcast nerdcast

# 3. Enviar DB + índice ao GCS e redesenhar Cloud Run
python -m backend.pipelines.deploy.upload_to_gcs --deploy
```

### Deploy inicial (primeira vez)

```powershell
# 1. Baixar episódios
python -m backend.pipelines.ingest.download --all

# 2. Ingerir
python -m backend.pipelines.ingest.ingest --all

# 3. Build da imagem + deploy
python -m backend.pipelines.deploy.build_and_deploy

# 4. Enviar dados ao GCS
python -m backend.pipelines.deploy.upload_to_gcs
```

### Atualizar código (sem novos dados)

```powershell
python -m backend.pipelines.deploy.build_and_deploy
```

### Atualizar apenas dados (sem rebuild da imagem)

```powershell
python -m backend.pipelines.deploy.upload_to_gcs --deploy
```
