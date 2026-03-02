#!/usr/bin/env python3
"""
Script para verificar o último item adicionado ao índice FAISS.
Este script carrega o mapeamento do FAISS e busca os detalhes do último segmento no banco de dados.
"""
import sys
from pathlib import Path
import numpy as np
import faiss

# Adiciona o diretório raiz ao path para permitir imports do backend
sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app.core.config import settings
from backend.app.core.logger import logger, format_path
from backend.app.db.session import get_db_session
from backend.app.db.models import PodcastSegment, PodcastEpisode

def get_last_added_in_faiss():
    """Busca o último item adicionado no índice FAISS e mapeia para o DB por podcast"""
    logger.header("VERIFICANDO ÚLTIMOS ITENS NO FAISS POR PODCAST")
    
    index_path = settings.get_faiss_index_path()
    mapping_path = index_path.parent / "embedding_id_mapping.npy"
    
    if not index_path.exists():
        logger.error(f"Índice FAISS não encontrado em: {format_path(index_path)}")
        return
    
    if not mapping_path.exists():
        logger.error(f"Mapeamento de IDs não encontrado em: {format_path(mapping_path)}")
        return

    try:
        # 1. Carregar o índice para ver o total
        index = faiss.read_index(str(index_path))
        total_vectors = index.ntotal
        logger.info(f"Total de vetores no índice: {total_vectors}")
        
        if total_vectors == 0:
            logger.warning("O índice está vazio.")
            return

        # 2. Carregar o mapeamento completo
        # O mapping é um array onde o índice do array é a posição no FAISS e o valor é o embedding_id do banco
        mapping = np.load(str(mapping_path))
        
        # 3. Buscar detalhes no Banco de Dados agindo por podcast
        db = get_db_session()
        try:
            # 1. Obter o conjunto de IDs presentes no FAISS para busca rápida
            faiss_ids_set = set(mapping.tolist())
            
            # Buscar quais podcasts existem no DB
            podcasts = db.query(PodcastSegment.podcast_source).distinct().all()
            podcasts = [p[0] for p in podcasts]
            
            logger.info(f"Podcasts detectados no banco: {', '.join(podcasts)}")

            for podcast in podcasts:
                logger.section(f"ÚLTIMO ITEM: {podcast.upper()}")
                
                # Em vez de usar .in_() com milhares de IDs, buscamos os mais recentes do DB
                # e verificamos se eles estão no FAISS.
                # Isso evita o erro "too many SQL variables".
                recent_segments = (
                    db.query(PodcastSegment)
                    .filter(PodcastSegment.podcast_source == podcast)
                    .order_by(PodcastSegment.embedding_id.desc())
                    .limit(100) # Verificamos os últimos 100 do DB
                    .all()
                )
                
                last_segment = None
                for seg in recent_segments:
                    if seg.embedding_id in faiss_ids_set:
                        last_segment = seg
                        break
                
                if not last_segment:
                    logger.warning(f"Nenhum dos últimos 100 segmentos de '{podcast}' está no índice FAISS.")
                    continue


                # Buscar o episódio relacionado
                episode = db.query(PodcastEpisode).filter(PodcastEpisode.filename == last_segment.episode).first()

                logger.info(f"Embedding ID: {last_segment.embedding_id}")
                logger.info(f"Episódio (ID/Slug): {last_segment.episode}")
                
                if episode:
                    logger.info(f"Título: {episode.title_original}")
                    logger.info(f"Data de Publicação: {episode.published_date}")
                else:
                    logger.warning("Metadados do episódio não encontrados no banco de dados principal.")
                
                logger.info(f"Conteúdo: \"{last_segment.content[:150]}...\"")
            
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Erro ao verificar os últimos itens: {e}")


if __name__ == "__main__":
    get_last_added_in_faiss()
