"""Servicio para validación y gestión de archivos multimedia."""

from __future__ import annotations

import os

from werkzeug.utils import secure_filename


class MediaService:
    """Centraliza reglas de negocio para carga y consulta de medios."""

    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "m4a"}

    def __init__(self, media_repository):
        self.media_repository = media_repository
        self.upload_folder_images = os.path.join("static", "uploads", "images")
        self.upload_folder_audio = os.path.join("static", "uploads", "audio")

    def ensure_upload_dirs(self) -> None:
        """Crear directorios de uploads en caso de no existir."""
        os.makedirs(self.upload_folder_images, exist_ok=True)
        os.makedirs(self.upload_folder_audio, exist_ok=True)

    def _allowed_file(self, filename: str, media_type: str) -> bool:
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        if media_type == "image":
            return ext in self.ALLOWED_IMAGE_EXTENSIONS
        if media_type == "audio":
            return ext in self.ALLOWED_AUDIO_EXTENSIONS
        return False

    def upload_media(self, uploaded_file, media_type: str, tag: str):
        """Guardar archivo y registrar metadatos en repositorio."""
        if media_type not in ("image", "audio"):
            return {
                "ok": False,
                "status_code": 400,
                "payload": {"error": 'Tipo de medio inválido. Use "image" o "audio"'},
            }

        if not self._allowed_file(uploaded_file.filename, media_type):
            return {
                "ok": False,
                "status_code": 400,
                "payload": {"error": "Extensión de archivo no permitida para el tipo especificado"},
            }

        filename = secure_filename(uploaded_file.filename)
        target_folder = self.upload_folder_images if media_type == "image" else self.upload_folder_audio

        save_path = os.path.join(target_folder, filename)
        if os.path.exists(save_path):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{int(os.stat(target_folder).st_mtime)}{ext}"
            save_path = os.path.join(target_folder, filename)

        uploaded_file.save(save_path)

        public_url = f"/static/uploads/{'images' if media_type == 'image' else 'audio'}/{filename}"
        self.media_repository.add_media(media_type, filename, public_url, tag)

        return {
            "ok": True,
            "status_code": 200,
            "payload": {
                "status": "success",
                "url": public_url,
                "filename": filename,
                "type": media_type,
                "tag": tag,
            },
        }

    def list_media(self, media_type: str, tag: str | None = None):
        """Listar medios persistidos por tipo y etiqueta opcional."""
        if media_type not in ("image", "audio"):
            return {
                "ok": False,
                "status_code": 400,
                "payload": {"error": 'Tipo de medio inválido. Use "image" o "audio"'},
            }

        files = self.media_repository.get_media(media_type, tag if tag else None)
        return {
            "ok": True,
            "status_code": 200,
            "payload": {
                "status": "success",
                "type": media_type,
                "files": files,
                "tag": tag if tag else None,
            },
        }
