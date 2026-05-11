"""
Definición de entidades del dominio con SQLAlchemy ORM.

Las entidades representan tablas de forma portable, evitando SQL específico
del motor para facilitar migraciones de base de datos.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from infrastructure.db import get_engine


class Base(DeclarativeBase):
    """Clase base para todas las entidades ORM."""


class DictionaryEntry(Base):
    """Entrada del diccionario Español <-> Nasa Yuwe."""

    __tablename__ = "dictionary"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    spanish_word: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    traduccion: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="No Verificado")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MediaItem(Base):
    """Archivo multimedia asociado a una etiqueta opcional."""

    __tablename__ = "media_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    tag: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


Index("ix_media_type_tag", MediaItem.media_type, MediaItem.tag)


def init_db() -> None:
    """Crear tablas si no existen en la base de datos configurada."""
    Base.metadata.create_all(bind=get_engine())
