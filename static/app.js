let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let recordingTimer;
let recordingStartTime;

function updateRecordingTime() {
    const currentTime = Date.now();
    const elapsedTime = Math.floor((currentTime - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsedTime / 60).toString().padStart(2, '0');
    const seconds = (elapsedTime % 60).toString().padStart(2, '0');
    document.getElementById('recordingTime').textContent = `${minutes}:${seconds}`;
}

document.getElementById('startRecording').addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            try {
                const audioBlob = new Blob(audioChunks);
                const formData = new FormData();
                formData.append('audio', audioBlob);

                const targetLanguage = document.getElementById('targetLanguage').value;
                formData.append('target_lang', targetLanguage);
                const response = await fetch('/api/process-audio', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error('Error en la traducción');
                }

                const result = await response.json();
                if (result.status === 'error') {
                    throw new Error(result.message);
                }
                document.getElementById('originalText').textContent = result.original_text || '';
                document.getElementById('translatedText').textContent = result.translation || '';
                document.getElementById('recordingStatus').textContent = 'Listo para grabar';
                document.getElementById('originalStatus').textContent = result.original_text ? 'Texto reconocido' : 'Error en el reconocimiento';
                document.getElementById('translationStatus').textContent = result.status === 'success' ? 'Traducción completada' : 'Traducción parcial';
                
                if (result.status === 'partial') {
                    document.getElementById('errorMessage').textContent = result.message;
                    document.getElementById('errorMessage').classList.remove('hidden');
                } else {
                    document.getElementById('errorMessage').classList.add('hidden');
                }
            } catch (error) {
                alert('Error al procesar el audio: ' + error.message);
                document.getElementById('originalText').textContent = '';
                document.getElementById('translatedText').textContent = 'Error en la traducción. Por favor, intente de nuevo.';
            } finally {
                isRecording = false;
                stream.getTracks().forEach(track => track.stop());
            }
        };

        mediaRecorder.start();
        isRecording = true;
        recordingStartTime = Date.now();
        recordingTimer = setInterval(updateRecordingTime, 1000);
        document.getElementById('startRecording').disabled = true;
        document.getElementById('stopRecording').disabled = false;
        document.getElementById('recordingStatus').textContent = 'Grabando...';
        document.getElementById('recordingIndicator').classList.add('recording');
        document.getElementById('originalStatus').textContent = 'Grabando audio...';
        document.getElementById('translationStatus').textContent = '';
    } catch (error) {
        alert('Hay un error para acceder al micrófono. Por favor, asegúrese de que tiene un micrófono conectado y ha dado los respectivos permisos.');
        isRecording = false;
    }
});

document.getElementById('stopRecording').addEventListener('click', () => {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        clearInterval(recordingTimer);
        document.getElementById('recordingTime').textContent = '00:00';
        document.getElementById('startRecording').disabled = false;
        document.getElementById('stopRecording').disabled = true;
        document.getElementById('recordingStatus').textContent = 'Procesando...';
        document.getElementById('originalStatus').textContent = 'Procesando audio...';
        document.getElementById('recordingIndicator').classList.remove('recording');
        audioChunks = [];
    }
});

document.getElementById('submitFeedback').addEventListener('click', async () => {
    try {
        const correctedTranslation = document.getElementById('correctedTranslation').value;
        if (!correctedTranslation.trim()) {
            alert('Por favor, ingrese una traducción corregida');
            return;
        }
        const originalText = document.getElementById('originalText').textContent;
        const targetLanguage = document.getElementById('targetLanguage').value;

        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                original_text: originalText,
                corrected_translation: correctedTranslation,
                target_lang: targetLanguage
            })
        });

        if (!response.ok) {
            throw new Error('Error al enviar el feedback');
        }

        document.getElementById('correctedTranslation').value = '';
        alert('¡Gracias por tu feedback!');
    } catch (error) {
        alert('Error al enviar el feedback: ' + error.message);
    }
});

// Funciones de cambio de método de entrada
document.getElementById('showTextInput').addEventListener('click', () => {
    document.getElementById('textInputSection').classList.remove('hidden');
    document.getElementById('voiceInputSection').classList.add('hidden');
    document.getElementById('showTextInput').classList.add('active');
    document.getElementById('showVoiceInput').classList.remove('active');
});

document.getElementById('showVoiceInput').addEventListener('click', () => {
    document.getElementById('textInputSection').classList.add('hidden');
    document.getElementById('voiceInputSection').classList.remove('hidden');
    document.getElementById('showTextInput').classList.remove('active');
    document.getElementById('showVoiceInput').classList.add('active');
});

// Función para traducir texto escrito
document.getElementById('translateText').addEventListener('click', async () => {
    try {
        const text = document.getElementById('inputText').value.trim();
        if (!text) {
            alert('Por favor, ingrese un texto para traducir');
            return;
        }

        const targetLanguage = document.getElementById('targetLanguage').value;
        const response = await fetch('/api/translate-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                target_lang: targetLanguage
            })
        });

        if (!response.ok) {
            throw new Error('Error en la traducción');
        }

        const result = await response.json();
        if (result.status === 'error') {
            throw new Error(result.message);
        }

        document.getElementById('originalText').textContent = text;
        document.getElementById('translatedText').textContent = result.translation || '';
        document.getElementById('originalStatus').textContent = 'Texto ingresado';
        document.getElementById('translationStatus').textContent = result.status === 'success' ? 'Traducción completada' : 'Traducción parcial';

        if (result.status === 'partial') {
            document.getElementById('errorMessage').textContent = result.message;
            document.getElementById('errorMessage').classList.remove('hidden');
        } else {
            document.getElementById('errorMessage').classList.add('hidden');
        }
    } catch (error) {
        alert('Error al traducir el texto: ' + error.message);
        document.getElementById('translatedText').textContent = 'Error en la traducción. Por favor, intente de nuevo.';
    }
});