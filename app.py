from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import os
import json
from grammar_engine import ConjugationEngine
from translation_model import AdvancedTranslationModel
from database import get_db

# Pipeline de entrenamiento NLLB
from core.training.trainer import (
    start_training, stop_training,
    read_training_status, is_training_running, get_training_log
)
from core.training.download_model import (
    start_download_thread, read_download_status, model_weights_exist
)

app = Flask(__name__)

# Inicializar el modelo de traducción avanzado
translation_model = None

def get_translation_model():
    global translation_model
    if translation_model is None:
        nasa_yuwe_dictionary_path = os.path.join('data', 'nasa_yuwe_dictionary.json')
        translation_model = AdvancedTranslationModel(nasa_yuwe_dictionary_path)
    return translation_model

# Mantener compatibilidad con el motor de conjugación
conjugation_engine = None

def get_conjugation_engine():
    global conjugation_engine
    if conjugation_engine is None:
        nasa_yuwe_dictionary_path = os.path.join('data', 'nasa_yuwe_dictionary.json')
        conjugation_engine = ConjugationEngine(nasa_yuwe_dictionary_path)
    return conjugation_engine

# Configuración de subida de archivos
UPLOAD_FOLDER_IMAGES = os.path.join('static', 'uploads', 'images')
UPLOAD_FOLDER_AUDIO = os.path.join('static', 'uploads', 'audio')

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "m4a"}

def allowed_file(filename, media_type):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if media_type == 'image':
        return ext in ALLOWED_IMAGE_EXTENSIONS
    if media_type == 'audio':
        return ext in ALLOWED_AUDIO_EXTENSIONS
    return False

