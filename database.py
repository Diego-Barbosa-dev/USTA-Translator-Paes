"""
Módulo de conexión y operaciones con MySQL (XAMPP).

Provee acceso centralizado a la base de datos para el diccionario
Nasa Yuwe y el índice de medios. Reemplaza los archivos JSON
que se usaban anteriormente.
"""

import pymysql
import pymysql.cursors
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Configuración de conexión ────────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',
    'database': 'nasa_yuwe_translator',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

# ─── Singleton ────────────────────────────────────────────────────────────────
_db_instance = None


def get_db():
    """Obtener instancia singleton de la base de datos."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


class Database:
    """Capa de acceso a datos MySQL para el traductor Nasa Yuwe."""

    def __init__(self):
        self._ensure_database_exists()
        self._ensure_tables_exist()
        logger.info("Conexión a MySQL establecida (nasa_yuwe_translator)")

    # ─── Conexión ─────────────────────────────────────────────────────────

    def _get_connection(self):
        """Crear una nueva conexión a la base de datos."""
        return pymysql.connect(**DB_CONFIG)

    def _ensure_database_exists(self):
        """Crear la base de datos si no existe."""
        config_no_db = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
        config_no_db.pop('cursorclass', None)
        conn = pymysql.connect(**config_no_db)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE DATABASE IF NOT EXISTS `nasa_yuwe_translator` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            conn.commit()
        finally:
            conn.close()

    def _ensure_tables_exist(self):
        """Crear las tablas si no existen."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS dictionary (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        spanish_word VARCHAR(255) NOT NULL,
                        traduccion VARCHAR(255) NOT NULL,
                        explanation TEXT DEFAULT '',
                        estado VARCHAR(50) DEFAULT 'No Verificado',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_spanish (spanish_word)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                      COLLATE=utf8mb4_unicode_ci
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS media_items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        media_type ENUM('image', 'audio') NOT NULL,
                        filename VARCHAR(255) NOT NULL,
                        url VARCHAR(500) NOT NULL,
                        tag VARCHAR(255) DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                      COLLATE=utf8mb4_unicode_ci
                """)
            conn.commit()
        finally:
            conn.close()

    # ─── Diccionario: lectura ─────────────────────────────────────────────

    def get_all_dictionary(self) -> dict:
        """
        Obtener todo el diccionario en formato compatible con el JSON anterior.
        Retorna: { "palabra": { "traduccion": "...", "explanation": "...", "estado": "..." }, ... }
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT spanish_word, traduccion, explanation, estado FROM dictionary")
                rows = cur.fetchall()
            result = {}
            for row in rows:
                result[row['spanish_word']] = {
                    'traduccion': row['traduccion'],
                    'explanation': row['explanation'] or '',
                    'estado': row['estado'] or 'No Verificado',
                }
            return result
        finally:
            conn.close()

    def get_word(self, spanish_word: str) -> dict:
        """Buscar una palabra en el diccionario (case-insensitive)."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT spanish_word, traduccion, explanation, estado "
                    "FROM dictionary WHERE LOWER(spanish_word) = LOWER(%s)",
                    (spanish_word,)
                )
                return cur.fetchone()
        finally:
            conn.close()

    def count_entries(self) -> int:
        """Contar entradas del diccionario."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM dictionary")
                return cur.fetchone()['cnt']
        finally:
            conn.close()

    # ─── Diccionario: escritura ───────────────────────────────────────────

    def add_word(self, spanish_word: str, traduccion: str,
                 explanation: str = '', estado: str = 'No Verificado') -> bool:
        """Agregar una palabra al diccionario. Retorna True si se insertó."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO dictionary (spanish_word, traduccion, explanation, estado) "
                    "VALUES (%s, %s, %s, %s)",
                    (spanish_word, traduccion, explanation, estado)
                )
            conn.commit()
            return True
        except pymysql.err.IntegrityError:
            return False  # Ya existe
        finally:
            conn.close()

    def update_word(self, spanish_word: str, traduccion: str = None,
                    explanation: str = None, estado: str = None) -> bool:
        """Actualizar una entrada existente del diccionario."""
        fields = []
        values = []
        if traduccion is not None:
            fields.append("traduccion = %s")
            values.append(traduccion)
        if explanation is not None:
            fields.append("explanation = %s")
            values.append(explanation)
        if estado is not None:
            fields.append("estado = %s")
            values.append(estado)

        if not fields:
            return False

        values.append(spanish_word)
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE dictionary SET {', '.join(fields)} "
                    "WHERE LOWER(spanish_word) = LOWER(%s)",
                    values
                )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def upsert_word(self, spanish_word: str, traduccion: str,
                    explanation: str = '', estado: str = 'No Verificado') -> None:
        """Insertar o actualizar una palabra (para migración y feedback)."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO dictionary (spanish_word, traduccion, explanation, estado) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE "
                    "traduccion = VALUES(traduccion), "
                    "explanation = VALUES(explanation), "
                    "estado = VALUES(estado)",
                    (spanish_word, traduccion, explanation, estado)
                )
            conn.commit()
        finally:
            conn.close()

    def delete_word(self, spanish_word: str) -> bool:
        """Eliminar una palabra del diccionario."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM dictionary WHERE LOWER(spanish_word) = LOWER(%s)",
                    (spanish_word,)
                )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    # ─── Medios ───────────────────────────────────────────────────────────

    def get_media(self, media_type: str, tag: str = None) -> list:
        """Obtener lista de medios, opcionalmente filtrada por tag."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if tag:
                    cur.execute(
                        "SELECT filename, url FROM media_items "
                        "WHERE media_type = %s AND tag = %s "
                        "ORDER BY created_at",
                        (media_type, tag)
                    )
                else:
                    cur.execute(
                        "SELECT filename, url FROM media_items "
                        "WHERE media_type = %s ORDER BY created_at",
                        (media_type,)
                    )
                return cur.fetchall()
        finally:
            conn.close()

    def add_media(self, media_type: str, filename: str,
                  url: str, tag: str = '') -> int:
        """Agregar un item de media. Retorna el ID insertado."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO media_items (media_type, filename, url, tag) "
                    "VALUES (%s, %s, %s, %s)",
                    (media_type, filename, url, tag)
                )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
