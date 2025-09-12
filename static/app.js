// Variables globales para reconocimiento de voz
let recognition = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingStartTime = null;
let recordingTimer = null;



// Inicializar reconocimiento de voz
function initializeSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        
        recognition.onstart = function() {
            console.log('Reconocimiento de voz iniciado');
            updateRecordingStatus('Escuchando...', true);
        };
        
        recognition.onresult = function(event) {
            let finalTranscript = '';
            let interimTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Mostrar resultado en el campo de texto
            const inputText = document.getElementById('inputText');
            if (finalTranscript) {
                inputText.value = finalTranscript;
                console.log('Texto reconocido:', finalTranscript);
                
                // Traducir automáticamente después de un breve retraso
                setTimeout(() => {
                    translateTextAutomatically();
                }, 1000);
            }
        };
        
        recognition.onerror = function(event) {
            console.error('Error en reconocimiento de voz:', event.error);
            let errorMessage = 'Error en el reconocimiento de voz';
            
            switch(event.error) {
                case 'no-speech':
                    errorMessage = 'No se detectó voz. Intente hablar más cerca del micrófono.';
                    break;
                case 'audio-capture':
                    errorMessage = 'No se pudo acceder al micrófono. Verifique los permisos.';
                    break;
                case 'not-allowed':
                    errorMessage = 'Acceso al micrófono denegado. Permita el acceso para usar esta función.';
                    break;
                case 'network':
                    errorMessage = 'Error de red. Verifique su conexión a internet.';
                    break;
            }
            
            showError(errorMessage);
            stopRecording();
        };
        
        recognition.onend = function() {
            console.log('Reconocimiento de voz terminado');
            if (isRecording) {
                stopRecording();
            }
        };
        
        return true;
    } else {
        console.warn('Reconocimiento de voz no soportado en este navegador');
        showError('Su navegador no soporta reconocimiento de voz. Use Chrome o Edge para esta función.');
        return false;
    }
}

// Configurar idioma de reconocimiento
function setRecognitionLanguage() {
    if (!recognition) return;
    
    const sourceLanguage = document.getElementById('sourceLanguage').value;
    let langCode = 'es-ES'; // Español por defecto
    
    switch(sourceLanguage) {
        case 'spanish':
            langCode = 'es-ES';
            break;
        case 'sikuani':
        case 'piapoco':
        case 'achagua':
        case 'guayabero':
        case 'nasa_yuwe':
            // Para idiomas indígenas, usar español como base
            // ya que no hay soporte directo en Web Speech API
            langCode = 'es-CO'; // Español de Colombia
            break;
        default:
            langCode = 'es-ES';
    }
    
    recognition.lang = langCode;
    console.log('Idioma de reconocimiento configurado:', langCode);
}

// Funciones de grabación
function startRecording() {
    if (!recognition && !initializeSpeechRecognition()) {
        return;
    }
    
    clearError();
    setRecognitionLanguage();
    
    try {
        recognition.start();
        isRecording = true;
        recordingStartTime = Date.now();
        
        // Actualizar UI
        document.getElementById('startRecording').disabled = true;
        document.getElementById('stopRecording').disabled = false;
        document.getElementById('inputText').value = '';
        
        // Iniciar timer
        startRecordingTimer();
        
        updateRecordingStatus('Iniciando...', true);
        
    } catch (error) {
        console.error('Error al iniciar grabación:', error);
        showError('Error al iniciar la grabación. Intente nuevamente.');
        stopRecording();
    }
}

function stopRecording() {
    if (recognition && isRecording) {
        recognition.stop();
    }
    
    isRecording = false;
    
    // Actualizar UI
    document.getElementById('startRecording').disabled = false;
    document.getElementById('stopRecording').disabled = true;
    
    // Detener timer
    stopRecordingTimer();
    
    updateRecordingStatus('Listo para grabar', false);
}

// Funciones de timer
function startRecordingTimer() {
    recordingTimer = setInterval(() => {
        if (recordingStartTime) {
            const elapsed = Date.now() - recordingStartTime;
            const seconds = Math.floor(elapsed / 1000);
            const minutes = Math.floor(seconds / 60);
            const displaySeconds = seconds % 60;
            
            const timeString = `${minutes.toString().padStart(2, '0')}:${displaySeconds.toString().padStart(2, '0')}`;
            document.getElementById('recordingTime').textContent = timeString;
        }
    }, 1000);
}

function stopRecordingTimer() {
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
    document.getElementById('recordingTime').textContent = '00:00';
    recordingStartTime = null;
}

// Actualizar estado de grabación
function updateRecordingStatus(status, isActive) {
    const statusElement = document.getElementById('recordingStatus');
    const indicatorElement = document.getElementById('recordingIndicator');
    
    statusElement.textContent = status;
    
    if (isActive) {
        indicatorElement.classList.add('recording');
    } else {
        indicatorElement.classList.remove('recording');
    }
}

