"""
Descargador del modelo NLLB-200 completo desde HuggingFace Hub.

El directorio local solo tiene el tokenizador. Este script descarga
los pesos del modelo (~2.4 GB) y actualiza el estado de la descarga
en tiempo real para que la UI pueda mostrarlo.
"""

import os
import sys
import json
import logging
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.training.training_config import (
    MODEL_BASE_PATH,
    HUGGINGFACE_MODEL_ID,
    DOWNLOAD_STATUS_PATH,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _write_status(status: dict):
    """Escribir estado de descarga en JSON para que la API lo lea."""
    os.makedirs(os.path.dirname(DOWNLOAD_STATUS_PATH), exist_ok=True)
    with open(DOWNLOAD_STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def read_download_status() -> dict:
    """Leer estado de descarga actual."""
    try:
        with open(DOWNLOAD_STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"state": "idle", "message": "Sin información de descarga"}


def model_weights_exist() -> bool:
    """Verificar si los pesos del modelo ya están descargados."""
    weight_files = [
        "model.safetensors",
        "pytorch_model.bin",
        "model.safetensors.index.json",
    ]
    for fname in weight_files:
        if os.path.exists(os.path.join(MODEL_BASE_PATH, fname)):
            return True

    # También revisar shards (modelos grandes divididos en partes)
    if os.path.exists(MODEL_BASE_PATH):
        files = os.listdir(MODEL_BASE_PATH)
        if any(f.startswith("model-") and f.endswith(".safetensors") for f in files):
            return True

    return False


def download_model_weights():
    """
    Descargar los pesos del modelo NLLB-200 desde HuggingFace Hub.
    Actualiza el archivo de estado en tiempo real.
    """
    if model_weights_exist():
        _write_status({
            "state": "already_downloaded",
            "message": "Los pesos del modelo ya están descargados.",
            "model_path": MODEL_BASE_PATH
        })
        logger.info("Los pesos del modelo ya existen localmente.")
        return True

    logger.info(f"Descargando modelo desde: {HUGGINGFACE_MODEL_ID}")
    _write_status({
        "state": "downloading",
        "message": "Iniciando descarga del modelo NLLB-200 (~2.4 GB)...",
        "progress": 0
    })

    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        from huggingface_hub import snapshot_download
        import huggingface_hub

        os.makedirs(MODEL_BASE_PATH, exist_ok=True)

        # Callback de progreso — huggingface_hub >= 0.14
        _write_status({
            "state": "downloading",
            "message": "Descargando pesos del modelo (puede tardar varios minutos)...",
            "progress": 10
        })

        logger.info("Descargando snapshot del modelo...")
        snapshot_download(
            repo_id=HUGGINGFACE_MODEL_ID,
            local_dir=MODEL_BASE_PATH,
            ignore_patterns=["*.msgpack", "*.h5", "flax_model*", "tf_model*"],
        )

        _write_status({
            "state": "verifying",
            "message": "Verificando archivos descargados...",
            "progress": 90
        })

        if model_weights_exist():
            _write_status({
                "state": "done",
                "message": "Modelo descargado y verificado exitosamente.",
                "progress": 100,
                "model_path": MODEL_BASE_PATH
            })
            logger.info("Descarga completada y verificada.")
            return True
        else:
            raise FileNotFoundError("Los archivos de pesos no se encontraron después de la descarga.")

    except ImportError as e:
        msg = f"Dependencia faltante: {e}. Instala: pip install huggingface_hub"
        logger.error(msg)
        _write_status({"state": "error", "message": msg, "progress": 0})
        return False

    except Exception as e:
        msg = f"Error durante la descarga: {str(e)}"
        logger.error(msg)
        _write_status({"state": "error", "message": msg, "progress": 0})
        return False


def start_download_thread():
    """Iniciar la descarga en un hilo de background."""
    t = threading.Thread(target=download_model_weights, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    print("=== Descargando modelo NLLB-200 ===")
    success = download_model_weights()
    if success:
        print("✅ Descarga completada")
    else:
        print("❌ Error en la descarga")
        sys.exit(1)
