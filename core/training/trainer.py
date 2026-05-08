"""
Pipeline de fine-tuning del modelo NLLB-200 para Español → Nasa Yuwe.

Implementa un ciclo de entrenamiento completo con:
- Carga del modelo base y tokenizador
- Dataset personalizado de PyTorch
- Optimizador AdamW + scheduler lineal
- Guardado de checkpoints
- Logging en tiempo real (JSON + archivo de log)
- Soporte para detención anticipada via flag file
"""

import os
import sys
import json
import time
import logging
import threading
import random
import math

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.training.training_config import (
    MODEL_BASE_PATH,
    MODEL_FINETUNED_PATH,
    TRAINING_PAIRS_PATH,
    TRAINING_STATUS_PATH,
    TRAINING_STOP_FLAG,
    TRAINING_LOG_PATH,
    TRAINING_CONFIG,
    SOURCE_LANG_CODE,
    TARGET_LANG_CODE,
)
from core.training.dataset_builder import build_and_save

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── Estado global del entrenamiento ──────────────────────────────────────────
_training_thread: threading.Thread = None
_training_lock = threading.Lock()


# ─── Utilidades de estado ─────────────────────────────────────────────────────

def _write_status(status: dict):
    """Persistir estado del entrenamiento en JSON para la API."""
    os.makedirs(os.path.dirname(TRAINING_STATUS_PATH), exist_ok=True)
    with open(TRAINING_STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def _append_log(message: str):
    """Agregar línea al log de entrenamiento."""
    os.makedirs(os.path.dirname(TRAINING_LOG_PATH), exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(TRAINING_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    logger.info(message)


def read_training_status() -> dict:
    """Leer estado actual del entrenamiento."""
    try:
        with open(TRAINING_STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"state": "idle", "message": "Sin entrenamiento activo"}


def is_training_running() -> bool:
    """Verificar si hay un entrenamiento en curso."""
    global _training_thread
    return _training_thread is not None and _training_thread.is_alive()


def request_stop():
    """Señalar que el entrenamiento debe detenerse."""
    os.makedirs(os.path.dirname(TRAINING_STOP_FLAG), exist_ok=True)
    with open(TRAINING_STOP_FLAG, "w") as f:
        f.write("stop")
    _append_log("Solicitud de detención recibida.")


def _should_stop() -> bool:
    """Verificar si se solicitó detener el entrenamiento."""
    return os.path.exists(TRAINING_STOP_FLAG)


def _clear_stop_flag():
    """Limpiar el flag de detención."""
    if os.path.exists(TRAINING_STOP_FLAG):
        os.remove(TRAINING_STOP_FLAG)


# ─── Dataset de PyTorch ───────────────────────────────────────────────────────

class NasaYuweDataset(Dataset):
    """
    Dataset de traducción Español ↔ Nasa Yuwe.
    Solo incluye pares donde la dirección es español → nasa_yuwe
    para el entrenamiento del modelo de generación.
    """

    def __init__(self, pairs: list, tokenizer, config: dict):
        self.pairs = pairs
        self.tokenizer = tokenizer
        self.max_src = config["max_source_length"]
        self.max_tgt = config["max_target_length"]

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        pair = self.pairs[idx]
        source_text = pair["source"]
        target_text = pair["target"]

        # Tokenizar texto fuente (español)
        self.tokenizer.src_lang = SOURCE_LANG_CODE
        encoded_src = self.tokenizer(
            source_text,
            max_length=self.max_src,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # Tokenizar texto objetivo (nasa yuwe → tratado como spa_Latn)
        self.tokenizer.tgt_lang = TARGET_LANG_CODE
        encoded_tgt = self.tokenizer(
            target_text,
            max_length=self.max_tgt,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        labels = encoded_tgt["input_ids"].squeeze()
        # Reemplazar padding con -100 para ignorarlo en el cálculo de pérdida
        labels[labels == self.tokenizer.pad_token_id] = -100

        return {
            "input_ids": encoded_src["input_ids"].squeeze(),
            "attention_mask": encoded_src["attention_mask"].squeeze(),
            "labels": labels,
        }


# ─── Pipeline de entrenamiento ────────────────────────────────────────────────

def _run_training():
    """
    Ciclo principal de fine-tuning.
    Se ejecuta en un hilo separado.
    """
    _clear_stop_flag()
    config = TRAINING_CONFIG

    try:
        # ── 1. Verificar que el modelo base existe ─────────────────────────
        _write_status({
            "state": "initializing",
            "message": "Inicializando pipeline de entrenamiento...",
            "epoch": 0,
            "total_epochs": config["num_epochs"],
            "step": 0,
            "loss": None,
            "best_loss": None,
            "progress": 2,
        })
        _append_log("=== Iniciando fine-tuning NLLB → Nasa Yuwe ===")

        model_weights = ["model.safetensors", "pytorch_model.bin"]
        has_weights = any(os.path.exists(os.path.join(MODEL_BASE_PATH, w)) for w in model_weights)
        # También revisar shards
        if not has_weights and os.path.exists(MODEL_BASE_PATH):
            has_weights = any(
                f.startswith("model-") and f.endswith(".safetensors")
                for f in os.listdir(MODEL_BASE_PATH)
            )

        if not has_weights:
            raise FileNotFoundError(
                "Los pesos del modelo no están disponibles. "
                "Primero descarga el modelo usando el botón 'Descargar Modelo'."
            )

        # ── 2. Construir dataset ───────────────────────────────────────────
        _write_status({
            "state": "building_dataset",
            "message": "Construyendo dataset desde el diccionario...",
            "epoch": 0, "total_epochs": config["num_epochs"],
            "step": 0, "loss": None, "best_loss": None, "progress": 5,
        })
        _append_log("Construyendo dataset de entrenamiento...")

        dataset_info = build_and_save()
        if not dataset_info:
            raise RuntimeError("No se pudo construir el dataset de entrenamiento.")

        with open(TRAINING_PAIRS_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        train_pairs = raw_data["train"]
        val_pairs   = raw_data.get("validation", [])

        _append_log(
            f"Dataset listo: {len(train_pairs)} pares de entrenamiento, "
            f"{len(val_pairs)} de validación."
        )

        # ── 3. Cargar tokenizador ──────────────────────────────────────────
        _write_status({
            "state": "loading_tokenizer",
            "message": "Cargando tokenizador NLLB...",
            "epoch": 0, "total_epochs": config["num_epochs"],
            "step": 0, "loss": None, "best_loss": None, "progress": 10,
        })
        _append_log("Cargando tokenizador...")

        from transformers import NllbTokenizer
        tokenizer = NllbTokenizer.from_pretrained(MODEL_BASE_PATH)
        _append_log("Tokenizador cargado.")

        # ── 4. Cargar modelo ───────────────────────────────────────────────
        _write_status({
            "state": "loading_model",
            "message": "Cargando modelo NLLB-200 en memoria...",
            "epoch": 0, "total_epochs": config["num_epochs"],
            "step": 0, "loss": None, "best_loss": None, "progress": 20,
        })
        _append_log("Cargando modelo NLLB-200 (puede tardar 1-2 minutos)...")

        from transformers import AutoModelForSeq2SeqLM
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_BASE_PATH)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)
        _append_log(f"Modelo cargado en: {device}")

        # ── 5. Preparar DataLoaders ────────────────────────────────────────
        torch.manual_seed(config["seed"])

        train_dataset = NasaYuweDataset(train_pairs, tokenizer, config)
        train_loader  = DataLoader(
            train_dataset,
            batch_size=config["batch_size"],
            shuffle=True,
            drop_last=False,
        )

        val_dataset = NasaYuweDataset(val_pairs, tokenizer, config) if val_pairs else None
        val_loader  = DataLoader(val_dataset, batch_size=config["batch_size"], shuffle=False) if val_dataset else None

        # ── 6. Optimizador + Scheduler ────────────────────────────────────
        optimizer = AdamW(
            model.parameters(),
            lr=config["learning_rate"],
            weight_decay=config["weight_decay"],
        )

        total_steps = len(train_loader) * config["num_epochs"] // config["gradient_accumulation_steps"]
        warmup = min(config["warmup_steps"], total_steps // 4)

        from transformers import get_linear_schedule_with_warmup
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=warmup,
            num_training_steps=total_steps,
        )

        # ── 7. Ciclo de entrenamiento ──────────────────────────────────────
        _append_log(f"Iniciando entrenamiento: {config['num_epochs']} épocas, "
                    f"LR={config['learning_rate']}, batch={config['batch_size']}, device={device}")

        best_val_loss = float("inf")
        global_step   = 0
        os.makedirs(MODEL_FINETUNED_PATH, exist_ok=True)

        for epoch in range(1, config["num_epochs"] + 1):
            if _should_stop():
                _append_log("Entrenamiento detenido por el usuario.")
                break

            model.train()
            epoch_loss = 0.0
            optimizer.zero_grad()

            for batch_idx, batch in enumerate(train_loader):
                if _should_stop():
                    break

                input_ids      = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels         = batch["labels"].to(device)

                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )
                loss = outputs.loss / config["gradient_accumulation_steps"]
                loss.backward()

                epoch_loss += outputs.loss.item()

                # Gradient accumulation
                if (batch_idx + 1) % config["gradient_accumulation_steps"] == 0:
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(), config["max_grad_norm"]
                    )
                    optimizer.step()
                    scheduler.step()
                    optimizer.zero_grad()
                    global_step += 1

                # Progreso dentro de la época
                epoch_progress = (batch_idx + 1) / len(train_loader)
                overall_progress = int(
                    20 + ((epoch - 1 + epoch_progress) / config["num_epochs"]) * 75
                )

                if batch_idx % 5 == 0:
                    current_loss = epoch_loss / (batch_idx + 1)
                    _write_status({
                        "state": "training",
                        "message": f"Época {epoch}/{config['num_epochs']} — "
                                   f"paso {batch_idx + 1}/{len(train_loader)} — "
                                   f"pérdida: {current_loss:.4f}",
                        "epoch": epoch,
                        "total_epochs": config["num_epochs"],
                        "step": global_step,
                        "batch": batch_idx + 1,
                        "total_batches": len(train_loader),
                        "loss": round(current_loss, 4),
                        "best_loss": round(best_val_loss, 4) if best_val_loss != float("inf") else None,
                        "progress": overall_progress,
                    })

            # ── Validación al final de cada época ─────────────────────────
            avg_train_loss = epoch_loss / max(len(train_loader), 1)
            avg_val_loss   = None

            if val_loader:
                model.eval()
                val_loss_total = 0.0
                with torch.no_grad():
                    for batch in val_loader:
                        input_ids      = batch["input_ids"].to(device)
                        attention_mask = batch["attention_mask"].to(device)
                        labels         = batch["labels"].to(device)
                        outputs = model(
                            input_ids=input_ids,
                            attention_mask=attention_mask,
                            labels=labels,
                        )
                        val_loss_total += outputs.loss.item()

                avg_val_loss = val_loss_total / max(len(val_loader), 1)
                check_loss   = avg_val_loss
            else:
                check_loss = avg_train_loss

            _append_log(
                f"Época {epoch} completada | "
                f"Pérdida entrenamiento: {avg_train_loss:.4f}" +
                (f" | Pérdida validación: {avg_val_loss:.4f}" if avg_val_loss else "")
            )

            # ── Guardar mejor modelo ───────────────────────────────────────
            if check_loss < best_val_loss:
                best_val_loss = check_loss
                model.save_pretrained(MODEL_FINETUNED_PATH)
                tokenizer.save_pretrained(MODEL_FINETUNED_PATH)
                _append_log(f"✅ Nuevo mejor modelo guardado (pérdida: {best_val_loss:.4f})")

        # ── 8. Finalización ────────────────────────────────────────────────
        _clear_stop_flag()
        stopped_early = _should_stop()

        final_state = "stopped" if stopped_early else "done"
        final_msg   = (
            "Entrenamiento detenido por el usuario."
            if stopped_early else
            f"Entrenamiento completado. Mejor pérdida: {best_val_loss:.4f}"
        )

        _write_status({
            "state": final_state,
            "message": final_msg,
            "epoch": config["num_epochs"],
            "total_epochs": config["num_epochs"],
            "step": global_step,
            "loss": round(avg_train_loss, 4) if 'avg_train_loss' in dir() else None,
            "best_loss": round(best_val_loss, 4) if best_val_loss != float("inf") else None,
            "progress": 100,
            "model_path": MODEL_FINETUNED_PATH,
        })
        _append_log(f"=== {final_msg} ===")

    except Exception as e:
        import traceback
        error_msg = f"Error durante el entrenamiento: {str(e)}"
        _append_log(error_msg)
        _append_log(traceback.format_exc())
        _write_status({
            "state": "error",
            "message": error_msg,
            "epoch": 0,
            "total_epochs": config["num_epochs"],
            "step": 0,
            "loss": None,
            "best_loss": None,
            "progress": 0,
        })
        _clear_stop_flag()


def start_training() -> dict:
    """
    Iniciar el entrenamiento en un hilo de background.
    Retorna un dict con el estado inicial.
    """
    global _training_thread

    with _training_lock:
        if is_training_running():
            return {
                "success": False,
                "message": "Ya hay un entrenamiento en curso.",
                "state": "already_running"
            }

        _training_thread = threading.Thread(target=_run_training, daemon=True)
        _training_thread.start()

    return {
        "success": True,
        "message": "Entrenamiento iniciado en background.",
        "state": "starting"
    }


def stop_training() -> dict:
    """Solicitar la detención del entrenamiento en curso."""
    if not is_training_running():
        return {"success": False, "message": "No hay entrenamiento en curso."}
    request_stop()
    return {"success": True, "message": "Señal de detención enviada. El entrenamiento se detendrá pronto."}


def get_training_log(max_lines: int = 50) -> list:
    """Leer las últimas líneas del log de entrenamiento."""
    try:
        with open(TRAINING_LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines[-max_lines:]]
    except Exception:
        return []


if __name__ == "__main__":
    print("=== Iniciando fine-tuning NLLB (modo directo) ===")
    result = start_training()
    print(result)

    # En modo CLI, esperar a que termine
    while is_training_running():
        status = read_training_status()
        print(f"\r[{status.get('state', '?')}] {status.get('message', '')}    ", end="", flush=True)
        time.sleep(3)

    status = read_training_status()
    print(f"\n\nFinalizado: {status}")