// Funciones de cambio de método de entrada
function showTextInput() {
    document.getElementById('textInputSection').classList.remove('hidden');
    document.getElementById('voiceInputSection').classList.add('hidden');
    document.getElementById('addWordSection').classList.add('hidden');
    
    document.getElementById('showTextInput').classList.add('active');
    document.getElementById('showVoiceInput').classList.remove('active');
    document.getElementById('showAddWordInput').classList.remove('active');
    
    // Detener grabación si está activa
    if (isRecording) {
        stopRecording();
    }
}

function showVoiceInput() {
    document.getElementById('textInputSection').classList.add('hidden');
    document.getElementById('voiceInputSection').classList.remove('hidden');
    document.getElementById('addWordSection').classList.add('hidden');
    
    document.getElementById('showTextInput').classList.remove('active');
    document.getElementById('showVoiceInput').classList.add('active');
    document.getElementById('showAddWordInput').classList.remove('active');
    
    // Inicializar reconocimiento si no está disponible
    if (!recognition) {
        initializeSpeechRecognition();
    }
}

function showAddWordInput() {
    document.getElementById('textInputSection').classList.add('hidden');
    document.getElementById('voiceInputSection').classList.add('hidden');
    document.getElementById('addWordSection').classList.remove('hidden');
    
    document.getElementById('showTextInput').classList.remove('active');
    document.getElementById('showVoiceInput').classList.remove('active');
    document.getElementById('showAddWordInput').classList.add('active');
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar reconocimiento de voz
    initializeSpeechRecognition();
    
    // Event listeners para botones de método de entrada
    document.getElementById('showTextInput').addEventListener('click', showTextInput);
    document.getElementById('showVoiceInput').addEventListener('click', showVoiceInput);
    document.getElementById('showAddWordInput').addEventListener('click', showAddWordInput);
    
    // Event listeners para grabación
    document.getElementById('startRecording').addEventListener('click', startRecording);
    document.getElementById('stopRecording').addEventListener('click', stopRecording);
    
    // Event listener para agregar palabras
    document.getElementById('addWordBtn').addEventListener('click', addNewWord);
    
    // Event listener para cambio de idioma
    document.getElementById('sourceLanguage').addEventListener('change', function() {
        if (recognition) {
            setRecognitionLanguage();
        }
    });
    
    // Inicializar toggle de tema
    initializeThemeToggle();
});

// Funcionalidad del toggle de tema
function initializeThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    const toggleIcon = themeToggle.querySelector('.toggle-icon');
    
    // Cargar tema guardado o usar modo oscuro por defecto
    const savedTheme = localStorage.getItem('theme') || 'dark';
    applyTheme(savedTheme);
    
    // Event listener para el botón toggle
    themeToggle.addEventListener('click', function() {
        const currentTheme = document.documentElement.classList.contains('light-mode') ? 'light' : 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Animación del botón
        themeToggle.style.transform = 'rotate(360deg)';
        setTimeout(() => {
            themeToggle.style.transform = '';
        }, 300);
    });
}

function applyTheme(theme) {
    const toggleIcon = document.querySelector('.toggle-icon');
    
    if (theme === 'light') {
        document.documentElement.classList.add('light-mode');
        toggleIcon.textContent = '☀️';
    } else {
        document.documentElement.classList.remove('light-mode');
        toggleIcon.textContent = '🌙';
    }
}

// Funciones principales de traducción
document.getElementById('translateText').addEventListener('click', async () => {
    try {
        const text = document.getElementById('inputText').value.trim();
        const sourceLanguage = document.getElementById('sourceLanguage').value;
        const targetLanguage = document.getElementById('targetLanguage').value;

        if (!text) {
            showError('Por favor ingrese texto para traducir');
            return;
        }

        if (sourceLanguage === targetLanguage) {
            showError('El idioma de origen y destino no pueden ser iguales');
            return;
        }

        showProgress();
        clearError();

        const response = await fetch('/api/translate-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                source_lang: sourceLanguage,
                target_lang: targetLanguage
            })
        });

        const data = await response.json();
        hideProgress();

        if (data.error) {
            showError(data.error);
            return;
        }

        document.getElementById('originalText').textContent = text;
        document.getElementById('translatedText').textContent = data.translation;
        document.getElementById('originalStatus').textContent = `(${sourceLanguage})`;
        document.getElementById('translationStatus').textContent = `(${targetLanguage})`;
    } catch (error) {
        hideProgress();
        showError('Error al traducir el texto');
        console.error('Error:', error);
    }
});

