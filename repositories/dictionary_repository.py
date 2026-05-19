"""Repositorio para operaciones del diccionario sobre la entidad DictionaryEntry."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from entities.models import DictionaryEntry


class DictionaryRepository:
    """Encapsula consultas y mutaciones de `dictionary`."""

    def __init__(self, session):
        self.session = session

    def get_all_dictionary(self) -> dict:
        """Retornar entradas en formato legacy para compatibilidad con módulos existentes."""
        rows = self.session.execute(
            select(
                DictionaryEntry.spanish_word,
                DictionaryEntry.traduccion,
                DictionaryEntry.explanation,
                DictionaryEntry.estado,
            )
        ).all()
        return {
            row.spanish_word: {
                "traduccion": row.traduccion,
                "explanation": row.explanation or "",
                "estado": row.estado or "No Verificado",
            }
            for row in rows
        }

    def get_word(self, spanish_word: str):
        """Buscar palabra exacta ignorando mayúsculas/minúsculas."""
        row = self.session.execute(
            select(DictionaryEntry).where(func.lower(DictionaryEntry.spanish_word) == spanish_word.lower())
        ).scalar_one_or_none()
        if row is None:
            return None
        return {
            "spanish_word": row.spanish_word,
            "traduccion": row.traduccion,
            "explanation": row.explanation,
            "estado": row.estado,
        }

    def count_entries(self) -> int:
        """Contar número de entradas disponibles."""
        return self.session.execute(select(func.count(DictionaryEntry.id))).scalar_one()

    def add_word(
        self,
        spanish_word: str,
        traduccion: str,
        explanation: str = "",
        estado: str = "No Verificado",
    ) -> bool:
        """Insertar palabra y retornar True si fue persistida."""
        entity = DictionaryEntry(
            spanish_word=spanish_word,
            traduccion=traduccion,
            explanation=explanation,
            estado=estado,
        )
        self.session.add(entity)
        try:
            self.session.commit()
            return True
        except IntegrityError:
            self.session.rollback()
            return False

    def update_word(
        self,
        spanish_word: str,
        traduccion: str | None = None,
        explanation: str | None = None,
        estado: str | None = None,
    ) -> bool:
        """Actualizar una palabra existente usando campos opcionales."""
        row = self.session.execute(
            select(DictionaryEntry).where(func.lower(DictionaryEntry.spanish_word) == spanish_word.lower())
        ).scalar_one_or_none()
        if row is None:
            return False

        if traduccion is not None:
            row.traduccion = traduccion
        if explanation is not None:
            row.explanation = explanation
        if estado is not None:
            row.estado = estado

        self.session.commit()
        return True

    def upsert_word(
        self,
        spanish_word: str,
        traduccion: str,
        explanation: str = "",
        estado: str = "No Verificado",
    ) -> None:
        """Insertar o actualizar una palabra según su existencia."""
        row = self.session.execute(
            select(DictionaryEntry).where(func.lower(DictionaryEntry.spanish_word) == spanish_word.lower())
        ).scalar_one_or_none()
        if row is None:
            row = DictionaryEntry(
                spanish_word=spanish_word,
                traduccion=traduccion,
                explanation=explanation,
                estado=estado,
            )
            self.session.add(row)
        else:
            row.traduccion = traduccion
            row.explanation = explanation
            row.estado = estado

        self.session.commit()

    def delete_word(self, spanish_word: str) -> bool:
        """Eliminar palabra por clave en español."""
        row = self.session.execute(
            select(DictionaryEntry).where(func.lower(DictionaryEntry.spanish_word) == spanish_word.lower())
        ).scalar_one_or_none()
        if row is None:
            return False

        self.session.delete(row)
        self.session.commit()
        return True