# Índice de medios (ahora en MySQL)
# Las funciones load_media_index / save_media_index ya no se usan.
# Se mantiene MEDIA_INDEX_PATH solo por si se necesita referencia.
MEDIA_INDEX_PATH = os.path.join('data', 'media_index.json')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/translate-text', methods=['POST'])
def translate_text_endpoint():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        source_lang = data.get('source_lang', 'spanish')
        target_lang = data.get('target_lang', 'nasa_yuwe')

        if not text:
            return jsonify({'error': 'No se proporcionó texto para traducir'})

        if source_lang == target_lang:
            return jsonify({'error': 'El idioma de origen y destino no pueden ser iguales'})

        # Validar idiomas soportados
        if not ((source_lang == 'spanish' and target_lang == 'nasa_yuwe') or 
                (source_lang == 'nasa_yuwe' and target_lang == 'spanish')):
            return jsonify({
                'error': 'Solo se admite traducción entre Español y Nasa Yuwe'
            })

        # Usar el modelo de traducción avanzado
        model = get_translation_model()
        result = model.translate(text, source_lang, target_lang)

        return jsonify({
            'translation': result['translation'],
            'status': 'success',
            'method': result['method'],
            'confidence': result['confidence'],
            'methods_tried': result.get('methods_tried', [])
        })

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/model-info', methods=['GET'])
def get_model_info():
    """Obtener información sobre el modelo de traducción"""
    try:
        model = get_translation_model()
        info = model.get_model_info()
        return jsonify({
            'status': 'success',
            'model_info': info
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/upload-media', methods=['POST'])
def upload_media():
    """Subir archivos de imagen o audio"""
    try:
        media_type = request.form.get('type', '').strip()
        tag = request.form.get('tag', '').strip()
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400

        if media_type not in ('image', 'audio'):
            return jsonify({'error': 'Tipo de medio inválido. Use "image" o "audio"'}), 400

        if not allowed_file(file.filename, media_type):
            return jsonify({'error': 'Extensión de archivo no permitida para el tipo especificado'}), 400

        filename = secure_filename(file.filename)

        # Evitar colisiones añadiendo sufijo si el archivo existe
        target_folder = UPLOAD_FOLDER_IMAGES if media_type == 'image' else UPLOAD_FOLDER_AUDIO
        os.makedirs(target_folder, exist_ok=True)
        save_path = os.path.join(target_folder, filename)
        if os.path.exists(save_path):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{int(os.stat(target_folder).st_mtime)}{ext}"
            save_path = os.path.join(target_folder, filename)

        file.save(save_path)

        # URL pública servida desde /static
        public_url = f"/static/uploads/{'images' if media_type == 'image' else 'audio'}/{filename}"

        # Registrar en MySQL
        db = get_db()
        db.add_media(media_type, filename, public_url, tag)

        return jsonify({'status': 'success', 'url': public_url, 'filename': filename, 'type': media_type, 'tag': tag})
    except Exception as e:
        return jsonify({'error': f'Error al subir el archivo: {str(e)}'}), 500

@app.route('/api/media-list', methods=['GET'])
def media_list():
    """Listar archivos de imagen o audio"""
    try:
        media_type = request.args.get('type', '').strip()
        tag = request.args.get('tag', '').strip()
        if media_type not in ('image', 'audio'):
            return jsonify({'error': 'Tipo de medio inválido. Use "image" o "audio"'}), 400

        db = get_db()
        files = db.get_media(media_type, tag if tag else None)

        return jsonify({
            'status': 'success',
            'type': media_type,
            'files': files,
            'tag': tag if tag else None
        })
    except Exception as e:
        return jsonify({'error': f'Error al listar medios: {str(e)}'}), 500

def translate_to_indigenous(text, dictionary):
    # Usar el motor de conjugación para mejorar la traducción
    engine = get_conjugation_engine()
    enhanced_translation = engine.enhance_translation(text, 'spanish', 'nasa_yuwe')
    
    # Si la traducción mejorada es diferente del texto original, usarla
    if enhanced_translation != text:
        return enhanced_translation
    
    # Fallback al método original
    words = text.split()
    translated_words = []

    for word in words:
        if word in dictionary:
            translated_words.append(dictionary[word]['traduccion'])
        else:
            translated_words.append(word)

    return ' '.join(translated_words)

def translate_to_spanish(text, dictionary):
    # Usar el motor de conjugación para mejorar la traducción
    engine = get_conjugation_engine()
    enhanced_translation = engine.enhance_translation(text, 'nasa_yuwe', 'spanish')
    
    # Si la traducción mejorada es diferente del texto original, usarla
    if enhanced_translation != text:
        return enhanced_translation
    
    # Fallback al método original
    words = text.split()
    translated_words = []

    # Crear un diccionario inverso para buscar palabras en español
    reverse_dict = {}
    for spanish_word, data in dictionary.items():
        indigenous_word = data['traduccion'].lower()
        reverse_dict[indigenous_word] = spanish_word

    for word in words:
        word_lower = word.lower()
        if word_lower in reverse_dict:
            translated_words.append(reverse_dict[word_lower])
        else:
            translated_words.append(word)

    return ' '.join(translated_words)

@app.route('/add_word', methods=['POST'])
def add_word():
    try:
        data = request.get_json()
        spanish_word = data.get('spanish_word', '').strip()
        nasa_yuwe_translation = data.get('nasa_yuwe_translation', '').strip()
        context = data.get('context', '').strip()
        
        # Validar que todos los campos estén presentes
        if not spanish_word or not nasa_yuwe_translation or not context:
            return jsonify({'error': 'Todos los campos son obligatorios'}), 400
        
        db = get_db()
        
        # Verificar si la palabra ya existe (case-insensitive)
        existing = db.get_word(spanish_word)
        if existing:
            return jsonify({'error': f'La palabra "{existing["spanish_word"]}" ya existe en el diccionario'}), 409
        
        # Agregar la nueva palabra a MySQL
        db.add_word(spanish_word, nasa_yuwe_translation, context)
        
        return jsonify({
            'status': 'success', 
            'message': f'Palabra "{spanish_word}" agregada exitosamente al diccionario'
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al agregar la palabra: {str(e)}'}), 500

@app.route('/api/feedback', methods=['POST'])
def receive_feedback():
    try:
        data = request.get_json()
        original_text = data.get('original_text', '').strip()
        corrected_translation = data.get('corrected_translation', '').strip()
        source_lang = data.get('source_lang', 'spanish')
        target_lang = data.get('target_lang', 'nasa_yuwe')

        if not original_text or not corrected_translation:
            return jsonify({'error': 'Se requiere texto original y traducción corregida'})

        db = get_db()

        try:
            if source_lang == 'spanish' and target_lang == 'nasa_yuwe':
                # Actualizar o crear entrada español → nasa yuwe
                existing = db.get_word(original_text)
                if existing:
                    db.update_word(existing['spanish_word'], traduccion=corrected_translation)
                else:
                    db.add_word(original_text, corrected_translation,
                                'Agregado por retroalimentación de usuario')

            elif source_lang == 'nasa_yuwe' and target_lang == 'spanish':
                # Buscar la entrada que tiene esta traducción en Nasa Yuwe
                dictionary = db.get_all_dictionary()
                entry_found = False
                for spanish_word, data_entry in dictionary.items():
                    if data_entry['traduccion'].lower() == original_text.lower():
                        # Actualizar: crear nueva con la corrección y borrar anterior si difiere
                        if spanish_word.lower() != corrected_translation.lower():
                            db.delete_word(spanish_word)
                        db.upsert_word(corrected_translation, data_entry['traduccion'],
                                       data_entry.get('explanation', ''))
                        entry_found = True
                        break

                if not entry_found:
                    db.add_word(corrected_translation, original_text,
                                'Agregado por retroalimentación de usuario')

            return jsonify({'status': 'success', 'message': 'Retroalimentación guardada exitosamente'})

        except Exception as e:
            return jsonify({'error': f'Error al procesar la retroalimentación: {str(e)}'})

    except Exception as e:
        return jsonify({'error': str(e)})

# ─── Endpoints de Entrenamiento NLLB ─────────────────────────────────────────

@app.route('/api/training/start', methods=['POST'])
def training_start():
    """Iniciar el fine-tuning del modelo NLLB en background."""
    try:
        result = start_training()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/training/stop', methods=['POST'])
def training_stop():
    """Solicitar detención del entrenamiento en curso."""
    try:
        result = stop_training()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/training/status', methods=['GET'])
def training_status():
    """Obtener el estado actual del entrenamiento."""
    try:
        status = read_training_status()
        status['is_running'] = is_training_running()
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/training/log', methods=['GET'])
def training_log():
    """Obtener las últimas líneas del log de entrenamiento."""
    try:
        lines = request.args.get('lines', 50, type=int)
        log_lines = get_training_log(max_lines=lines)
        return jsonify({'success': True, 'log': log_lines})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/training/download-model', methods=['POST'])
def training_download_model():
    """Iniciar la descarga de los pesos del modelo NLLB desde HuggingFace."""
    try:
        if model_weights_exist():
            return jsonify({
                'success': True,
                'message': 'Los pesos del modelo ya están disponibles.',
                'already_downloaded': True
            })
        start_download_thread()
        return jsonify({
            'success': True,
            'message': 'Descarga iniciada en background. Use /api/training/download-status para verificar el progreso.',
            'already_downloaded': False
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/training/download-status', methods=['GET'])
def training_download_status():
    """Obtener el estado actual de la descarga del modelo."""
    try:
        status = read_download_status()
        status['model_ready'] = model_weights_exist()
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/training/reload-model', methods=['POST'])
def training_reload_model():
    """Recargar el modelo de traducción después del fine-tuning."""
    global translation_model
    try:
        translation_model = None  # Forzar recarga en la próxima solicitud
        model = get_translation_model()  # Recarga con el modelo fine-tuneado si existe
        info = model.get_model_info()
        return jsonify({
            'success': True,
            'message': 'Modelo recargado exitosamente.',
            'model_info': info
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/training/rebuild-dataset', methods=['POST'])
def training_rebuild_dataset():
    """
    Reconstruir el dataset de entrenamiento desde el diccionario actual.
    Se llama automáticamente tras agregar palabras o enviar retroalimentación,
    habilitando el aprendizaje continuo del modelo.
    """
    try:
        from core.training.dataset_builder import build_and_save
        result = build_and_save()
        if result:
            return jsonify({
                'success': True,
                'message': 'Dataset reconstruido exitosamente.',
                'total_pairs':  result['metadata']['total_pairs'],
                'train_pairs':  result['metadata']['train_pairs'],
                'val_pairs':    result['metadata']['val_pairs'],
                'dict_entries': result['metadata']['dictionary_entries'],
            })
        else:
            return jsonify({'success': False, 'message': 'No se pudo reconstruir el dataset.'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─── Arranque de la aplicación ────────────────────────────────────────────────

if __name__ == '__main__':
    # Asegurarse de que los directorios necesarios existen
    os.makedirs('data', exist_ok=True)
    os.makedirs(UPLOAD_FOLDER_IMAGES, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER_AUDIO, exist_ok=True)
    # Inicializar conexión a base de datos
    get_db()
    app.run(debug=True)