// Función para traducir automáticamente
async function translateTextAutomatically() {
    try {
        const text = document.getElementById('inputText').value.trim();
        const sourceLanguage = document.getElementById('sourceLanguage').value;
        const targetLanguage = document.getElementById('targetLanguage').value;

        if (!text) {
            return;
        }

        if (sourceLanguage === targetLanguage) {
            showError('El idioma de origen y destino no pueden ser iguales');
            return;
        }

        showProgress();
        clearError();

        const response = await fetch('/api/translate-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                source_lang: sourceLanguage,
                target_lang: targetLanguage
            })
        });

        const data = await response.json();
        hideProgress();

        if (data.error) {
            showError(data.error);
            return;
        }

        document.getElementById('originalText').textContent = text;
        document.getElementById('translatedText').textContent = data.translation;
        document.getElementById('originalStatus').textContent = `(${sourceLanguage})`;
        document.getElementById('translationStatus').textContent = `(${targetLanguage})`;
        
        console.log('Traducción automática completada:', data.translation);
    } catch (error) {
        hideProgress();
        showError('Error al traducir el texto automáticamente');
        console.error('Error en traducción automática:', error);
    }
}

// Funciones de utilidad
function showError(message) {
    const errorElement = document.getElementById('errorMessage');
    errorElement.textContent = message;
    errorElement.classList.remove('hidden');
}

function clearError() {
    const errorElement = document.getElementById('errorMessage');
    errorElement.textContent = '';
    errorElement.classList.add('hidden');
}

function showProgress() {
    document.getElementById('translationProgress').classList.remove('hidden');
}

function hideProgress() {
    document.getElementById('translationProgress').classList.add('hidden');
}

// Función para agregar nueva palabra
async function addNewWord() {
    const spanishWord = document.getElementById('spanishWord').value.trim();
    const nasaYuweTranslation = document.getElementById('nasaYuweTranslation').value.trim();
    const wordContext = document.getElementById('wordContext').value.trim();
    const statusElement = document.getElementById('addWordStatus');
    
    // Validar campos
    if (!spanishWord || !nasaYuweTranslation || !wordContext) {
        showAddWordStatus('Por favor, complete todos los campos.', 'error');
        return;
    }
    
    try {
        const response = await fetch('/add_word', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                spanish_word: spanishWord,
                nasa_yuwe_translation: nasaYuweTranslation,
                context: wordContext
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Limpiar formulario
            document.getElementById('spanishWord').value = '';
            document.getElementById('nasaYuweTranslation').value = '';
            document.getElementById('wordContext').value = '';
            
            showAddWordStatus('¡Palabra agregada exitosamente al diccionario!', 'success');
        } else {
            showAddWordStatus(result.error || 'Error al agregar la palabra', 'error');
        }
    } catch (error) {
        console.error('Error al agregar palabra:', error);
        showAddWordStatus('Error de conexión al agregar la palabra', 'error');
    }
}

// Función para mostrar estado de agregar palabra
function showAddWordStatus(message, type) {
    const statusElement = document.getElementById('addWordStatus');
    statusElement.textContent = message;
    statusElement.className = `add-word-status ${type}`;
    statusElement.classList.remove('hidden');
    
    // Ocultar mensaje después de 5 segundos
    setTimeout(() => {
        statusElement.classList.add('hidden');
    }, 5000);
}

// Función para enviar retroalimentación
async function submitFeedback() {
    try {
        const correctedTranslation = document.getElementById('correctedTranslation').value.trim();
        const originalText = document.getElementById('inputText').value.trim();
        const sourceLanguage = document.getElementById('sourceLanguage').value;
        const targetLanguage = document.getElementById('targetLanguage').value;

        if (!correctedTranslation) {
            showError('Por favor ingrese una traducción corregida');
            return;
        }

        if (!originalText) {
            showError('No hay texto original para corregir');
            return;
        }

        showProgress();

        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                original_text: originalText,
                corrected_translation: correctedTranslation,
                source_lang: sourceLanguage,
                target_lang: targetLanguage
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Limpiar el campo de retroalimentación
            document.getElementById('correctedTranslation').value = '';
            
            // Mostrar mensaje de éxito
            const successMessage = document.createElement('div');
            successMessage.className = 'success-message';
            successMessage.textContent = 'Retroalimentación enviada exitosamente. ¡Gracias por contribuir!';
            successMessage.style.cssText = `
                background: rgba(0, 255, 0, 0.1);
                border: 1px solid rgba(0, 255, 0, 0.3);
                color: #00ff00;
                padding: 1rem;
                border-radius: 8px;
                margin: 1rem 0;
                text-align: center;
            `;
            
            const feedbackSection = document.querySelector('.feedback-section');
            feedbackSection.appendChild(successMessage);
            
            // Remover mensaje después de 5 segundos
            setTimeout(() => {
                if (successMessage.parentNode) {
                    successMessage.parentNode.removeChild(successMessage);
                }
            }, 5000);
            
            clearError();
        } else {
            showError(data.error || 'Error al enviar la retroalimentación');
        }
    } catch (error) {
        console.error('Error al enviar retroalimentación:', error);
        showError('Error de conexión al enviar la retroalimentación');
    } finally {
        hideProgress();
    }
}

// Event listener para el formulario de retroalimentación
document.addEventListener('DOMContentLoaded', function() {
    const feedbackForm = document.querySelector('.feedback-section form');
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitFeedback();
        });
    }
});