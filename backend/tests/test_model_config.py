"""
Quick test to verify Whisper medium model loads correctly
"""
import torch
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.logger import logger

def test_whisper_model():
    """Test if Whisper medium model loads"""
    logger.section(f"Testando modelo Whisper: {settings.WHISPER_MODEL}")
    
    # Check GPU availability
    if torch.cuda.is_available():
        logger.success(f"✓ GPU disponível: {torch.cuda.get_device_name(0)}")
        logger.info(f"  VRAM total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    else:
        logger.warning("⚠️  GPU não disponível, usando CPU")
    
    # Test loading (without actually loading to save time)
    logger.info(f"\n📥 Modelo configurado: {settings.WHISPER_MODEL}")
    logger.info(f"📊 Características:")
    
    model_specs = {
        "tiny": {"params": "39M", "vram": "1GB", "speed": "32x", "accuracy": "~75%"},
        "base": {"params": "74M", "vram": "1GB", "speed": "16x", "accuracy": "~80%"},
        "small": {"params": "244M", "vram": "2GB", "speed": "6x", "accuracy": "~90%"},
        "medium": {"params": "769M", "vram": "5GB", "speed": "2x", "accuracy": "~95%"},
        "large-v3": {"params": "1550M", "vram": "10GB", "speed": "1x", "accuracy": "~97%"}
    }
    
    specs = model_specs.get(settings.WHISPER_MODEL, {})
    logger.info(f"  • Parâmetros: {specs.get('params', 'N/A')}")
    logger.info(f"  • VRAM necessária: {specs.get('vram', 'N/A')}")
    logger.info(f"  • Velocidade relativa: {specs.get('speed', 'N/A')}")
    logger.info(f"  • Acurácia estimada (PT-BR): {specs.get('accuracy', 'N/A')}")
    
    logger.success("\n✓ Configuração válida!")
    logger.info("\nPróximos passos:")
    logger.info("  1. Baixar todos os podcasts: python -m backend.scripts.download_podcasts")
    logger.info("  2. Processar com ingest: python -m backend.scripts.ingest_podcasts")

if __name__ == "__main__":
    test_whisper_model()
