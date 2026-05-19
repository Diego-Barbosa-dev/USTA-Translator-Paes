"""
Configuración central del ORM y sesión de base de datos.

Este módulo encapsula la inicialización de SQLAlchemy para desacoplar
la aplicación del motor de base de datos concreto.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


DEFAULT_DATABASE_URL = "mysql+pymysql://admin:admin123@localhost:3306/nasa_yuwe_translator"

_engine = None
_session_factory = None


def get_database_url() -> str:
    """Obtener URL de conexión desde variables de entorno o valor por defecto."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine():
    """Retornar la instancia singleton del engine SQLAlchemy."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(),
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory():
    """Crear y retornar un factory de sesiones thread-safe."""
    global _session_factory
    if _session_factory is None:
        _session_factory = scoped_session(
            sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
        )
    return _session_factory


def get_session():
    """Crear una nueva sesión de base de datos."""
    return get_session_factory()()


def remove_session() -> None:
    """Limpiar la sesión del contexto actual (por ejemplo, al finalizar request)."""
    session_factory = get_session_factory()
    session_factory.remove()
