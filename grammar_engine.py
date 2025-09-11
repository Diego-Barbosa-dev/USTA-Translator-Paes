import re
import json
from typing import Dict, List, Tuple, Optional

class ConjugationEngine:
    def __init__(self, dictionary_path: str):
        self.dictionary_path = dictionary_path
        self.dictionary = self.load_dictionary()
        self.verb_patterns = self.identify_verb_patterns()
        self.spanish_conjugations = self.load_spanish_conjugations()
        self.noun_patterns = self.load_noun_patterns()
        self.adjective_patterns = self.load_adjective_patterns()
        self.nasa_yuwe_grammar = self.load_nasa_yuwe_grammar()
        
    def load_dictionary(self) -> Dict:
        """Cargar el diccionario de Nasa Yuwe"""
        try:
            with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def identify_verb_patterns(self) -> Dict[str, List[str]]:
        """Identificar patrones de verbos en Nasa Yuwe"""
        patterns = {
            'transitive_verbs': [],  # verbos que terminan en -
            'intransitive_verbs': [], # verbos intransitivos
            'action_verbs': []       # verbos de acción
        }
        
        for spanish_word, data in self.dictionary.items():
            nasa_word = data['traduccion']
            explanation = data.get('explanation', '').lower()
            
            # Identificar verbos transitivos (terminan en -)
            if nasa_word.endswith('-'):
                if 'transitivo' in explanation:
                    patterns['transitive_verbs'].append((spanish_word, nasa_word))
                elif 'intransitivo' in explanation:
                    patterns['intransitive_verbs'].append((spanish_word, nasa_word))
                else:
                    patterns['action_verbs'].append((spanish_word, nasa_word))
        
        return patterns
    
    def load_spanish_conjugations(self) -> Dict:
        """Reglas básicas de conjugación en español"""
        return {
            'ar_verbs': {
                'yo': 'o',
                'tú': 'as', 
                'él/ella': 'a',
                'nosotros': 'amos',
                'vosotros': 'áis',
                'ellos': 'an'
            },
            'er_verbs': {
                'yo': 'o',
                'tú': 'es',
                'él/ella': 'e', 
                'nosotros': 'emos',
                'vosotros': 'éis',
                'ellos': 'en'
            },
            'ir_verbs': {
                'yo': 'o',
                'tú': 'es',
                'él/ella': 'e',
                'nosotros': 'imos', 
                'vosotros': 'ís',
                'ellos': 'en'
            }
        }
    
    def load_noun_patterns(self) -> Dict:
        """Cargar patrones de sustantivos para pluralización y género"""
        return {
            'spanish': {
                'plural_rules': [
                    {'pattern': r'([aeiou])$', 'replacement': r'\1s'},  # casa -> casas
                    {'pattern': r'([^aeiou])$', 'replacement': r'\1es'},  # árbol -> árboles
                    {'pattern': r'z$', 'replacement': 'ces'},  # luz -> luces
                ],
                'gender_rules': [
                    {'pattern': r'o$', 'gender': 'masculine'},
                    {'pattern': r'a$', 'gender': 'feminine'},
                    {'pattern': r'e$', 'gender': 'neutral'}
                ]
            },
            'nasa_yuwe': {
                'plural_rules': [
                    {'pattern': r'$', 'replacement': 'we'},  # Regla básica de pluralización
                ],
                'collective_markers': ['txi', 'txiwe']  # Marcadores colectivos
            }
        }
    
    def load_adjective_patterns(self) -> Dict:
        """Cargar patrones de adjetivos para concordancia"""
        return {
            'spanish': {
                'agreement_rules': [
                    {'pattern': r'o$', 'feminine': 'a', 'plural_masc': 'os', 'plural_fem': 'as'},
                    {'pattern': r'e$', 'feminine': 'e', 'plural_masc': 'es', 'plural_fem': 'es'},
                ]
            },
            'nasa_yuwe': {
                'descriptive_suffixes': ['sa', 'te', 'yu']  # Sufijos descriptivos comunes
            }
        }
    
    def load_nasa_yuwe_grammar(self) -> Dict:
        """Cargar reglas gramaticales específicas del Nasa Yuwe"""
        return {
            'verb_suffixes': {
                'present': ['n', 'te', 'sa', 'we'],
                'past': ['tx', 'txi', 'txin', 'txiwe'],
                'future': ['we', 'wes', 'wet', 'wesx'],
                'imperative': ['ka', 'ki', 'ku']
            },
            'person_markers': {
                '1sg': 'ũ',     # yo
                '2sg': 'um',    # tú
                '3sg': 'nas',   # él/ella
                '1pl': 'ũs',    # nosotros (inclusivo)
                '1pl_excl': 'ũh', # nosotros (exclusivo)
                '2pl': 'ums',   # ustedes
                '3pl': 'nasa'   # ellos/ellas
            },
            'aspect_markers': {
                'completive': 'tx',
                'continuative': 'sa',
                'habitual': 'te',
                'iterative': 'txi',
                'intensive': 'sx'
            },
            'directional_markers': {
                'up': 'ksxa',
                'down': 'jxu',
                'towards_speaker': 'yu',
                'away_from_speaker': 'pa',
                'inside': 'pila',
                'outside': 'wala'
            },
            'temporal_markers': {
                'morning': 'uma',
                'afternoon': 'tay',
                'night': 'akx',
                'yesterday': 'ksxaw',
                'today': 'jxuka',
                'tomorrow': 'wejxa'
            },
            'question_particles': {
                'what': 'kwe',
                'who': 'jĩ',
                'where': 'naa',
                'when': 'kãjã',
                'how': 'kãh',
                'why': 'kwesx'
            },
            'negation': {
                'not': 'kwe',
                'never': 'kwesx',
                'nothing': 'kwekwe'
            }
        }
    
    def get_verb_root(self, verb: str) -> Tuple[str, str]:
        """Obtener la raíz del verbo y su tipo"""
        verb = verb.lower().strip()
        
        if verb.endswith('ar'):
            return verb[:-2], 'ar'
        elif verb.endswith('er'):
            return verb[:-2], 'er'
        elif verb.endswith('ir'):
            return verb[:-2], 'ir'
        else:
            return verb, 'irregular'
    
    def conjugate_spanish_verb(self, verb: str, person: str = 'él/ella') -> str:
        """Conjugar verbo en español"""
        root, verb_type = self.get_verb_root(verb)
        
        if verb_type == 'irregular':
            return verb  # Devolver sin cambios si es irregular
        
        conjugation_rules = self.spanish_conjugations.get(f'{verb_type}_verbs', {})
        ending = conjugation_rules.get(person, '')
        
        return root + ending
    
    def conjugate_nasa_yuwe_verb(self, nasa_verb: str, context: str = 'present') -> str:
        """Conjugar verbo en Nasa Yuwe (básico)"""
        # Reglas básicas observadas en el diccionario
        if nasa_verb.endswith('-'):
            root = nasa_verb[:-1]
            
            # Agregar sufijos básicos según el contexto
            if context == 'present':
                return root + 'we'  # forma presente
            elif context == 'past':
                return root + 'ka'  # forma pasada
            elif context == 'future':
                return root + 'sa'  # forma futura
        
        return nasa_verb
    
    def detect_conjugated_form(self, word: str) -> Optional[Tuple[str, str]]:
        """Detectar si una palabra está conjugada y encontrar su forma base"""
        word_lower = word.lower()
        
        # Buscar en el diccionario primero
        for spanish_word, data in self.dictionary.items():
            if spanish_word.lower() == word_lower:
                return spanish_word, data['traduccion']
        
        # Intentar detectar conjugaciones en español
        spanish_endings = ['o', 'as', 'a', 'amos', 'áis', 'an', 'es', 'e', 'emos', 'éis', 'en', 'imos', 'ís']
        
        for ending in spanish_endings:
            if word_lower.endswith(ending) and len(word_lower) > len(ending) + 2:
                possible_root = word_lower[:-len(ending)]
                
                # Probar diferentes terminaciones de infinitivo
                for inf_ending in ['ar', 'er', 'ir']:
                    infinitive = possible_root + inf_ending
                    
                    # Buscar el infinitivo en el diccionario
                    for spanish_word, data in self.dictionary.items():
                        if spanish_word.lower() == infinitive:
                            return spanish_word, data['traduccion']
        
        return None
    
    def pluralize_spanish(self, word: str) -> str:
        """Pluralizar sustantivos en español"""
        word_lower = word.lower()
        
        if word_lower.endswith(('a', 'e', 'i', 'o', 'u')):
            return word + 's'
        elif word_lower.endswith('z'):
            return word[:-1] + 'ces'
        else:
            return word + 'es'
    
    def pluralize_nasa_yuwe(self, word: str) -> str:
        """Pluralizar sustantivos en Nasa Yuwe (reglas básicas)"""
        # Reglas observadas: algunos plurales se forman con sufijos
        if word.endswith("'"):
            return word + 'we'  # plural para palabras que terminan en '
        else:
            return word + 'we'  # sufijo general de plural
    
    def pluralize_spanish_noun(self, noun: str) -> str:
        """Pluralizar un sustantivo en español"""
        for rule in self.noun_patterns['spanish']['plural_rules']:
            if re.search(rule['pattern'], noun):
                return re.sub(rule['pattern'], rule['replacement'], noun)
        return noun + 's'  # Regla por defecto
    
    def pluralize_nasa_yuwe_noun(self, noun: str) -> str:
        """Pluralizar un sustantivo en Nasa Yuwe"""
        # Regla básica: agregar 'we' al final
        return noun + 'we'
    
    def get_noun_gender(self, noun: str) -> str:
        """Determinar el género de un sustantivo español"""
        for rule in self.noun_patterns['spanish']['gender_rules']:
            if re.search(rule['pattern'], noun):
                return rule['gender']
        return 'neutral'
    
    def conjugate_adjective_spanish(self, adjective: str, gender: str = 'masculine', number: str = 'singular') -> str:
        """Conjugar un adjetivo español según género y número"""
        for rule in self.adjective_patterns['spanish']['agreement_rules']:
            if re.search(rule['pattern'], adjective):
                root = re.sub(rule['pattern'], '', adjective)
                if gender == 'feminine' and number == 'singular':
                    return root + rule['feminine']
                elif gender == 'masculine' and number == 'plural':
                    return root + rule['plural_masc']
                elif gender == 'feminine' and number == 'plural':
                    return root + rule['plural_fem']
        return adjective
    
    def detect_word_type(self, word: str) -> str:
        """Detectar el tipo de palabra (verbo, sustantivo, adjetivo)"""
        # Detectar verbos por terminaciones
        if re.search(r'(ar|er|ir)$', word):
            return 'verb'
        
        # Detectar sustantivos por contexto en el diccionario
        if word in self.dictionary:
            explanation = self.dictionary[word].get('explicacion', '').lower()
            if any(marker in explanation for marker in ['sustantivo', 'nombre', 'cosa']):
                return 'noun'
            elif any(marker in explanation for marker in ['adjetivo', 'cualidad', 'describe']):
                return 'adjective'
            elif any(marker in explanation for marker in ['verbo', 'acción', 'hacer']):
                return 'verb'
        
        # Detectar por terminaciones comunes
        if re.search(r'(ción|sión|dad|tad|eza|ura|ancia|encia)$', word):
            return 'noun'
        elif re.search(r'(oso|osa|ivo|iva|able|ible|ante|ente)$', word):
            return 'adjective'
        
        return 'unknown'
    
    def translate_noun_with_features(self, noun: str, source_lang: str, target_lang: str) -> str:
        """Traducir sustantivo considerando plural y género"""
        # Detectar si es plural
        is_plural = False
        base_noun = noun
        
        if source_lang == 'spanish':
            # Detectar plural en español
            if noun.endswith('s') and len(noun) > 1:
                is_plural = True
                # Intentar obtener la forma singular
                if noun.endswith('es'):
                    base_noun = noun[:-2]
                else:
                    base_noun = noun[:-1]
        
        # Buscar traducción de la forma base
        if source_lang == 'spanish':
            # Buscar con insensibilidad a mayúsculas/minúsculas
            translation = base_noun
            for spanish_word, data in self.dictionary.items():
                if spanish_word.lower() == base_noun.lower():
                    translation = data['traduccion']
                    break
        elif source_lang == 'nasa_yuwe':
            # Buscar en el diccionario inverso
            translation = base_noun
            for spanish_word, data in self.dictionary.items():
                if data['traduccion'].lower() == base_noun.lower():
                    translation = spanish_word
                    break
        else:
            translation = base_noun
        
        # Aplicar pluralización si es necesario
        if is_plural and target_lang == 'nasa_yuwe':
            translation = self.pluralize_nasa_yuwe_noun(translation)
        elif is_plural and target_lang == 'spanish':
            translation = self.pluralize_spanish_noun(translation)
        
        return translation
    
    def translate_adjective_with_agreement(self, adjective: str, source_lang: str, target_lang: str, context_words: List[str], position: int) -> str:
        """Traducir adjetivo considerando concordancia"""
        # Obtener traducción base
        if source_lang == 'spanish':
            # Buscar con insensibilidad a mayúsculas/minúsculas
            translation = adjective
            for spanish_word, data in self.dictionary.items():
                if spanish_word.lower() == adjective.lower():
                    translation = data['traduccion']
                    break
        elif source_lang == 'nasa_yuwe':
            # Buscar en el diccionario inverso
            translation = adjective
            for spanish_word, data in self.dictionary.items():
                if data['traduccion'].lower() == adjective.lower():
                    translation = spanish_word
                    break
        else:
            translation = adjective
        
        # En Nasa Yuwe, los adjetivos generalmente no cambian por género/número
        # pero pueden tener sufijos descriptivos
        if target_lang == 'nasa_yuwe':
            # Agregar sufijo descriptivo si no lo tiene
            if not any(translation.endswith(suffix) for suffix in self.adjective_patterns['nasa_yuwe']['descriptive_suffixes']):
                translation += 'sa'  # Sufijo descriptivo común
        
        return translation
    
    def enhance_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        """Mejorar traducción con conjugaciones y reglas gramaticales"""
        words = text.split()
        translated_words = []
        
        for i, word in enumerate(words):
            # Limpiar puntuación
            clean_word = re.sub(r'[^\w\s]', '', word)
            punctuation = word[len(clean_word):] if len(word) > len(clean_word) else ''
            
            word_type = self.detect_word_type(clean_word)
            
            # Manejar diferentes tipos de palabras
            if word_type == 'verb':
                if source_lang == 'spanish':
                    # Buscar con insensibilidad a mayúsculas/minúsculas
                    translation = clean_word
                    for spanish_word, data in self.dictionary.items():
                        if spanish_word.lower() == clean_word.lower():
                            translation = data['traduccion']
                            break
                elif source_lang == 'nasa_yuwe':
                    # Buscar en el diccionario inverso
                    translation = clean_word
                    for spanish_word, data in self.dictionary.items():
                        if data['traduccion'].lower() == clean_word.lower():
                            translation = spanish_word
                            break
                else:
                    translation = clean_word
            elif word_type == 'noun':
                translation = self.translate_noun_with_features(clean_word, source_lang, target_lang)
            elif word_type == 'adjective':
                translation = self.translate_adjective_with_agreement(clean_word, source_lang, target_lang, words, i)
            else:
                # Traducción básica para palabras no identificadas
                if source_lang == 'spanish':
                    # Buscar con insensibilidad a mayúsculas/minúsculas
                    translation = clean_word
                    for spanish_word, data in self.dictionary.items():
                        if spanish_word.lower() == clean_word.lower():
                            translation = data['traduccion']
                            break
                elif source_lang == 'nasa_yuwe':
                    # Buscar en el diccionario inverso
                    translation = clean_word
                    for spanish_word, data in self.dictionary.items():
                        if data['traduccion'].lower() == clean_word.lower():
                            translation = spanish_word
                            break
                else:
                    translation = clean_word
            
            translated_words.append(translation + punctuation)
        
        return ' '.join(translated_words)
    
    def detect_temporal_context(self, text: str, source_lang: str) -> Dict:
        """Detectar contexto temporal en el texto"""
        temporal_info = {'markers': [], 'tense': 'present'}
        
        if source_lang == 'spanish':
            # Detectar marcadores temporales en español
            temporal_spanish = {
                'ayer': 'past',
                'hoy': 'present', 
                'mañana': 'future',
                'ahora': 'present',
                'antes': 'past',
                'después': 'future',
                'en la mañana': 'morning',
                'en la tarde': 'afternoon',
                'en la noche': 'night'
            }
            
            text_lower = text.lower()
            for spanish_marker, tense in temporal_spanish.items():
                if spanish_marker in text_lower:
                    temporal_info['markers'].append(spanish_marker)
                    if tense in ['past', 'present', 'future']:
                        temporal_info['tense'] = tense
        
        return temporal_info
    
    def detect_question_type(self, text: str, source_lang: str) -> Dict:
        """Detectar tipo de pregunta"""
        question_info = {'is_question': False, 'type': None, 'particle': None}
        
        if source_lang == 'spanish':
            question_words = {
                'qué': 'what',
                'quién': 'who', 
                'dónde': 'where',
                'cuándo': 'when',
                'cómo': 'how',
                'por qué': 'why'
            }
            
            text_lower = text.lower()
            
            # Detectar si termina en ?
            if text.strip().endswith('?'):
                question_info['is_question'] = True
            
            # Detectar tipo de pregunta
            for spanish_q, q_type in question_words.items():
                if spanish_q in text_lower:
                    question_info['is_question'] = True
                    question_info['type'] = q_type
                    question_info['particle'] = self.nasa_yuwe_grammar['question_particles'][q_type]
                    break
        
        return question_info
    
    def apply_nasa_yuwe_morphology(self, word: str, morphology: Dict) -> str:
        """Aplicar morfología específica del Nasa Yuwe"""
        result = word
        
        # Aplicar marcadores de persona
        if 'person' in morphology:
            person_marker = self.nasa_yuwe_grammar['person_markers'].get(morphology['person'])
            if person_marker:
                result = person_marker + ' ' + result
        
        # Aplicar marcadores de aspecto
        if 'aspect' in morphology:
            aspect_marker = self.nasa_yuwe_grammar['aspect_markers'].get(morphology['aspect'])
            if aspect_marker:
                result = result + aspect_marker
        
        # Aplicar marcadores direccionales
        if 'direction' in morphology:
            dir_marker = self.nasa_yuwe_grammar['directional_markers'].get(morphology['direction'])
            if dir_marker:
                result = result + ' ' + dir_marker
        
        # Aplicar negación
        if morphology.get('negated', False):
            neg_marker = self.nasa_yuwe_grammar['negation']['not']
            result = neg_marker + ' ' + result
        
        return result
    
    def enhanced_contextual_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        """Traducción contextual mejorada usando todos los patrones gramaticales"""
        if source_lang == target_lang:
            return text
        
        # Detectar contexto
        temporal_context = self.detect_temporal_context(text, source_lang)
        question_context = self.detect_question_type(text, source_lang)
        
        # Traducción base
        base_translation = self.enhance_translation(text, source_lang, target_lang)
        
        if target_lang == 'nasa_yuwe':
            # Aplicar mejoras específicas para Nasa Yuwe
            
            # Agregar partículas de pregunta si es necesario
            if question_context['is_question'] and question_context['particle']:
                base_translation = question_context['particle'] + ' ' + base_translation
            
            # Agregar marcadores temporales
            if temporal_context['markers']:
                temporal_nasa = self.nasa_yuwe_grammar['temporal_markers']
                for marker in temporal_context['markers']:
                    if marker == 'ayer' and 'yesterday' in temporal_nasa:
                        base_translation = temporal_nasa['yesterday'] + ' ' + base_translation
                    elif marker == 'mañana' and 'tomorrow' in temporal_nasa:
                        base_translation = temporal_nasa['tomorrow'] + ' ' + base_translation
        
        return base_translation
    
    def translate_spanish_to_nasa_yuwe(self, word: str) -> str:
        """Traducir palabra del español al Nasa Yuwe con conjugaciones"""
        # Buscar traducción directa primero
        for spanish_word, data in self.dictionary.items():
            if spanish_word.lower() == word.lower():
                return data['traduccion']
        
        # Intentar detectar conjugación
        conjugation_result = self.detect_conjugated_form(word)
        if conjugation_result:
            base_spanish, base_nasa = conjugation_result
            # Aplicar conjugación en Nasa Yuwe
            return self.conjugate_nasa_yuwe_verb(base_nasa, 'present')
        
        # Intentar pluralización
        if word.lower().endswith('s') and len(word) > 2:
            singular = word[:-1]
            for spanish_word, data in self.dictionary.items():
                if spanish_word.lower() == singular.lower():
                    return self.pluralize_nasa_yuwe(data['traduccion'])
        
        return word  # Devolver sin cambios si no se encuentra
    
    def translate_nasa_yuwe_to_spanish(self, word: str) -> str:
        """Traducir palabra del Nasa Yuwe al español con conjugaciones"""
        # Buscar traducción directa (inversa)
        for spanish_word, data in self.dictionary.items():
            if data['traduccion'].lower() == word.lower():
                return spanish_word
        
        # Intentar detectar conjugación en Nasa Yuwe
        if word.endswith('we') and len(word) > 3:
            possible_root = word[:-2] + '-'
            for spanish_word, data in self.dictionary.items():
                if data['traduccion'].lower() == possible_root.lower():
                    return self.conjugate_spanish_verb(spanish_word, 'él/ella')
        
        return word  # Devolver sin cambios si no se encuentra