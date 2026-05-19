"""Repositorio para operaciones de archivos multimedia."""

from __future__ import annotations

from sqlalchemy import select

from entities.models import MediaItem


class MediaRepository:
    """Encapsula acceso a `media_items`."""

    def __init__(self, session):
        self.session = session

    def get_media(self, media_type: str, tag: str | None = None) -> list:
        """Obtener lista de medios filtrando opcionalmente por etiqueta."""
        stmt = select(MediaItem).where(MediaItem.media_type == media_type)
        if tag:
            stmt = stmt.where(MediaItem.tag == tag)
        stmt = stmt.order_by(MediaItem.created_at)

        rows = self.session.execute(stmt).scalars().all()
        return [{"filename": row.filename, "url": row.url} for row in rows]

    def add_media(self, media_type: str, filename: str, url: str, tag: str = "") -> int:
        """Persistir archivo multimedia y retornar su identificador."""
        item = MediaItem(media_type=media_type, filename=filename, url=url, tag=tag)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item.id
