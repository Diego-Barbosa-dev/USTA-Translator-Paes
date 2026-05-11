"""
Controlador principal de la API REST.

Define endpoints HTTP y delega toda la lógica de negocio a la capa de servicios.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request


api_bp = Blueprint("api", __name__)


def _service(name: str):
    """Resolver servicio desde el contenedor registrado en Flask app config."""
    return current_app.config["services"][name]


@api_bp.route("/")
def index():
    """Renderizar interfaz principal."""
    return render_template("index.html")


@api_bp.route("/api/translate-text", methods=["POST"])
def translate_text_endpoint():
    """Endpoint de traducción textual entre Español y Nasa Yuwe."""
    try:
        data = request.get_json() or {}
        text = data.get("text", "").strip()
        source_lang = data.get("source_lang", "spanish")
        target_lang = data.get("target_lang", "nasa_yuwe")

        result = _service("translation").translate_text(text, source_lang, target_lang)
        return jsonify(result["payload"]), result["status_code"]
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/model-info", methods=["GET"])
def get_model_info():
    """Obtener metadata operativa del modelo de traducción."""
    try:
        info = _service("translation").get_model_info()
        return jsonify(info)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/upload-media", methods=["POST"])
def upload_media():
    """Subir un archivo multimedia y registrar metadatos."""
    try:
        media_type = request.form.get("type", "").strip()
        tag = request.form.get("tag", "").strip()

        if "file" not in request.files:
            return jsonify({"error": "No se envió ningún archivo"}), 400

        uploaded_file = request.files["file"]
        if uploaded_file.filename == "":
            return jsonify({"error": "Nombre de archivo vacío"}), 400

        result = _service("media").upload_media(uploaded_file, media_type, tag)
        return jsonify(result["payload"]), result["status_code"]
    except Exception as exc:
        return jsonify({"error": f"Error al subir el archivo: {str(exc)}"}), 500


@api_bp.route("/api/media-list", methods=["GET"])
def media_list():
    """Listar archivos multimedia registrados."""
    try:
        media_type = request.args.get("type", "").strip()
        tag = request.args.get("tag", "").strip()

        result = _service("media").list_media(media_type, tag if tag else None)
        return jsonify(result["payload"]), result["status_code"]
    except Exception as exc:
        return jsonify({"error": f"Error al listar medios: {str(exc)}"}), 500


@api_bp.route("/add_word", methods=["POST"])
def add_word():
    """Agregar una nueva palabra al diccionario."""
    try:
        data = request.get_json() or {}
        spanish_word = data.get("spanish_word", "").strip()
        nasa_yuwe_translation = data.get("nasa_yuwe_translation", "").strip()
        context = data.get("context", "").strip()

        if not spanish_word or not nasa_yuwe_translation or not context:
            return jsonify({"error": "Todos los campos son obligatorios"}), 400

        result = _service("dictionary").add_word(spanish_word, nasa_yuwe_translation, context)
        return jsonify(result["payload"]), result["status_code"]
    except Exception as exc:
        return jsonify({"error": f"Error al agregar la palabra: {str(exc)}"}), 500


@api_bp.route("/api/feedback", methods=["POST"])
def receive_feedback():
    """Recibir retroalimentación de traducciones para mejora continua."""
    try:
        data = request.get_json() or {}
        original_text = data.get("original_text", "").strip()
        corrected_translation = data.get("corrected_translation", "").strip()
        source_lang = data.get("source_lang", "spanish")
        target_lang = data.get("target_lang", "nasa_yuwe")

        if not original_text or not corrected_translation:
            return jsonify({"error": "Se requiere texto original y traducción corregida"}), 400

        _service("dictionary").process_feedback(
            original_text,
            corrected_translation,
            source_lang,
            target_lang,
        )
        return jsonify({"status": "success", "message": "Retroalimentación guardada exitosamente"})
    except Exception as exc:
        return jsonify({"error": f"Error al procesar la retroalimentación: {str(exc)}"}), 500


@api_bp.route("/api/training/start", methods=["POST"])
def training_start():
    """Iniciar entrenamiento del modelo en segundo plano."""
    try:
        return jsonify(_service("training").start())
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@api_bp.route("/api/training/stop", methods=["POST"])
def training_stop():
    """Solicitar detención del entrenamiento en curso."""
    try:
        return jsonify(_service("training").stop())
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@api_bp.route("/api/training/status", methods=["GET"])
def training_status():
    """Consultar estado del entrenamiento."""
    try:
        return jsonify(_service("training").status())
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@api_bp.route("/api/training/log", methods=["GET"])
def training_log():
    """Obtener últimas líneas del log de entrenamiento."""
    try:
        lines = request.args.get("lines", 50, type=int)
        return jsonify(_service("training").log(lines))
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@api_bp.route("/api/training/download-model", methods=["POST"])
def training_download_model():
    """Iniciar descarga de pesos base del modelo."""
    try:
        return jsonify(_service("training").start_model_download())
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@api_bp.route("/api/training/download-status", methods=["GET"])
def training_download_status():
    """Consultar estado de descarga de pesos del modelo."""
    try:
        return jsonify(_service("training").model_download_status())
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@api_bp.route("/api/training/reload-model", methods=["POST"])
def training_reload_model():
    """Recargar modelo en memoria para usar último artefacto disponible."""
    try:
        return jsonify(_service("training").reload_model())
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@api_bp.route("/api/training/rebuild-dataset", methods=["POST"])
def training_rebuild_dataset():
    """Reconstruir dataset de entrenamiento desde el diccionario actual."""
    try:
        payload, status = _service("training").rebuild_dataset()
        return jsonify(payload), status
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500
