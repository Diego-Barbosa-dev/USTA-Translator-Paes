"""
Generador de dataset de entrenamiento a partir del diccionario Nasa Yuwe.

Crea pares de traducción (español → nasa_yuwe) con variaciones sintéticas
para aumentar el volumen de datos disponibles para el fine-tuning.
"""

import json
import os
import sys
import random
import logging

# Permitir ejecución directa desde cualquier directorio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.training.training_config import DICTIONARY_PATH, TRAINING_PAIRS_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ─── Plantillas de oraciones para aumentación de datos ────────────────────────
SPANISH_TEMPLATES = [
    "La palabra {word} en Nasa Yuwe es {translation}.",
    "En Nasa Yuwe, {word} se dice {translation}.",
    "Traduce {word} al Nasa Yuwe: {translation}.",
    "{word} significa {translation} en el idioma Nasa Yuwe.",
    "El término {word} en Nasa Yuwe es {translation}.",
]

# Plantillas simples (una palabra / frase corta → su traducción directa)
# Estas son las más importantes para el modelo
SIMPLE_TEMPLATES = [
    ("{word}", "{translation}"),
    ("¿Cómo se dice {word}?", "{translation}"),
    ("Traduce: {word}", "{translation}"),
]


def load_dictionary(path: str = DICTIONARY_PATH) -> dict:
    """Cargar el diccionario Nasa Yuwe desde MySQL (o JSON como fallback)."""
    # Intentar cargar desde MySQL primero
    try:
        from database import get_db
        db = get_db()
        data = db.get_all_dictionary()
        if data:
            logger.info(f"Diccionario cargado desde MySQL: {len(data)} entradas")
            return data
    except Exception as e:
        logger.warning(f"No se pudo cargar desde MySQL, usando JSON: {e}")

    # Fallback a JSON
    if not os.path.exists(path):
        logger.error(f"Diccionario no encontrado en: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Diccionario cargado desde JSON: {len(data)} entradas")
    return data


def build_training_pairs(dictionary: dict) -> list:
    """
    Construir pares de entrenamiento (español → nasa_yuwe).

    Genera:
    1. Par directo: palabra española → traducción nasa yuwe
    2. Par inverso: traducción nasa yuwe → palabra española
    3. Pares con contexto (explanation) si está disponible
    4. Variaciones sintéticas con plantillas
    """
    pairs = []
    skipped = 0

    for spanish_word, entry in dictionary.items():
        nasa_translation = entry.get("traduccion", "").strip()
        explanation = entry.get("explanation", "").strip()
        spanish_word = spanish_word.strip()

        # Saltar entradas sin traducción o con traducción igual al original
        if not nasa_translation or nasa_translation.lower() == spanish_word.lower():
            skipped += 1
            continue

        # ── Par directo: español → nasa yuwe ──────────────────────────────
        pairs.append({
            "source_lang": "spanish",
            "target_lang": "nasa_yuwe",
            "source": spanish_word,
            "target": nasa_translation,
            "type": "direct"
        })

        # ── Par inverso: nasa yuwe → español ──────────────────────────────
        pairs.append({
            "source_lang": "nasa_yuwe",
            "target_lang": "spanish",
            "source": nasa_translation,
            "target": spanish_word,
            "type": "inverse"
        })

        # ── Variaciones con plantillas simples ────────────────────────────
        for src_tpl, tgt_tpl in SIMPLE_TEMPLATES:
            src_text = src_tpl.format(word=spanish_word, translation=nasa_translation)
            tgt_text = tgt_tpl.format(word=spanish_word, translation=nasa_translation)
            if src_text != spanish_word:  # no duplicar el par directo
                pairs.append({
                    "source_lang": "spanish",
                    "target_lang": "nasa_yuwe",
                    "source": src_text,
                    "target": tgt_text,
                    "type": "template"
                })

        # ── Par con contexto si hay explicación útil ──────────────────────
        if explanation and explanation != "." and len(explanation) > 5:
            pairs.append({
                "source_lang": "spanish",
                "target_lang": "nasa_yuwe",
                "source": f"{spanish_word} ({explanation})",
                "target": nasa_translation,
                "type": "contextual"
            })

    logger.info(
        f"Pares generados: {len(pairs)} | "
        f"Entradas omitidas: {skipped} | "
        f"Directos: {sum(1 for p in pairs if p['type'] == 'direct')} | "
        f"Inversos: {sum(1 for p in pairs if p['type'] == 'inverse')}"
    )
    return pairs


def split_dataset(pairs: list, train_ratio: float = 0.85):
    """Dividir dataset en entrenamiento y validación."""
    random.seed(42)
    shuffled = pairs.copy()
    random.shuffle(shuffled)
    split_idx = max(1, int(len(shuffled) * train_ratio))
    train = shuffled[:split_idx]
    val   = shuffled[split_idx:]
    logger.info(f"Split → Entrenamiento: {len(train)} | Validación: {len(val)}")
    return train, val


def save_training_pairs(pairs: list, output_path: str = TRAINING_PAIRS_PATH):
    """Guardar los pares de entrenamiento en JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    dictionary = load_dictionary()
    train_pairs, val_pairs = split_dataset(pairs)

    output = {
        "metadata": {
            "total_pairs": len(pairs),
            "train_pairs": len(train_pairs),
            "val_pairs": len(val_pairs),
            "dictionary_entries": len(dictionary),
            "version": "1.0"
        },
        "train": train_pairs,
        "validation": val_pairs
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"Dataset guardado en: {output_path}")
    return output


def build_and_save():
    """Pipeline completo: cargar diccionario → construir pares → guardar."""
    logger.info("=== Construyendo dataset de entrenamiento ===")
    dictionary = load_dictionary()
    if not dictionary:
        logger.error("No se pudo cargar el diccionario. Abortando.")
        return None

    pairs = build_training_pairs(dictionary)
    if not pairs:
        logger.error("No se generaron pares de entrenamiento.")
        return None

    result = save_training_pairs(pairs)
    logger.info("=== Dataset listo ===")
    return result


if __name__ == "__main__":
    result = build_and_save()
    if result:
        print(f"\n✅ Dataset generado exitosamente:")
        print(f"   Total pares : {result['metadata']['total_pairs']}")
        print(f"   Entrenamiento: {result['metadata']['train_pairs']}")
        print(f"   Validación  : {result['metadata']['val_pairs']}")
        print(f"   Archivo     : {TRAINING_PAIRS_PATH}")
