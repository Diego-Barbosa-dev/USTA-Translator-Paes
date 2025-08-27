from flask import Flask, request, jsonify, render_template 
'''
Flask = ayuda a crear la app para iniciar la app.
Request = Sirve para recibir información en archivos .form, .json, .args, .files y el metodo HTTP
jsonify = ayuda a convertir datos como diccionarios o tuplas en respuestas JSON válidas
render_template = sirve para cargar las pestañas .html de flask, usa la carpeta templates/ por defecto
'''
from speech_recognition import Recognizer, AudioFile, UnknownValueError, RequestError
'''
Recognizer = Es la clase principal para el reconocimiento de voz. Carga Audio, ajusta el volumen de voz y usa diferentes APIS
AudioFile = Permite leer un archivo de audio (.wav, .aiff, .flac) y usarlo con Recognizer
UnknownValueError = Excepción que se lanza cuando el motor de reconocimiento no entiende el audio (por mala calidad, ruido, idioma incorrecto, etc.).
RequestError = Excepción que se lanza cuando hay un problema de conexión o con la API usada para reconocer el audio.
'''
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


import torch
import soundfile as sf
import numpy as np
import logging
from logging.handlers import RotatingFileHandler
import os
import json
from pathlib import Path

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Configuración del sistema de logging, esto creará una carpeta para los logs
if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Iniciando aplicación de traducción')


# Configuración de modelos y datos offline
MODELS_DIR = Path('models')
DATA_DIR = Path('data')
MODELS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Diccionario de lenguas indígenas del Meta disponibles
LENGUAS_META = {
    'sikuani': 'Sikuani',
    'piapoco': 'Piapoco',
    'achagua': 'Achagua',
    'guayabero': 'Guayabero'
}

# Cargar diccionario offline
def load_offline_dictionary(lengua):
    try:
        dict_path = DATA_DIR / f'{lengua}_dictionary.json'
        if dict_path.exists():
            with open(dict_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        app.logger.error(f'Error al cargar diccionario offline: {str(e)}')
        return {}

# Initialize the translation model
try:
    # Cargar modelo pequeño para traducción offline desde el directorio local
    model_path = MODELS_DIR / 'nllb-200-distilled-600M'
    if not model_path.exists():
        app.logger.warning('Modelo no encontrado localmente. Por favor, ejecute primero download_model.py')
        model = None
        tokenizer = None
    else:
        tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path), local_files_only=True)
        model.eval()
        if torch.cuda.is_available():
            model = model.to('cuda')
        app.logger.info('Modelo de traducción offline cargado exitosamente')
except Exception as e:
    app.logger.error(f'Error al cargar el modelo de traducción: {str(e)}')
    model = None
    tokenizer = None

@torch.no_grad()  # decorador para desactivar el calculo del gradiente
def translate_text(text):
    if model is None or tokenizer is None:
        raise RuntimeError('El modelo de traducción no está disponible')
    try:
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        if torch.cuda.is_available():
            inputs = {k: v.to('cuda') for k, v in inputs.items()}
        translated = model.generate(**inputs, max_length=512)
        return tokenizer.decode(translated[0], skip_special_tokens=True)
    except Exception as e:
        raise RuntimeError(f'Error en la traducción: {str(e)}')

