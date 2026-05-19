"""Servicio para la lógica de traducción y gestión del modelo."""

from __future__ import annotations

import os

from translation_model import AdvancedTranslationModel


class TranslationService:
    """Gestiona validación funcional y uso del modelo de traducción."""

    def __init__(self):
        self._translation_model = None

    def _get_model(self) -> AdvancedTranslationModel:
        """Inicializar el modelo bajo demanda para reducir tiempo de arranque."""
        if self._translation_model is None:
            dictionary_path = os.path.join("data", "nasa_yuwe_dictionary.json")
            self._translation_model = AdvancedTranslationModel(dictionary_path)
        return self._translation_model

    def reset_model(self) -> None:
        """Forzar recarga del modelo en la siguiente traducción."""
        self._translation_model = None

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> dict:
        """Aplicar reglas de validación y ejecutar traducción."""
        if not text:
            return {"ok": False, "status_code": 400, "payload": {"error": "No se proporcionó texto para traducir"}}

        if source_lang == target_lang:
            return {
                "ok": False,
                "status_code": 400,
                "payload": {"error": "El idioma de origen y destino no pueden ser iguales"},
            }

        supported = {
            ("spanish", "nasa_yuwe"),
            ("nasa_yuwe", "spanish"),
        }
        if (source_lang, target_lang) not in supported:
            return {
                "ok": False,
                "status_code": 400,
                "payload": {"error": "Solo se admite traducción entre Español y Nasa Yuwe"},
            }

        result = self._get_model().translate(text, source_lang, target_lang)
        return {
            "ok": True,
            "status_code": 200,
            "payload": {
                "translation": result["translation"],
                "status": "success",
                "method": result["method"],
                "confidence": result["confidence"],
                "methods_tried": result.get("methods_tried", []),
            },
        }

    def get_model_info(self) -> dict:
        """Retornar metadatos operativos del modelo de traducción."""
        info = self._get_model().get_model_info()
        return {"status": "success", "model_info": info}
