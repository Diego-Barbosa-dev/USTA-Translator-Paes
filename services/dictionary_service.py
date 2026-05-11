"""Servicio de negocio para gestión de palabras del diccionario."""

from __future__ import annotations


class DictionaryService:
    """Orquesta reglas del diccionario desacoplando controlador y repositorio."""

    def __init__(self, dictionary_repository):
        self.dictionary_repository = dictionary_repository

    def add_word(self, spanish_word: str, nasa_yuwe_translation: str, context: str):
        """Agregar palabra validando duplicados case-insensitive."""
        existing = self.dictionary_repository.get_word(spanish_word)
        if existing:
            return {
                "ok": False,
                "status_code": 409,
                "payload": {
                    "error": f'La palabra "{existing["spanish_word"]}" ya existe en el diccionario'
                },
            }

        self.dictionary_repository.add_word(spanish_word, nasa_yuwe_translation, context)
        return {
            "ok": True,
            "status_code": 200,
            "payload": {
                "status": "success",
                "message": f'Palabra "{spanish_word}" agregada exitosamente al diccionario',
            },
        }

    def process_feedback(
        self,
        original_text: str,
        corrected_translation: str,
        source_lang: str,
        target_lang: str,
    ):
        """Aplicar retroalimentación del usuario en el diccionario."""
        if source_lang == "spanish" and target_lang == "nasa_yuwe":
            existing = self.dictionary_repository.get_word(original_text)
            if existing:
                self.dictionary_repository.update_word(
                    existing["spanish_word"], traduccion=corrected_translation
                )
            else:
                self.dictionary_repository.add_word(
                    original_text,
                    corrected_translation,
                    "Agregado por retroalimentación de usuario",
                )
            return

        if source_lang == "nasa_yuwe" and target_lang == "spanish":
            dictionary = self.dictionary_repository.get_all_dictionary()
            entry_found = False
            for spanish_word, data_entry in dictionary.items():
                if data_entry["traduccion"].lower() == original_text.lower():
                    if spanish_word.lower() != corrected_translation.lower():
                        self.dictionary_repository.delete_word(spanish_word)
                    self.dictionary_repository.upsert_word(
                        corrected_translation,
                        data_entry["traduccion"],
                        data_entry.get("explanation", ""),
                    )
                    entry_found = True
                    break

            if not entry_found:
                self.dictionary_repository.add_word(
                    corrected_translation,
                    original_text,
                    "Agregado por retroalimentación de usuario",
                )