class IndigenousTranslator:
    def __init__(self):
        self.dictionaries = {}
        self.load_dictionaries()

    def load_dictionaries(self):
        for lengua in LENGUAS_META.keys():
            self.dictionaries[lengua] = load_offline_dictionary(lengua)

    def translate(self, text, source_lang, target_lang):
        try:
            # Verifica si el texto está vacío
            if not text or text.isspace():
                raise ValueError('El texto a traducir está vacío')

            # Verifica si el idioma objetivo está disponible
            if target_lang not in LENGUAS_META:
                raise ValueError(f'Lengua indígena no soportada. Lenguas disponibles: {", ".join(LENGUAS_META.values())}')

            # Verifica si el diccionario está cargado
            if not self.dictionaries.get(target_lang):
                app.logger.error(f'Diccionario no encontrado para {target_lang}')
                raise ValueError(f'No se pudo cargar el diccionario para {LENGUAS_META[target_lang]}')

            # Usar diccionario offline para traducción
            words = text.lower().split()
            translated_words = []
            untranslated_words = []
            dictionary = self.dictionaries[target_lang]

            for word in words:
                # Se busca en el diccionario offline para la palabra actual
                translated_word = dictionary.get(word)
                if translated_word:
                    translated_words.append(translated_word)
                else:
                    translated_words.append(word)
                    untranslated_words.append(word)

            translation = ' '.join(translated_words)
            
            # Si hay palabras no traducidas, incluirlas en el mensaje
            if untranslated_words:
                return {
                    'status': 'partial',
                    'translation': translation,
                    'message': f'Traducción parcial. Palabras no encontradas en el diccionario: {", ".join(untranslated_words)}'
                }
            
            # Guardar para aprendizaje
            self.save_translation(text, translation, target_lang)
            
            return {
                'status': 'success',
                'translation': translation,
                'message': 'Traducción completada exitosamente'
            }

        except ValueError as ve:
            app.logger.warning(f'Error de validación: {str(ve)}')
            return {
                'status': 'error',
                'message': str(ve)
            }
        except Exception as e:
            app.logger.error(f'Error en la traducción: {str(e)}')
            return {
                'status': 'error',
                'message': 'Ocurrió un error durante la traducción. Por favor, inténtelo de nuevo.'
            }

    def save_translation(self, original_text, translation, target_lang):
        try:
            translations_file = DATA_DIR / f'{target_lang}_translations.json'
            translations = []
            
            if translations_file.exists():
                with open(translations_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
            
            translations.append({
                'original': original_text,
                'translation': translation,
                'verified': False
            })
            
            with open(translations_file, 'w', encoding='utf-8') as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            app.logger.warning(f'Error al guardar traducción: {str(e)}')

translator = IndigenousTranslator()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    try:
        if 'audio' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'Archivo de audio inválido'
            }), 400

        # Validación del idioma objetivo
        target_lang = request.form.get('target_lang')
        if not target_lang:
            return jsonify({
                'status': 'error',
                'message': 'No se especificó el idioma objetivo'
            }), 400

        if target_lang not in LENGUAS_META:
            return jsonify({
                'status': 'error',
                'message': f'Lengua indígena no soportada. Lenguas disponibles: {', '.join(LENGUAS_META.values())}'
            }), 400

        audio_file = request.files['audio']
        if not audio_file.filename:
            app.logger.warning('Nombre de archivo de audio inválido')
            return jsonify({
                'status': 'error',
                'message': 'Archivo de audio inválido'
            }), 400
            
        # Validación del tamaño del archivo
        if len(audio_file.read()) > 10 * 1024 * 1024:  # 10MB límite
            app.logger.warning('Archivo de audio demasiado grande')
            return jsonify({
                'status': 'error',
                'message': 'El archivo de audio es demasiado grande. Máximo 10MB'
            }), 400
        audio_file.seek(0)  # Reiniciar el puntero del archivo

        # Validar formato de audio
        allowed_extensions = {'wav', 'mp3', 'ogg'}
        if not audio_file.filename.lower().endswith(tuple(allowed_extensions)):
            return jsonify({
                'status': 'error',
                'message': f'Este formato de audio no está soportado. Use: {', '.join(allowed_extensions)}'
            }), 400

        # Guardar archivo temporalmente
        temp_path = 'temp_audio.wav'
        audio_file.save(temp_path)

        try:
            # Convertir audio a texto
            recognizer = Recognizer()
            with AudioFile(temp_path) as source:
                # Configurar parámetros optimizados para el reconocimiento
                recognizer.dynamic_energy_threshold = True
                recognizer.energy_threshold = 300
                recognizer.pause_threshold = 0.8
                recognizer.phrase_threshold = 0.3
                recognizer.operation_timeout = 30
                
                app.logger.info('Ajustando ruido ambiental...')
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                app.logger.info('Grabando audio...')
                audio = recognizer.record(source)
                
                app.logger.info('Reconociendo texto...')
                text = recognizer.recognize_google(audio, language='es-ES')
                
                app.logger.info(f'Texto reconocido: {text}')

            # Validar longitud del texto
            if len(text) > 1000:
                return jsonify({
                    'status': 'error',
                    'message': 'El texto es demasiado largo para traducir (máximo 1000 caracteres)',
                    'code': 'TEXT_TOO_LONG'
                }), 400

            # Validar y procesar el texto antes de traducir
            text = text.strip()
            if not text:
                return jsonify({
                    'status': 'error',
                    'message': 'El texto reconocido está vacío',
                    'code': 'EMPTY_TEXT'
                }), 400

            # Intentar traducir el texto
            translation_result = translator.translate(text, 'es', target_lang)
            
            if translation_result.get('status') == 'error':
                return jsonify({
                    'status': 'error',
                    'message': translation_result.get('message', 'Error en la traducción'),
                    'code': 'TRANSLATION_ERROR'
                }), 400

            translation = translation_result.get('translation')
            if not translation or not translation.strip():
                app.logger.warning('La traducción no produjo resultados')
                return jsonify({
                    'status': 'error',
                    'message': 'La traducción no produjo resultados',
                    'code': 'EMPTY_TRANSLATION'
                }), 400

            response = {
                'status': 'success',
                'original_text': text,
                'translated_text': translation,
                'target_language': LENGUAS_META[target_lang],
                'is_offline': True,
                'message': translation_result.get('message', '')
            }

            app.logger.info('Traducción completada exitosamente')
            return jsonify(response)

        except RequestError:
            app.logger.error('Error de conexión con el servicio de reconocimiento de voz')
            return jsonify({
                'status': 'error',
                'message': 'No se pudo conectar con el servicio de reconocimiento de voz. Por favor, verifica tu conexión a internet.',
                'suggestions': ['Verifica tu conexión a internet', 'Intenta de nuevo en unos momentos']
            }), 503

        except UnknownValueError:
            app.logger.error('No se pudo reconocer el audio')
            return jsonify({
                'status': 'error',
                'message': 'No se pudo entender el audio. Por favor, intenta de nuevo.',
                'suggestions': [
                    'Habla más cerca del micrófono',
                    'Evita ruidos de fondo',
                    'Habla claro y pausado',
                    'Asegúrate de que el micrófono esté funcionando correctamente'
                ]
            }), 400

        except Exception as e:
            app.logger.error(f'Error inesperado: {str(e)}')
            return jsonify({
                'status': 'error',
                'message': 'Ocurrió un error inesperado. Por favor, intenta de nuevo.',
                'details': str(e) if app.debug else None
            }), 500

        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        app.logger.error(f'Error general en process_audio: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Ocurrió un error al procesar el audio. Por favor, intenta de nuevo.',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/api/feedback', methods=['POST'])
def receive_feedback():
    try:
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No se recibieron datos de retroalimentación'
            }), 400

        required_fields = ['original_text', 'corrected_translation', 'target_lang']
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': 'Faltan campos requeridos en la retroalimentación'
            }), 400

        if data['target_lang'] not in LENGUAS_META:
            return jsonify({
                'status': 'error',
                'message': f'Lengua indígena no soportada: {data["target_lang"]}'
            }), 400

        # Cargar el diccionario existente
        dict_path = f'data/{data["target_lang"]}_dictionary.json'
        try:
            if os.path.exists(dict_path):
                with open(dict_path, 'r', encoding='utf-8') as f:
                    dictionary = json.load(f)
            else:
                dictionary = {}

            # Agregar o actualizar la traducción
            original_text = data['original_text'].lower().strip()
            dictionary[original_text] = {
                'traduccion': data['corrected_translation'],
                'explicacion': 'Agregado mediante retroalimentación del usuario'
            }

            # Guardar el diccionario actualizado
            with open(dict_path, 'w', encoding='utf-8') as f:
                json.dump(dictionary, f, ensure_ascii=False, indent=4)

            return jsonify({'status': 'success', 'message': 'Retroalimentación guardada exitosamente'})

        except Exception as e:
            app.logger.error(f'Error al guardar retroalimentación: {str(e)}')
            return jsonify({
                'status': 'error',
                'message': 'Error al guardar la retroalimentación'
            }), 500

    except Exception as e:
        app.logger.error(f'Error al procesar retroalimentación: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Error al procesar la retroalimentación'
        }), 500

