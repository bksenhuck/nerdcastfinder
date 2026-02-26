"""
Script de migração: Nerdcast-específico → Multi-Podcast genérico

Este script migra o banco de dados de uma estrutura específica para Nerdcast
para uma estrutura genérica que suporta múltiplos podcasts.

Alterações realizadas:
1. Renomeia tabela: nerdcast_episodes → podcast_episodes
2. Renomeia tabela: nerdcast_segments → podcast_segments
3. Adiciona coluna: podcast_source (VARCHAR) em ambas as tabelas
4. Popula podcast_source='nerdcast' para todos os registros existentes

IMPORTANTE: 
- Um backup automático será criado antes da migração
- Para reverter, use o backup criado

Uso:
    python -m backend.pipelines.db.migrate_to_multi_podcast

    # Para reverter (restaurar backup):
    python -m backend.pipelines.db.migrate_to_multi_podcast --rollback
"""

import sys
import os
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.core.config import settings
from backend.app.core.logger import logger


def create_backup(db_path: Path) -> Path:
    """Cria um backup do banco de dados."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
    
    from backend.app.core.logger import format_path
    logger.info(f"Criando backup: {format_path(backup_path)}")
    shutil.copy2(db_path, backup_path)
    logger.info(f"✓ Backup criado com sucesso")
    
    return backup_path


def check_current_schema(cursor: sqlite3.Cursor) -> dict:
    """Verifica o estado atual do esquema do banco de dados."""
    schema_state = {
        'has_old_episodes': False,
        'has_old_segments': False,
        'has_new_episodes': False,
        'has_new_segments': False,
        'episodes_has_podcast_source': False,
        'segments_has_podcast_source': False
    }
    
    # Verifica quais tabelas existem
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema_state['has_old_episodes'] = 'nerdcast_episodes' in tables
    schema_state['has_old_segments'] = 'nerdcast_segments' in tables
    schema_state['has_new_episodes'] = 'podcast_episodes' in tables
    schema_state['has_new_segments'] = 'podcast_segments' in tables
    
    # Verifica se coluna podcast_source existe
    if schema_state['has_old_episodes']:
        cursor.execute("PRAGMA table_info(nerdcast_episodes)")
        columns = [row[1] for row in cursor.fetchall()]
        schema_state['episodes_has_podcast_source'] = 'podcast_source' in columns
    
    if schema_state['has_old_segments']:
        cursor.execute("PRAGMA table_info(nerdcast_segments)")
        columns = [row[1] for row in cursor.fetchall()]
        schema_state['segments_has_podcast_source'] = 'podcast_source' in columns
    
    return schema_state


def migrate_database(db_path: Path, dry_run: bool = False):
    """Executa a migração do banco de dados."""
    logger.info("=" * 70)
    logger.info("MIGRAÇÃO: Nerdcast-específico → Multi-Podcast genérico")
    logger.info("=" * 70)
    
    if not db_path.exists():
        logger.error(f"Banco de dados não encontrado: {format_path(db_path)}")
        return False
    
    # Cria backup
    if not dry_run:
        backup_path = create_backup(db_path)
        logger.info(f"\n📦 Backup salvo em: {format_path(backup_path)}")
    
    # Conecta ao banco
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verifica estado atual
        logger.info("\n1️⃣  Verificando estado atual do schema...")
        schema = check_current_schema(cursor)
        
        logger.info(f"   - Tabela nerdcast_episodes: {'✓' if schema['has_old_episodes'] else '✗'}")
        logger.info(f"   - Tabela nerdcast_segments: {'✓' if schema['has_old_segments'] else '✗'}")
        logger.info(f"   - Tabela podcast_episodes: {'✓' if schema['has_new_episodes'] else '✗'}")
        logger.info(f"   - Tabela podcast_segments: {'✓' if schema['has_new_segments'] else '✗'}")
        
        # Verifica se já foi migrado
        if schema['has_new_episodes'] and schema['has_new_segments']:
            logger.warning("\n⚠️  Migração já foi executada anteriormente!")
            logger.info("   As tabelas podcast_episodes e podcast_segments já existem.")
            
            if schema['has_old_episodes'] or schema['has_old_segments']:
                logger.info("\n   As tabelas antigas ainda existem. Você pode:")
                logger.info("   1. Mantê-las como backup")
                logger.info("   2. Removê-las manualmente se confirmar que tudo está funcionando")
            
            conn.close()
            return True
        
        # Conta registros antes da migração
        counts = {}
        if schema['has_old_episodes']:
            cursor.execute("SELECT COUNT(*) FROM nerdcast_episodes")
            counts['episodes'] = cursor.fetchone()[0]
            logger.info(f"\n📊 Registros encontrados:")
            logger.info(f"   - Episódios: {counts['episodes']}")
        
        if schema['has_old_segments']:
            cursor.execute("SELECT COUNT(*) FROM nerdcast_segments")
            counts['segments'] = cursor.fetchone()[0]
            logger.info(f"   - Segmentos: {counts['segments']}")
        
        if dry_run:
            logger.info("\n🔍 DRY RUN - Nenhuma alteração será feita")
            conn.close()
            return True
        
        # Inicia transação
        logger.info("\n2️⃣  Iniciando migração...")
        
        # ETAPA 1: Adiciona coluna podcast_source nas tabelas antigas (se necessário)
        if schema['has_old_episodes'] and not schema['episodes_has_podcast_source']:
            logger.info("   - Adicionando coluna podcast_source em nerdcast_episodes...")
            cursor.execute("""
                ALTER TABLE nerdcast_episodes 
                ADD COLUMN podcast_source VARCHAR(100) DEFAULT 'nerdcast'
            """)
        
        if schema['has_old_segments'] and not schema['segments_has_podcast_source']:
            logger.info("   - Adicionando coluna podcast_source em nerdcast_segments...")
            cursor.execute("""
                ALTER TABLE nerdcast_segments 
                ADD COLUMN podcast_source VARCHAR(100) DEFAULT 'nerdcast'
            """)
        
        # ETAPA 2: Popula podcast_source com 'nerdcast' para todos os registros existentes
        if schema['has_old_episodes']:
            logger.info("   - Populando podcast_source='nerdcast' nos episódios existentes...")
            cursor.execute("""
                UPDATE nerdcast_episodes 
                SET podcast_source = 'nerdcast' 
                WHERE podcast_source IS NULL OR podcast_source = ''
            """)
        
        if schema['has_old_segments']:
            logger.info("   - Populando podcast_source='nerdcast' nos segmentos existentes...")
            cursor.execute("""
                UPDATE nerdcast_segments 
                SET podcast_source = 'nerdcast' 
                WHERE podcast_source IS NULL OR podcast_source = ''
            """)
        
        # ETAPA 3: Renomeia as tabelas
        if schema['has_old_episodes']:
            logger.info("   - Renomeando nerdcast_episodes → podcast_episodes...")
            cursor.execute("ALTER TABLE nerdcast_episodes RENAME TO podcast_episodes")
        
        if schema['has_old_segments']:
            logger.info("   - Renomeando nerdcast_segments → podcast_segments...")
            cursor.execute("ALTER TABLE nerdcast_segments RENAME TO podcast_segments")
        
        # Commit das alterações
        conn.commit()
        
        # Verifica resultado
        logger.info("\n3️⃣  Verificando resultado...")
        cursor.execute("SELECT COUNT(*) FROM podcast_episodes")
        new_episodes_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM podcast_segments")
        new_segments_count = cursor.fetchone()[0]
        
        logger.info(f"   - Episódios migrados: {new_episodes_count}")
        logger.info(f"   - Segmentos migrados: {new_segments_count}")
        
        # Verifica integridade dos dados
        cursor.execute("SELECT DISTINCT podcast_source FROM podcast_episodes")
        episode_sources = [row[0] for row in cursor.fetchall()]
        logger.info(f"   - Podcasts em episódios: {episode_sources}")
        
        cursor.execute("SELECT DISTINCT podcast_source FROM podcast_segments")
        segment_sources = [row[0] for row in cursor.fetchall()]
        logger.info(f"   - Podcasts em segmentos: {segment_sources}")
        
        logger.info("\n✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        logger.info(f"\n📦 Backup disponível em: {format_path(backup_path)}")
        logger.info("\n⚠️  PRÓXIMOS PASSOS:")
        logger.info("   1. Atualizar os modelos em backend/app/db/models.py")
        logger.info("   2. Atualizar imports em todos os arquivos que usam os modelos")
        logger.info("   3. Testar a aplicação")
        logger.info("   4. Se tudo funcionar, você pode remover o backup")
        
    except Exception as e:
        logger.error(f"\n❌ ERRO durante migração: {e}")
        conn.rollback()
        logger.info("\n🔄 Rollback executado - nenhuma alteração foi salva")
        return False
    
    finally:
        conn.close()
    
    return True


def rollback_migration(db_path: Path, backup_path: str = None):
    """Reverte a migração usando um backup."""
    logger.info("=" * 70)
    logger.info("ROLLBACK: Restaurando backup")
    logger.info("=" * 70)
    
    if backup_path and Path(backup_path).exists():
        backup = Path(backup_path)
    else:
        # Procura pelo backup mais recente
        backup_pattern = f"{db_path.stem}_backup_*{db_path.suffix}"
        backups = sorted(db_path.parent.glob(backup_pattern), reverse=True)
        
        if not backups:
            logger.error("❌ Nenhum backup encontrado!")
            logger.info(f"   Procurei por: {format_path(db_path.parent / backup_pattern)}")
            return False
        
        backup = backups[0]
        logger.info(f"📦 Backup mais recente encontrado: {format_path(backup)}")
    
    # Confirma com o usuário
    logger.warning(f"\n⚠️  ATENÇÃO: Isso irá SUBSTITUIR o banco atual:")
    logger.info(f"   Origem: {format_path(backup)}")
    logger.info(f"   Destino: {format_path(db_path)}")
    
    response = input("\nDeseja continuar? (yes/no): ")
    if response.lower() not in ['yes', 'y', 'sim', 's']:
        logger.info("❌ Rollback cancelado")
        return False
    
    # Faz backup do estado atual antes de fazer rollback
    current_backup = db_path.parent / f"{db_path.stem}_before_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}{db_path.suffix}"
    shutil.copy2(db_path, current_backup)
    logger.info(f"\n📦 Backup do estado atual salvo em: {format_path(current_backup)}")
    
    # Restaura o backup
    shutil.copy2(backup, db_path)
    logger.info(f"\n✅ Banco de dados restaurado com sucesso!")
    logger.info(f"   O estado anterior foi salvo em: {format_path(current_backup)}")
    
    return True


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migração: Nerdcast-específico → Multi-Podcast genérico"
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Reverte a migração usando um backup'
    )
    parser.add_argument(
        '--backup-path',
        type=str,
        help='Caminho para o backup específico a ser restaurado (usado com --rollback)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula a migração sem fazer alterações'
    )
    
    args = parser.parse_args()
    
    db_path = settings.get_database_path()
    
    if args.rollback:
        success = rollback_migration(db_path, args.backup_path)
    else:
        success = migrate_database(db_path, dry_run=args.dry_run)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
