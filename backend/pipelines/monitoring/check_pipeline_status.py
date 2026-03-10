#!/usr/bin/env python3
"""
Gera relatorios .md individuais por podcast e um sumario geral.
"""
import sys
import argparse
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import get_db_session
from backend.app.db.models import PodcastEpisode, PodcastSegment
from backend.app.utils.faiss_utils import load_indexed_embedding_ids

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent


def icon(condition: bool) -> str:
    return "✅" if condition else "❌"


def faiss_icon(all_ok: bool, any_ok: bool) -> str:
    if all_ok:
        return "✅"
    if any_ok:
        return "⚠️"
    return "❌"


def pct(num: int, total: int) -> str:
    return f"{num/total*100:.1f}%" if total else "0.0%"


def get_sort_key(ep):
    if ep.stable_id:
        parts = ep.stable_id.split("_")
        for part in reversed(parts):
            if part.isdigit():
                return int(part)
    return 0


def run(output_dir: Path):
    logger.header("GERANDO RELATORIOS DE STATUS DO PIPELINE (INDIVIDUAIS)")

    faiss_ids = load_indexed_embedding_ids()
    logger.info(f"IDs carregados do FAISS: {len(faiss_ids):,}")

    db = get_db_session()
    try:
        logger.info("Coletando nomes dos podcasts...")
        podcasts = [p[0] for p in db.query(PodcastEpisode.podcast_source).distinct().all()]
        
        # Inicia Sumario Geral
        summary_lines = ["# Sumario Geral do Pipeline\n"]
        summary_lines.append(f"> Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        summary_lines.append("| Podcast | Episodios | Transcritos | No FAISS | Sem Transcricao | Relatorio |")
        summary_lines.append("|:---|---:|---:|---:|---:|:---|")

        for podcast in sorted(podcasts):
            logger.info(f"Processando podcast: {podcast}")
            
            # Busca episodios
            episodes = (
                db.query(PodcastEpisode)
                .filter(PodcastEpisode.podcast_source == podcast)
                .all()
            )
            episodes.sort(key=get_sort_key, reverse=True)

            total = len(episodes)
            with_segs = 0
            fully_faiss = 0
            part_faiss = 0
            no_segs = 0
            
            # Linhas para o arquivo individual
            indiv_lines = [f"# Relatorio de Status: {podcast}\n"]
            indiv_lines.append(f"> Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            indiv_lines.append("| Data | Meta | Transcricao | Segs | FAISS | Episodio |")
            indiv_lines.append("|:---|:---:|:---:|---:|:---:|:---|")

            for ep in episodes:
                if ep.stable_id:
                    seg_filter = PodcastSegment.stable_id == ep.stable_id
                else:
                    seg_filter = PodcastSegment.episode == ep.filename
                
                seg_ids = [
                    s[0] for s in
                    db.query(PodcastSegment.embedding_id)
                    .filter(seg_filter)
                    .all()
                ]

                n_segs = len(seg_ids)
                n_faiss = sum(1 for eid in seg_ids if eid in faiss_ids)
                has = n_segs > 0
                all_ok = has and n_faiss == n_segs
                any_ok = has and n_faiss > 0

                if has:
                    with_segs += 1
                    if all_ok:
                        fully_faiss += 1
                    elif any_ok:
                        part_faiss += 1
                else:
                    no_segs += 1

                date_str = str(ep.published_date)[:10] if ep.published_date else "????"
                segs_str = str(n_segs) if has else "-"
                title_md = (ep.title_original or ep.filename)[:100]
                
                indiv_lines.append(
                    f"| {date_str} | {icon(True)} | {icon(has)} | {segs_str} | {faiss_icon(all_ok, any_ok)} | {title_md} |"
                )

            # Salvar o arquivo individual
            safe_name = podcast.replace(" ", "_").lower()
            indiv_filename = f"status_{safe_name}.md"
            indiv_path = output_dir / indiv_filename
            indiv_path.write_text("\n".join(indiv_lines), encoding="utf-8")
            logger.info(f"Relatorio individual salvo: {indiv_filename}")

            # Adicionar ao sumario geral
            summary_lines.append(
                f"| `{podcast}` | {total} | {with_segs} ({pct(with_segs, total)}) " 
                f"| {fully_faiss} ({pct(fully_faiss, total)}) "
                f"| {no_segs} ({pct(no_segs, total)}) "
                f"| [Ver Detalhes](./{indiv_filename}) |"
            )

        # Salvar o Sumario Geral
        summary_path = output_dir / "pipeline_status.md"
        summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
        logger.info(f"Sumario geral salvo em: {summary_path}")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera relatorios de status do pipeline")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Diretorio de saida")
    args = parser.parse_args()
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run(args.output_dir)
