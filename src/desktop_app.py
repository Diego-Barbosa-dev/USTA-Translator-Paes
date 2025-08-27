import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,QComboBox, QTextEdit, QPushButton, QLabel, QDialog,QLineEdit, QFormLayout, QMessageBox, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QLinearGradient
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from pathlib import Path
import json
import speech_recognition as sr

class AddWordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Agregar Nueva Palabra')
        self.setModal(True)
        layout = QFormLayout(self)

        self.spanish_word = QLineEdit(self)
        self.translation = QLineEdit(self)
        self.explanation = QTextEdit(self)
        self.explanation.setMaximumHeight(100)

        layout.addRow('Palabra en Español:', self.spanish_word)
        layout.addRow('Traducción:', self.translation)
        layout.addRow('Explicación:', self.explanation)

        buttons = QHBoxLayout()
        save_button = QPushButton('Guardar', self)
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton('Cancelar', self)
        cancel_button.clicked.connect(self.reject)

        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

class TraductorIndigena(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Traductor de Lenguas Indígenas')
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.setup_styles()
        self.load_dictionaries()
        self.setup_speech_recognition()
        self.setup_animations()

    def setup_animations(self):
        # Animación para botones
        for button in self.findChildren(QPushButton):
            animation = QPropertyAnimation(button, b'pos')
            animation.setDuration(200)
            animation.setEasingCurve(QEasingCurve.Type.OutQuad)
            button.enterEvent = lambda e, b=button: self.button_hover_enter(e, b)
            button.leaveEvent = lambda e, b=button: self.button_hover_leave(e, b)

    def button_hover_enter(self, event, button):
        animation = QPropertyAnimation(button, b'pos', duration=200)
        pos = button.pos()
        animation.setStartValue(pos)
        animation.setEndValue(QPoint(pos.x(), pos.y() - 2))
        animation.start()

    def button_hover_leave(self, event, button):
        animation = QPropertyAnimation(button, b'pos', duration=200)
        pos = button.pos()
        animation.setStartValue(pos)
        animation.setEndValue(QPoint(pos.x(), pos.y() + 2))
        animation.start()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Header
        header = QFrame()
        header.setStyleSheet('background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3498DB, stop:1 #2980B9); border-radius: 12px; margin: 15px; padding: 10px;')
        header_layout = QHBoxLayout(header)

        title = QLabel('Traductor de Lenguas Indígenas')
        title.setStyleSheet('color: white; font-size: 24px; font-weight: bold;')
        header_layout.addWidget(title)

        # Language selector
        selector_frame = QFrame()
        selector_frame.setStyleSheet('background-color: #F0F0F0; border-radius: 10px; padding: 10px;')
        selector_layout = QHBoxLayout(selector_frame)

        self.language_label = QLabel('Seleccione la lengua indígena:')
        self.language_combo = QComboBox()
        self.language_combo.addItems(['Sikuani', 'Piapoco', 'Achagua', 'Guayabero'])
        self.language_combo.setStyleSheet('padding: 5px;')

        selector_layout.addWidget(self.language_label)
        selector_layout.addWidget(self.language_combo)

        # Input area
        input_frame = QFrame()
        input_frame.setStyleSheet('background-color: white; border-radius: 10px; padding: 10px;')
        input_layout = QVBoxLayout(input_frame)

        self.input_label = QLabel('Texto en español:')
        self.input_text = QTextEdit()

        voice_button = QPushButton('🎤 Reconocimiento de Voz')
        voice_button.clicked.connect(self.start_voice_recognition)
        voice_button.setStyleSheet(
            'background-color: #3498DB; color: white; padding: 12px; border-radius: 8px; font-weight: bold;'
        )

        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(voice_button)

        # Translation buttons
        buttons_layout = QHBoxLayout()
        self.translate_button = QPushButton('Traducir')
        self.translate_button.clicked.connect(self.translate_text)
        self.translate_button.setStyleSheet(
            'background-color: #3498DB; color: white; padding: 12px; border-radius: 8px; font-weight: bold;'
        )

        add_word_button = QPushButton('Agregar Nueva Palabra')
        add_word_button.clicked.connect(self.show_add_word_dialog)
        add_word_button.setStyleSheet(
            'background-color: #2980B9; color: white; padding: 12px; border-radius: 8px; font-weight: bold;'
        )

        buttons_layout.addWidget(self.translate_button)
        buttons_layout.addWidget(add_word_button)

        # Output area
        output_frame = QFrame()
        output_frame.setStyleSheet('background-color: white; border-radius: 10px; padding: 10px;')
        output_layout = QVBoxLayout(output_frame)

        self.output_label = QLabel('Traducción:')
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)

        self.explanation_label = QLabel('Explicación:')
        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)

        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_text)
        output_layout.addWidget(self.explanation_label)
        output_layout.addWidget(self.explanation_text)

        # Add all components to main layout
        layout.addWidget(header)
        layout.addWidget(selector_frame)
        layout.addWidget(input_frame)
        layout.addLayout(buttons_layout)
        layout.addWidget(output_frame)

    def setup_styles(self):
        # Aplicar efecto de sombra a los frames
        for widget in self.findChildren(QFrame):
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(15)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 2)
            widget.setGraphicsEffect(shadow)

        # Establecer estilos modernos
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ECF0F1, stop:1 #BDC3C7);
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #34495E;
                margin: 8px;
                letter-spacing: 0.5px;
            }
            QTextEdit {
                border: 2px solid #3498DB;
                border-radius: 10px;
                padding: 12px;
                background-color: rgba(255, 255, 255, 0.95);
                selection-background-color: #3498DB;
                color: #2C3E50;
                font-size: 14px;
                line-height: 1.6;
                box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            QPushButton {
                border: none;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3498DB, stop:1 #2980B9);
                transition: all 0.3s;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2980B9, stop:1 #2471A3);
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
            QComboBox {
                border: 2px solid #3498DB;
                border-radius: 10px;
                padding: 8px 15px;
                background: white;
                font-size: 13px;
                color: #2C3E50;
            }
            QComboBox::drop-down {
                border: none;
                width: 35px;
                border-left: 2px solid #3498DB;
                background: #3498DB;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin-top: 3px;
            }
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 12px;
            }
        """)

    def setup_speech_recognition(self):
        self.recognizer = sr.Recognizer()

    def start_voice_recognition(self):
        try:
            with sr.Microphone() as source:
                self.statusBar().showMessage('Escuchando... Habla ahora')
                audio = self.recognizer.listen(source)
                try:
                    text = self.recognizer.recognize_google(audio, language='es-ES')
                    self.input_text.setText(text)
                    self.statusBar().showMessage('Texto reconocido correctamente', 3000)
                except sr.UnknownValueError:
                    self.statusBar().showMessage('No se pudo entender el audio', 3000)
                except sr.RequestError:
                    self.statusBar().showMessage('Error en el servicio de reconocimiento', 3000)
        except Exception as e:
            QMessageBox.warning(self, 'Error', 'Error al iniciar el micrófono: ' + str(e))

    def show_add_word_dialog(self):
        dialog = AddWordDialog(self)
        if dialog.exec():
            word = dialog.spanish_word.text().lower()
            translation = dialog.translation.text()
            explanation = dialog.explanation.toPlainText()
            
            selected_language = self.language_combo.currentText()
            if selected_language not in self.dictionaries:
                self.dictionaries[selected_language] = {}
            
            self.dictionaries[selected_language][word] = {
                'traduccion': translation,
                'explicacion': explanation
            }
            
            # Guardar en archivo
            data_dir = Path('data')
            data_dir.mkdir(exist_ok=True)
            dict_path = data_dir / f'{selected_language.lower()}_dictionary.json'
            
            with open(dict_path, 'w', encoding='utf-8') as f:
                json.dump(self.dictionaries[selected_language], f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, 'Éxito', 'Palabra agregada correctamente')

    def load_dictionaries(self):
        self.dictionaries = {}
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        languages = {'Sikuani': 'sikuani', 'Piapoco': 'piapoco',
                    'Achagua': 'achagua', 'Guayabero': 'guayabero'}
        
        for lang_name, lang_code in languages.items():
            dict_path = data_dir / f'{lang_code}_dictionary.json'
            if dict_path.exists():
                with open(dict_path, 'r', encoding='utf-8') as f:
                    self.dictionaries[lang_name] = json.load(f)
            else:
                self.dictionaries[lang_name] = {}

    def translate_text(self):
        input_text = self.input_text.toPlainText().lower()
        selected_language = self.language_combo.currentText()
        
        if not input_text:
            self.output_text.setText('Por favor ingrese texto para traducir')
            return
        
        dictionary = self.dictionaries.get(selected_language, {})
        words = input_text.split()
        translated_words = []
        explanations = []
        unknown_words = []
        
        for word in words:
            if word in dictionary:
                word_data = dictionary[word]
                translated_words.append(word_data['traduccion'])
                explanations.append(f'{word} ({word_data["traduccion"]}): {word_data["explicacion"]}')
            else:
                translated_words.append(f'[{word}]')
                unknown_words.append(word)
        
        translation = ' '.join(translated_words)
        explanation = '\n\n'.join(explanations)
        
        self.output_text.setText(translation)
        self.explanation_text.setText(explanation)
        
        if unknown_words:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle('Palabras Desconocidas')
            msg.setText('Se encontraron palabras no registradas en el diccionario:\n' + 
                      '\n'.join(unknown_words) + 
                      '\n\n¿Desea agregar estas palabras al diccionario?')
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if msg.exec() == QMessageBox.StandardButton.Yes:
                self.show_add_word_dialog()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = TraductorIndigena()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()