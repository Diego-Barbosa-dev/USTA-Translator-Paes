from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import os
from pathlib import Path

def download_model():
    # Crear directorio para modelos si no existe
    models_dir = Path('models')
    models_dir.mkdir(exist_ok=True)
    
    # Configurar el directorio de caché de Hugging Face
    os.environ['TRANSFORMERS_CACHE'] = str(models_dir.absolute())
    
    # Nombre del modelo a descargar
    model_name = "facebook/nllb-200-distilled-600M"
    
    print(f"Descargando modelo {model_name}...")
    
    try:
        # Descargar y guardar el modelo
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Guardar el modelo y tokenizer localmente
        model_path = models_dir / 'nllb-200-distilled-600M'
        model.save_pretrained(str(model_path))
        tokenizer.save_pretrained(str(model_path))
        
        print(f"Modelo guardado exitosamente en {model_path}")
        return True
    except Exception as e:
        print(f"Error al descargar el modelo: {str(e)}")
        return False

if __name__ == '__main__':
    download_model()