@app.route('/api/translate-text', methods=['POST'])
def translate_text_endpoint():
    try:
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No se recibieron datos para traducir'
            }), 400

        text = data.get('text')
        target_lang = data.get('target_lang')

        if not text or not text.strip():
            return jsonify({
                'status': 'error',
                'message': 'El texto a traducir está vacío'
            }), 400

        if not target_lang:
            return jsonify({
                'status': 'error',
                'message': 'No se especificó el idioma objetivo'
            }), 400

        if target_lang not in LENGUAS_META:
            return jsonify({
                'status': 'error',
                'message': f'Lengua indígena no soportada. Lenguas disponibles: {', '.join(LENGUAS_META.values())}'
            }), 400

        # Validar longitud del texto
        if len(text) > 1000:
            return jsonify({
                'status': 'error',
                'message': 'El texto es demasiado largo para traducir (máximo 1000 caracteres)',
                'code': 'TEXT_TOO_LONG'
            }), 400

        # Normalizar el texto antes de traducir
        text = text.lower().strip()
        
        # Cargar el diccionario correspondiente al idioma seleccionado
        try:
            dict_path = f'data/{target_lang}_dictionary.json'
            if not os.path.exists(dict_path):
                return jsonify({
                    'status': 'error',
                    'message': f'No se encontró el diccionario para {LENGUAS_META[target_lang]}',
                    'code': 'DICTIONARY_NOT_FOUND'
                }), 404

            with open(dict_path, 'r', encoding='utf-8') as f:
                dictionary = json.load(f)
        except Exception as e:
            app.logger.error(f'Error al cargar el diccionario: {str(e)}')
            return jsonify({
                'status': 'error',
                'message': 'Error al cargar el diccionario de traducción',
                'code': 'DICTIONARY_ERROR'
            }), 500

        # Buscar la traducción en el diccionario
        if text in dictionary:
            translation = dictionary[text]['traduccion']
            return jsonify({
                'status': 'success',
                'translation': translation,
                'message': 'Traducción completada exitosamente'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No se encontró una traducción para el texto proporcionado',
                'code': 'NO_TRANSLATION'
            }), 404

    except Exception as e:
        app.logger.error(f'Error en la traducción de texto: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Ocurrió un error al procesar la traducción. Por favor, intente de nuevo.',
            'details': str(e) if app.debug else None
        }), 500

if __name__ == '__main__':
    app.run(debug=True)