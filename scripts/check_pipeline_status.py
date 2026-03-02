#!/usr/bin/env python3
"""
Gera um relatorio .md com o status de cada episodio por podcast em cada etapa do pipeline:
  - Metadados   : presenca na tabela podcast_episodes
  - Transcricao : presenca na tabela podcast_segments (whisper)
  - FAISS       : presenca no indice vetorial

Uso:
  python scripts/check_pipeline_status.py
  python scripts/check_pipeline_status.py --output relatorio.md
"""
import sys
import argparse
from datetime import datetime
from pathlib import Path

import numpy as np  # noqa: E402

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app.core.config import settings  # noqa: E402
from backend.app.core.logger import logger  # noqa: E402
from backend.app.db.session import get_db_session  # noqa: E402
from backend.app.db.models import PodcastEpisode, PodcastSegment  # noqa: E402

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "pipeline_status.md"


def load_faiss_ids() -> set:
    mapping_path = settings.get_faiss_dir() / "embedding_id_mapping.npy"
    if not mapping_path.exists():
        logger.error(f"Mapping nao encontrado: {mapping_path}")
        return set()
    mapping = np.load(str(mapping_path))
    return set(mapping.tolist())


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


def build_report(faiss_ids: set, db) -> str:
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines.append("# Relatorio de Status do Pipeline")
    lines.append(f"\n> Gerado em: {now}")
    lines.append(f"> Total de vetores no FAISS: **{len(faiss_ids):,}**\n")

    podcasts = [p[0] for p in db.query(PodcastEpisode.podcast_source).distinct().all()]

    # ── sumario global ──────────────────────────────────────────────────────
    lines.append("## Sumario Geral\n")
    lines.append("| Podcast | Episodios | Com transcricao | No FAISS | Sem transcricao |")
    lines.append("|---------|----------:|----------------:|---------:|----------------:|")

    podcast_data = {}
    for podcast in sorted(podcasts):
        episodes = (
            db.query(PodcastEpisode)
            .filter(PodcastEpisode.podcast_source == podcast)
            .order_by(PodcastEpisode.published_date.desc())
            .all()
        )

        total = len(episodes)
        with_segs = 0
        fully_faiss = 0
        part_faiss = 0
        no_segs = 0
        rows = []

        for ep in episodes:
            seg_ids = [
                s[0] for s in
                db.query(PodcastSegment.embedding_id)
                .filter(PodcastSegment.episode == ep.filename)
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
            rows.append((date_str, has, n_segs, n_faiss, all_ok, any_ok, ep.filename, ep.title_original))

        podcast_data[podcast] = {
            "total": total,
            "with_segs": with_segs,
            "fully_faiss": fully_faiss,
            "part_faiss": part_faiss,
            "no_segs": no_segs,
            "rows": rows,
        }

        lines.append(
            f"| `{podcast}` | {total} | {with_segs} ({pct(with_segs, total)}) "
            f"| {fully_faiss} ({pct(fully_faiss, total)}) "
            f"| {no_segs} ({pct(no_segs, total)}) |"
        )

    lines.append("")

    # ── detalhe por podcast ─────────────────────────────────────────────────
    for podcast in sorted(podcasts):
        d = podcast_data[podcast]
        lines.append(f"---\n")
        lines.append(f"## {podcast}\n")

        lines.append(
            f"- **Total de episodios:** {d['total']}\n"
            f"- **Com transcricao (whisper):** {d['with_segs']} ({pct(d['with_segs'], d['total'])})\n"
            f"- **Totalmente no FAISS:** {d['fully_faiss']} ({pct(d['fully_faiss'], d['total'])})\n"
            f"- **Parcialmente no FAISS:** {d['part_faiss']}\n"
            f"- **Sem transcricao:** {d['no_segs']} ({pct(d['no_segs'], d['total'])})\n"
        )

        lines.append("| Data | Meta | Transcricao | Segs | FAISS | Episodio |")
        lines.append("|------|:----:|:-----------:|-----:|:-----:|---------|")

        for date_str, has, n_segs, n_faiss, all_ok, any_ok, filename, title in d["rows"]:
            segs_str = str(n_segs) if has else "-"
            faiss_str = str(n_faiss) if has else "-"
            title_md = (title or filename)[:80]
            lines.append(
                f"| {date_str} | {icon(True)} | {icon(has)} | {segs_str} | {faiss_icon(all_ok, any_ok)} | {title_md} |"
            )

        lines.append("")

    return "\n".join(lines)


def run(output_path: Path):
    logger.header("GERANDO RELATORIO DE STATUS DO PIPELINE")

    faiss_ids = load_faiss_ids()
    logger.info(f"IDs carregados do FAISS: {len(faiss_ids):,}")

    db = get_db_session()
    try:
        logger.info("Coletando dados do banco...")
        report = build_report(faiss_ids, db)
    finally:
        db.close()

    output_path.write_text(report, encoding="utf-8")
    logger.info(f"Relatorio salvo em: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera relatorio de status do pipeline em .md")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Caminho do arquivo de saida")
    args = parser.parse_args()
    run(args.output)
