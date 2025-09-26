from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import os
import json
from typing import Dict
from grammar_engine import ConjugationEngine
import logging

class AdvancedTranslationModel:
    """
    Modelo de traducción avanzado que combina:
    1. Modelo NLLB-200 para traducción contextual
    2. Diccionario personalizado para términos específicos
    3. Motor gramatical para reglas del Nasa Yuwe
    """
    
    def __init__(self, dictionary_path='data/nasa_yuwe_dictionary.json'):
        self.dictionary_path = dictionary_path
        self.model = None
        self.tokenizer = None
        self.dictionary = {}
        self.grammar_engine = None
        self.model_loaded = False
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Inicializar componentes
        self._load_dictionary()
        self._initialize_grammar_engine()
        self._load_nllb_model()
    
    def _load_dictionary(self):
        """Cargar el diccionario personalizado de Nasa Yuwe"""
        try:
            if os.path.exists(self.dictionary_path):
                with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                    self.dictionary = json.load(f)
                self.logger.info(f"Diccionario cargado: {len(self.dictionary)} entradas")
            else:
                self.logger.warning("Diccionario no encontrado, usando diccionario vacío")
        except Exception as e:
            self.logger.error(f"Error cargando diccionario: {e}")
    
    def _initialize_grammar_engine(self):
        """Inicializar el motor gramatical"""
        try:
            self.grammar_engine = ConjugationEngine(self.dictionary_path)
            self.logger.info("Motor gramatical inicializado")
        except Exception as e:
            self.logger.error(f"Error inicializando motor gramatical: {e}")
    
    def _load_nllb_model(self):
        """Cargar el modelo NLLB-200 si está disponible"""
        model_path = "models/nllb-200-distilled-600M"
        
        try:
            if os.path.exists(model_path):
                self.logger.info("Cargando modelo NLLB-200...")
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
                
                # Configurar dispositivo (CPU/GPU)
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                self.model.to(self.device)
                
                self.model_loaded = True
                self.logger.info(f"Modelo NLLB-200 cargado en {self.device}")
            else:
                self.logger.warning("Modelo NLLB-200 no encontrado, usando solo diccionario")
        except Exception as e:
            self.logger.error(f"Error cargando modelo NLLB-200: {e}")
            self.model_loaded = False
    
    def _get_language_code(self, lang):
        """Obtener códigos de idioma para NLLB"""
        language_codes = {
            'spanish': 'spa_Latn',
            'nasa_yuwe': 'spa_Latn'  # Fallback a español por falta de soporte directo
        }
        return language_codes.get(lang, 'spa_Latn')
    
    def _translate_with_dictionary(self, text, source_lang, target_lang):
        """Traducción usando el diccionario personalizado"""
        if not self.dictionary:
            return None
            
        words = text.lower().split()
        translated_words = []
        found_translations = False
        
        if source_lang == 'spanish' and target_lang == 'nasa_yuwe':
            for word in words:
                if word in self.dictionary:
                    translated_words.append(self.dictionary[word]['traduccion'])
                    found_translations = True
                else:
                    translated_words.append(word)
        
        elif source_lang == 'nasa_yuwe' and target_lang == 'spanish':
            # Crear diccionario inverso
            reverse_dict = {}
            for spanish_word, data in self.dictionary.items():
                nasa_word = data['traduccion'].lower()
                reverse_dict[nasa_word] = spanish_word
            
            for word in words:
                if word in reverse_dict:
                    translated_words.append(reverse_dict[word])
                    found_translations = True
                else:
                    translated_words.append(word)
        
        if found_translations:
            result = ' '.join(translated_words)
            return {
                'translation': result,
                'method': 'dictionary',
                'confidence': 0.80,
                'tried_methods': ['dictionary']
            }
        
        return None
    
    def _translate_with_nllb(self, text, source_lang, target_lang):
        """Traducción usando el modelo NLLB-200"""
        if not self.model_loaded:
            return None
        
        try:
            # Preparar el texto para NLLB
            src_lang = self._get_language_code(source_lang)
            tgt_lang = self._get_language_code(target_lang)
            
            # Tokenizar
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generar traducción
            with torch.no_grad():
                generated_tokens = self.model.generate(
                    **inputs,
                    forced_bos_token_id=self.tokenizer.lang_code_to_id[tgt_lang],
                    max_length=512,
                    num_beams=5,
                    early_stopping=True
                )
            
            # Decodificar resultado
            translation = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            return translation.strip()
            
        except Exception as e:
            self.logger.error(f"Error en traducción NLLB: {e}")
            return None
    
    def _translate_with_grammar(self, text: str, source_lang: str, target_lang: str) -> Dict:
        """Traducir usando el motor gramatical"""
        if self.grammar_engine:
            try:
                # Intentar con el método contextual mejorado primero
                enhanced = self.grammar_engine.enhanced_contextual_translation(text, source_lang, target_lang)
                if enhanced and enhanced != text:
                    return {
                        'translation': enhanced,
                        'method': 'enhanced_grammar',
                        'confidence': 0.90,
                        'tried_methods': ['enhanced_grammar']
                    }
                
                # Fallback al método original
                enhanced = self.grammar_engine.enhance_translation(text, source_lang, target_lang)
                if enhanced and enhanced != text:
                    return {
                        'translation': enhanced,
                        'method': 'grammar',
                        'confidence': 0.90,
                        'tried_methods': ['enhanced_grammar', 'grammar']
                    }
            except Exception as e:
                print(f"Error en motor gramatical: {e}")
        return None
    
    def translate(self, text, source_lang='spanish', target_lang='nasa_yuwe'):
        """Traducción híbrida usando múltiples métodos"""
        if not text or not text.strip():
            return {'translation': '', 'method': 'empty', 'confidence': 0}
        
        text = text.strip()
        
        # Intentar diferentes métodos de traducción en orden de prioridad
        
        # 1. Intentar con diccionario personalizado (mayor precisión)
        dict_result = self._translate_with_dictionary(text, source_lang, target_lang)
        if dict_result:
            return dict_result
        
        # 2. Intentar con motor gramatical mejorado
        grammar_result = self._translate_with_grammar(text, source_lang, target_lang)
        if grammar_result:
            return grammar_result
        
        # 3. Intentar con NLLB (solo para español-español como fallback)
        if self.model_loaded and source_lang == 'spanish':
            nllb_translation = self._translate_with_nllb(text, source_lang, 'spanish')
            if nllb_translation and nllb_translation != text:
                return {
                    'translation': nllb_translation,
                    'method': 'nllb',
                    'confidence': 0.7,
                    'tried_methods': ['dictionary', 'grammar', 'nllb']
                }
        
        # Fallback: devolver texto original
        return {
            'translation': text,
            'method': 'fallback',
            'confidence': 0.1,
            'tried_methods': ['dictionary', 'grammar', 'nllb']
        }
    
    def get_model_info(self):
        """Obtener información sobre el estado del modelo"""
        return {
            'nllb_loaded': self.model_loaded,
            'dictionary_entries': len(self.dictionary),
            'grammar_engine_loaded': self.grammar_engine is not None,
            'device': str(self.device) if self.model_loaded else 'N/A'
        }