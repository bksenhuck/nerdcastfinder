"""
Script de migração: Adicionar campo program_name para distinguir programas dentro do mesmo feed

Este script adiciona o campo program_name na tabela podcast_episodes e popula
automaticamente baseado no título de cada episódio.

Uso:
    python -m backend.pipelines.db.add_program_name_field

    # Para dry-run (simular sem aplicar):
    python -m backend.pipelines.db.add_program_name_field --dry-run
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.core.config import settings
from backend.app.utils.program_utils import extract_program_from_title, normalize_program_name
from backend.app.core.logger import logger


def add_program_name_field(dry_run: bool = False):
    """Adiciona campo program_name e popula com base nos títulos"""
    db_path = settings.get_database_path()
    
    from backend.app.core.logger import format_path
    logger.info("=" * 70)
    logger.info("MIGRAÇÃO: Adicionar campo program_name")
    logger.info("=" * 70)
    
    if not db_path.exists():
        logger.error(f"Banco de dados não encontrado: {format_path(db_path)}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verifica se a coluna já existe
        logger.info("\n1️⃣  Verificando schema atual...")
        cursor.execute("PRAGMA table_info(podcast_episodes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'program_name' in columns:
            logger.warning("⚠️  Coluna 'program_name' já existe!")
            conn.close()
            return True
        
        # Conta episódios
        cursor.execute("SELECT COUNT(*) FROM podcast_episodes")
        total_episodes = cursor.fetchone()[0]
        logger.info(f"   Total de episódios: {total_episodes}")
        
        if dry_run:
            logger.info("\n🔍 DRY RUN - Nenhuma alteração será feita")
            logger.info("\n2️⃣  Simulando extração de programs...")
            
            cursor.execute("SELECT title_original, podcast_source FROM podcast_episodes LIMIT 20")
            episodes = cursor.fetchall()
            
            program_counts = {}
            for title, pod_source in episodes:
                program = extract_program_from_title(title)
                normalized = normalize_program_name(program, pod_source)
                program_counts[normalized] = program_counts.get(normalized, 0) + 1
                
            logger.info(f"\n   Programas identificados (amostra de 20):")
            for prog, count in sorted(program_counts.items()):
                logger.info(f"     - {prog}: {count} episódios")
            
            conn.close()
            return True
        
        logger.info("\n2️⃣  Adicionando coluna program_name...")
        cursor.execute("""
            ALTER TABLE podcast_episodes 
            ADD COLUMN program_name VARCHAR(100)
        """)
        conn.commit()
        logger.info("   ✓ Coluna adicionada")
        
        logger.info("\n3️⃣  Populando program_name baseado nos títulos...")
        
        # Busca todos os episódios
        cursor.execute("SELECT id, title_original, podcast_source FROM podcast_episodes")
        episodes = cursor.fetchall()
        
        updated = 0
        program_counts = {}
        
        for episode_id, title, pod_source in episodes:
            program = extract_program_from_title(title)
            normalized = normalize_program_name(program, pod_source)
            
            cursor.execute(
                "UPDATE podcast_episodes SET program_name = ? WHERE id = ?",
                (normalized, episode_id)
            )
            
            updated += 1
            program_counts[normalized] = program_counts.get(normalized, 0) + 1
            
            if updated % 100 == 0:
                logger.info(f"   Processados: {updated}/{total_episodes}")
        
        conn.commit()
        
        logger.info(f"\n✅ {updated} episódios atualizados!")
        logger.info("\n📊 Distribuição por programa:")
        for prog, count in sorted(program_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   - {prog}: {count} episódios")
        
        logger.info("\n✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        
    except Exception as e:
        logger.error(f"\n❌ ERRO durante migração: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()
    
    return True


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Adicionar campo program_name à tabela podcast_episodes"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula a migração sem fazer alterações'
    )
    
    args = parser.parse_args()
    
    success = add_program_name_field(dry_run=args.dry_run)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
