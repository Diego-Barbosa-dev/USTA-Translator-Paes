"""Fábrica de servicios para inyección simple de dependencias."""

from __future__ import annotations

from repositories.dictionary_repository import DictionaryRepository
from repositories.media_repository import MediaRepository
from services.dictionary_service import DictionaryService
from services.media_service import MediaService
from services.training_service import TrainingService
from services.translation_service import TranslationService


def build_services(session):
    """Construir y cablear servicios de aplicación."""
    dictionary_repository = DictionaryRepository(session)
    media_repository = MediaRepository(session)

    translation_service = TranslationService()
    dictionary_service = DictionaryService(dictionary_repository)
    media_service = MediaService(media_repository)
    training_service = TrainingService(translation_service)

    return {
        "translation": translation_service,
        "dictionary": dictionary_service,
        "media": media_service,
        "training": training_service,
    }
