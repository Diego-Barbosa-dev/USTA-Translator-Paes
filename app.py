from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import json
from grammar_engine import ConjugationEngine

app = Flask(__name__)

# Inicializar el motor de conjugación
conjugation_engine = None

def get_conjugation_engine():
    global conjugation_engine
    if conjugation_engine is None:
        nasa_yuwe_dictionary_path = os.path.join('data', 'nasa_yuwe_dictionary.json')
        conjugation_engine = ConjugationEngine(nasa_yuwe_dictionary_path)
    return conjugation_engine

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/translate-text', methods=['POST'])
def translate_text_endpoint():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        source_lang = data.get('source_lang', 'spanish')
        target_lang = data.get('target_lang', 'sikuani')

        if not text:
            return jsonify({'error': 'No se proporcionó texto para traducir'})

        if source_lang == target_lang:
            return jsonify({'error': 'El idioma de origen y destino no pueden ser iguales'})

        # Normalizar el texto de entrada
        text = text.lower()

        # Cargar el diccionario de Nasa Yuwe
        nasa_yuwe_dictionary_path = os.path.join('data', 'nasa_yuwe_dictionary.json')

        try:
            with open(nasa_yuwe_dictionary_path, 'r', encoding='utf-8') as f:
                dictionary = json.load(f)
            
            if source_lang == 'spanish' and target_lang == 'nasa_yuwe':
                translation = translate_to_indigenous(text, dictionary)
            elif source_lang == 'nasa_yuwe' and target_lang == 'spanish':
                translation = translate_to_spanish(text, dictionary)
            else:
                return jsonify({
                    'error': 'Solo se admite traducción entre Español y Nasa Yuwe'
                })

            return jsonify({
                'translation': translation,
                'status': 'success'
            })

        except FileNotFoundError:
            return jsonify({
                'error': 'Diccionario de Nasa Yuwe no encontrado'
            })

    except Exception as e:
        return jsonify({'error': str(e)})



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
        
        # Cargar el diccionario actual
        dictionary_path = os.path.join('data', 'nasa_yuwe_dictionary.json')
        
        try:
            with open(dictionary_path, 'r', encoding='utf-8') as f:
                dictionary = json.load(f)
        except FileNotFoundError:
            dictionary = {}
        
        # Verificar si la palabra ya existe (case-insensitive)
        spanish_word_lower = spanish_word.lower()
        existing_word = None
        for word in dictionary.keys():
            if word.lower() == spanish_word_lower:
                existing_word = word
                break
        
        if existing_word:
            return jsonify({'error': f'La palabra "{existing_word}" ya existe en el diccionario'}), 409
        
        # Agregar la nueva palabra al diccionario
        dictionary[spanish_word] = {
            'traduccion': nasa_yuwe_translation,
            'explanation': context
        }
        
        # Guardar el diccionario actualizado
        with open(dictionary_path, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, ensure_ascii=False, indent=4)
        
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

        # Solo trabajamos con el diccionario de Nasa Yuwe
        dictionary_path = os.path.join('data', 'nasa_yuwe_dictionary.json')

        try:
            # Cargar el diccionario existente
            with open(dictionary_path, 'r', encoding='utf-8') as f:
                dictionary = json.load(f)

            # Normalizar textos
            original_text_lower = original_text.lower()
            corrected_translation_lower = corrected_translation.lower()

            if source_lang == 'spanish' and target_lang == 'nasa_yuwe':
                # Buscar si ya existe una entrada para esta palabra en español
                entry_found = False
                for key in dictionary.keys():
                    if key.lower() == original_text_lower:
                        # Actualizar la traducción existente
                        dictionary[key]['traduccion'] = corrected_translation
                        entry_found = True
                        break
                
                # Si no se encontró, crear nueva entrada
                if not entry_found:
                    dictionary[original_text] = {
                        'traduccion': corrected_translation,
                        'explanation': 'Agregado por retroalimentación de usuario'
                    }
            
            elif source_lang == 'nasa_yuwe' and target_lang == 'spanish':
                # Buscar la entrada que tiene esta traducción en Nasa Yuwe
                entry_found = False
                for spanish_word, data in dictionary.items():
                    if data['traduccion'].lower() == original_text_lower:
                        # Actualizar la palabra en español (clave del diccionario)
                        # Crear nueva entrada con la palabra corregida
                        dictionary[corrected_translation] = {
                            'traduccion': data['traduccion'],
                            'explanation': data.get('explanation', '')
                        }
                        # Eliminar la entrada anterior si es diferente
                        if spanish_word.lower() != corrected_translation.lower():
                            del dictionary[spanish_word]
                        entry_found = True
                        break
                
                # Si no se encontró, crear nueva entrada
                if not entry_found:
                    dictionary[corrected_translation] = {
                        'traduccion': original_text,
                        'explanation': 'Agregado por retroalimentación de usuario'
                    }

            # Guardar el diccionario actualizado
            with open(dictionary_path, 'w', encoding='utf-8') as f:
                json.dump(dictionary, f, ensure_ascii=False, indent=4)

            return jsonify({'status': 'success', 'message': 'Retroalimentación guardada exitosamente'})

        except Exception as e:
            return jsonify({'error': f'Error al procesar la retroalimentación: {str(e)}'})

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    # Asegurarse de que el directorio de datos existe
    os.makedirs('data', exist_ok=True)
    app.run(debug=True)