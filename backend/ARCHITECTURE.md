# Organização do Código - Nerdcast Finder

## Estrutura de Pastas

### 📁 `app/config/` - Configurações Centralizadas

Contém todas as configurações da aplicação em um único local.

**Arquivo:** `settings.py`

- **Model Configuration**: Nomes dos modelos (Whisper, Embedding)
- **Transcription Settings**: Tamanho de chunks, idioma, verbose
- **Embedding Settings**: Batch size, progress bar
- **Search Settings**: Top-K padrão e máximo, tamanho de excerpts
- **Audio File Settings**: Extensões de arquivo suportadas
- **Path Configuration**: Métodos para obter paths (backend, data, FAISS, database)
- **Database Settings**: Echo, check_same_thread
- **API Settings**: Host, porta, reload, título, descrição
- **CORS Settings**: Origins, credentials, methods, headers

**Benefícios:**
- ✅ Configuração centralizada em um só lugar
- ✅ Fácil de modificar sem mexer no código
- ✅ Paths calculados dinamicamente
- ✅ Singleton pattern com `settings`

---

### 📁 `app/utils/` - Funções Utilitárias

Bibliotecas de funções reutilizáveis isoladas por tema.

#### `text_utils.py` - Processamento de Texto

- `split_text_into_chunks()`: Divide texto em chunks respeitando limites de sentenças
- `truncate_text()`: Trunca texto com sufixo customizável
- `clean_text()`: Remove espaços extras e normaliza

#### `file_utils.py` - Sistema de Arquivos

- `find_audio_files()`: Encontra arquivos de áudio em um diretório
- `get_episode_name()`: Extrai nome do episódio do path
- `ensure_directory_exists()`: Garante que diretório existe

#### `logger.py` - Logging Consistente

- `logger.info()`: Mensagens informativas (ℹ️)
- `logger.success()`: Mensagens de sucesso (✓)
- `logger.error()`: Mensagens de erro (✗)
- `logger.warning()`: Avisos (⚠️)
- `logger.header()`: Cabeçalhos com separadores
- `logger.section()`: Seções
- `logger.progress()`: Informações de progresso

**Benefícios:**
- ✅ Funções testáveis e reutilizáveis
- ✅ Código DRY (Don't Repeat Yourself)
- ✅ Logging consistente em toda aplicação
- ✅ Fácil manutenção

---

## Refatorações Aplicadas

### 1. **TranscriptionService** (`app/services/transcription_service.py`)

**Antes:**
- Hardcoded: `model_name="large-v3"`, `chunk_size=750`, `language="pt"`
- Função `split_into_chunks()` duplicada dentro da classe
- Prints diretos com `print()`
- Descoberta de arquivos inline

**Depois:**
- Usa `settings.WHISPER_MODEL`, `settings.CHUNK_SIZE`, `settings.TRANSCRIPTION_LANGUAGE`
- Delega splitting para `split_text_into_chunks()` de `text_utils`
- Usa `logger` para mensagens consistentes
- Usa `find_audio_files()` e `get_episode_name()` de `file_utils`

---

### 2. **EmbeddingService** (`app/services/embedding_service.py`)

**Antes:**
- Hardcoded: `model_name="all-MiniLM-L6-v2"`, `batch_size=32`, `show_progress_bar=True`
- Prints diretos

**Depois:**
- Usa `settings.EMBEDDING_MODEL`, `settings.EMBEDDING_BATCH_SIZE`, `settings.EMBEDDING_SHOW_PROGRESS`
- Usa `logger` para mensagens

---

### 3. **SearchService** (`app/services/search_service.py`)

**Antes:**
- Path calculation inline com `os.path.join()`
- Truncamento de excerpt inline: `content[:500] + "..."`
- Hardcoded: `top_k=10`
- Prints diretos

**Depois:**
- Usa `settings.get_faiss_index_path()`
- Usa `truncate_text()` de `text_utils`
- Usa `settings.DEFAULT_TOP_K`, `settings.EXCERPT_MAX_LENGTH`
- Usa `logger` para mensagens

---

### 4. **Database Session** (`app/db/session.py`)

**Antes:**
- Path calculation inline complexo
- Hardcoded: `check_same_thread=False`, `echo=False`

**Depois:**
- Usa `settings.get_database_url()`
- Usa `settings.DB_CHECK_SAME_THREAD`, `settings.DB_ECHO`

---

### 5. **Main App** (`app/main.py`)

**Antes:**
- Hardcoded: host, port, título, CORS origins

**Depois:**
- Usa `settings.API_*` para todas configurações
- Usa `settings.CORS_*` para CORS

---

### 6. **Search API** (`app/api/search.py`)

**Antes:**
- Hardcoded: `top_k=10`, `le=50`

**Depois:**
- Usa `settings.DEFAULT_TOP_K`, `settings.MAX_TOP_K`

---

### 7. **Ingestion Script** (`scripts/ingest_podcasts.py`)

**Antes:**
- Path calculation duplicado
- Hardcoded model names e chunk size
- Prints diretos

**Depois:**
- Usa `settings.get_*()` para paths
- Services usam configurações padrão
- Usa `logger` para output consistente

---

## Como Usar

### Modificar Configurações

Edite apenas `app/config/settings.py`:

```python
# Trocar modelo Whisper
WHISPER_MODEL: str = "medium"  # Era "large-v3"

# Aumentar chunk size
CHUNK_SIZE: int = 1000  # Era 750

# Mudar idioma
TRANSCRIPTION_LANGUAGE: str = "en"  # Era "pt"

# Mudar modelo de embeddings
EMBEDDING_MODEL: str = "all-mpnet-base-v2"  # Era "all-MiniLM-L6-v2"
```

### Usar Utilidades em Novo Código

```python
from app.config.settings import settings
from app.utils.logger import logger
from app.utils.text_utils import split_text_into_chunks

# Configurações
model = settings.WHISPER_MODEL
chunks = split_text_into_chunks(text, settings.CHUNK_SIZE)

# Logging
logger.info("Processing started")
logger.success("Done!")
```

---

## Benefícios da Refatoração

### 🎯 Manutenibilidade
- Uma única fonte de verdade para configurações
- Fácil encontrar e modificar valores

### 🧪 Testabilidade
- Funções isoladas podem ser testadas independentemente
- Mock de configurações é simples

### 📖 Legibilidade
- Código mais limpo e menos repetitivo
- Intenção clara com nomes descritivos

### 🔧 Extensibilidade
- Fácil adicionar novas configurações
- Utils podem ser expandidos sem quebrar código existente

### 🎨 Consistência
- Logging padronizado em toda aplicação
- Tratamento de paths e arquivos consistente

---

## Próximos Passos Recomendados

1. **Variáveis de Ambiente**: Mover configurações sensíveis para `.env`
2. **Testes Unitários**: Criar testes para utils
3. **Type Hints**: Adicionar type hints em settings
4. **Validação**: Usar Pydantic para validar configurações
5. **Documentação**: Adicionar docstrings completas
