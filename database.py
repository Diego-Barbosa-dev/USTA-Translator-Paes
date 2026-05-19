"""
Fachada de base de datos compatible con la API anterior.

Aunque internamente ahora se usa SQLAlchemy ORM, este módulo mantiene
los mismos métodos públicos (`get_db`, `add_word`, etc.) para no romper
componentes existentes durante la transición arquitectónica.
"""

from __future__ import annotations

import logging

from entities.models import init_db
from infrastructure.db import get_session_factory
from repositories.dictionary_repository import DictionaryRepository
from repositories.media_repository import MediaRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_db_instance = None


def get_db():
    """Obtener instancia singleton de la fachada de base de datos."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


class Database:
    """Fachada orientada a compatibilidad que delega en repositorios ORM."""

    def __init__(self):
        init_db()
        self.session = get_session_factory()
        self.dictionary_repository = DictionaryRepository(self.session)
        self.media_repository = MediaRepository(self.session)
        logger.info("Conexión ORM inicializada")

    def get_all_dictionary(self) -> dict:
        return self.dictionary_repository.get_all_dictionary()

    def get_word(self, spanish_word: str):
        return self.dictionary_repository.get_word(spanish_word)

    def count_entries(self) -> int:
        return self.dictionary_repository.count_entries()

    def add_word(self, spanish_word: str, traduccion: str, explanation: str = "", estado: str = "No Verificado"):
        return self.dictionary_repository.add_word(spanish_word, traduccion, explanation, estado)

    def update_word(
        self,
        spanish_word: str,
        traduccion: str | None = None,
        explanation: str | None = None,
        estado: str | None = None,
    ):
        return self.dictionary_repository.update_word(spanish_word, traduccion, explanation, estado)

    def upsert_word(self, spanish_word: str, traduccion: str, explanation: str = "", estado: str = "No Verificado"):
        self.dictionary_repository.upsert_word(spanish_word, traduccion, explanation, estado)

    def delete_word(self, spanish_word: str):
        return self.dictionary_repository.delete_word(spanish_word)

    def get_media(self, media_type: str, tag: str | None = None):
        return self.media_repository.get_media(media_type, tag)

    def add_media(self, media_type: str, filename: str, url: str, tag: str = ""):
        return self.media_repository.add_media(media_type, filename, url, tag)
