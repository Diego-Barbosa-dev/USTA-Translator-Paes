from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import os

def download_model():
    model_name = "facebook/nllb-200-distilled-600M"
    model_dir = "models/nllb-200-distilled-600M"

    try:
        # Crear el directorio si no existe
        os.makedirs(model_dir, exist_ok=True)

        # Descargar y guardar el modelo y el tokenizador
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

        # Guardar el modelo y el tokenizador localmente
        tokenizer.save_pretrained(model_dir)
        model.save_pretrained(model_dir)

        print(f"Modelo descargado y guardado en {model_dir}")
        return True

    except Exception as e:
        print(f"Error al descargar el modelo: {str(e)}")
        return False

if __name__ == "__main__":
    download_model()