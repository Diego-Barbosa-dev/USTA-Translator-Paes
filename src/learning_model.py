from pathlib import Path
import json
import random
from typing import List, Dict, Optional

class LearningUnit:
    def __init__(self, title: str, description: str, difficulty: int):
        self.title = title
        self.description = description
        self.difficulty = difficulty
        self.exercises: List[Exercise] = []
        self.completed = False
        self.score = 0

class Exercise:
    def __init__(self, type: str, question: str, correct_answer: str,
                 options: List[str], image_path: Optional[str] = None):
        self.type = type  # 'multiple_choice', 'translation', 'listening'
        self.question = question
        self.correct_answer = correct_answer
        self.options = options
        self.image_path = image_path
        self.completed = False

class NasaLearningModel:
    def __init__(self):
        self.data_dir = Path('data')
        self.units: List[LearningUnit] = []
        self.current_unit_index = 0
        self.total_score = 0
        self.dictionary: Dict[str, Dict[str, List[str]]] = {}
        self.load_dictionary()
        self.initialize_learning_units()

    def load_dictionary(self):
        try:
            dict_path = self.data_dir / 'nasa_dictionary.json'
            if dict_path.exists():
                with open(dict_path, 'r', encoding='utf-8') as f:
                    self.dictionary = json.load(f)
        except Exception as e:
            print(f'Error al cargar diccionario Nasa: {str(e)}')
            self.dictionary = {}

    def initialize_learning_units(self):
        # Unidades de aprendizaje básicas
        basic_units = [
            {
                'title': 'Saludos y Presentaciones',
                'description': 'Aprende saludos básicos en Nasa',
                'difficulty': 1,
                'exercises': [
                    {
                        'type': 'multiple_choice',
                        'question': '¿Cómo se dice "Hola" en Nasa?',
                        'correct_answer': 'We\'te',
                        'options': ['We\'te', 'Payuth', 'Yuwe', 'Kiwe']
                    }
                ]
            },
            {
                'title': 'Números y Conteo',
                'description': 'Aprende los números en Nasa',
                'difficulty': 1
            },
            {
                'title': 'Familia y Relaciones',
                'description': 'Vocabulario sobre la familia en Nasa Yuwe',
                'difficulty': 2,
                'exercises': [
                    {
                        'type': 'multiple_choice',
                        'question': '¿Cómo se dice "madre" en Nasa Yuwe?',
                        'correct_answer': 'Nxhi',
                        'options': ['Nxhi', 'Tata', 'Yuwe', 'Kiwe'],
                        'feedback': 'Nxhi significa "madre" en Nasa Yuwe.'
                    },
                    {
                        'type': 'multiple_choice',
                        'question': '¿Cómo se dice "padre" en Nasa Yuwe?',
                        'correct_answer': 'Tata',
                        'options': ['Nxhi', 'Tata', 'Yuwe', 'Kiwe'],
                        'feedback': 'Tata significa "padre" en Nasa Yuwe.'
                    },
                    {
                        'type': 'multiple_choice',
                        'question': '¿Cómo se dice "hermano" en Nasa Yuwe?',
                        'correct_answer': 'Nxisa',
                        'options': ['Nxisa', 'Tata', 'Nxhi', 'Kiwe'],
                        'feedback': 'Nxisa significa "hermano" en Nasa Yuwe.'
                    }
                ]
            }
        ]

        for unit_data in basic_units:
            unit = LearningUnit(
                title=unit_data['title'],
                description=unit_data['description'],
                difficulty=unit_data['difficulty']
            )
            if 'exercises' in unit_data:
                for ex_data in unit_data['exercises']:
                    exercise = Exercise(
                        type=ex_data['type'],
                        question=ex_data['question'],
                        correct_answer=ex_data['correct_answer'],
                        options=ex_data['options']
                    )
                    unit.exercises.append(exercise)
            self.units.append(unit)

    def get_current_unit(self) -> Optional[LearningUnit]:
        if 0 <= self.current_unit_index < len(self.units):
            return self.units[self.current_unit_index]
        return None

    def check_answer(self, exercise: Exercise, user_answer: str) -> bool:
        is_correct = exercise.correct_answer.lower() == user_answer.lower()
        if is_correct:
            self.total_score += 10 * self.get_current_unit().difficulty
        return is_correct

    def get_word_meanings(self, word: str) -> List[str]:
        return self.dictionary.get(word, {}).get('meanings', [])

    def get_next_exercise(self) -> Optional[Exercise]:
        current_unit = self.get_current_unit()
        if current_unit:
            incomplete_exercises = [
                ex for ex in current_unit.exercises if not ex.completed
            ]
            if incomplete_exercises:
                return random.choice(incomplete_exercises)
        return None

    def advance_unit(self) -> bool:
        current_unit = self.get_current_unit()
        if current_unit and all(ex.completed for ex in current_unit.exercises):
            current_unit.completed = True
            self.current_unit_index += 1
            return True
        return False

    def get_progress(self) -> dict:
        return {
            'total_score': self.total_score,
            'units_completed': sum(1 for unit in self.units if unit.completed),
            'total_units': len(self.units),
            'current_unit': self.current_unit_index + 1
        }