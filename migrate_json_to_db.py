"""
Script de migración: JSON → MySQL.

Lee los archivos JSON existentes (diccionario y media_index) e inserta
los datos en las tablas MySQL. Se ejecuta una sola vez.
"""

import json
import os
import sys

# Asegurar imports del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db


def migrate_dictionary():
    """Migrar nasa_yuwe_dictionary.json → tabla dictionary."""
    path = os.path.join('data', 'nasa_yuwe_dictionary.json')
    if not os.path.exists(path):
        print(f"⚠️  No se encontró {path}, omitiendo diccionario.")
        return 0

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    db = get_db()
    count = 0
    for spanish_word, entry in data.items():
        traduccion = entry.get('traduccion', '').strip()
        explanation = entry.get('explanation', '').strip()
        estado = entry.get('estado', 'No Verificado').strip()

        if not traduccion:
            print(f"  ⏭️  Omitiendo '{spanish_word}' (sin traducción)")
            continue

        db.upsert_word(spanish_word, traduccion, explanation, estado)
        count += 1

    print(f"✅ Diccionario migrado: {count} entradas insertadas/actualizadas")
    return count


def migrate_media_index():
    """Migrar media_index.json → tabla media_items."""
    path = os.path.join('data', 'media_index.json')
    if not os.path.exists(path):
        print(f"⚠️  No se encontró {path}, omitiendo medios.")
        return 0

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    db = get_db()
    items = data.get('items', [])
    count = 0
    for item in items:
        media_type = item.get('type', '')
        filename = item.get('filename', '')
        url = item.get('url', '')
        tag = item.get('tag', '')

        if not media_type or not filename:
            continue

        db.add_media(media_type, filename, url, tag)
        count += 1

    print(f"✅ Medios migrados: {count} items insertados")
    return count


def verify_migration():
    """Verificar que los datos se migraron correctamente."""
    db = get_db()
    dict_count = db.count_entries()
    dictionary = db.get_all_dictionary()

    print(f"\n─── Verificación ───")
    print(f"  Entradas en diccionario: {dict_count}")

    # Verificar una palabra conocida
    word = db.get_word('hola')
    if word:
        print(f"  Prueba 'hola': {word['traduccion']} ✅")
    else:
        # Intentar con mayúscula
        word = db.get_word('Casa')
        if word:
            print(f"  Prueba 'Casa': {word['traduccion']} ✅")
        else:
            print(f"  ⚠️  No se encontró palabra de prueba")

    media = db.get_media('image')
    print(f"  Items de imagen: {len(media)}")
    media = db.get_media('audio')
    print(f"  Items de audio: {len(media)}")


if __name__ == '__main__':
    print("═══ Migración JSON → MySQL (XAMPP) ═══\n")

    dict_count = migrate_dictionary()
    media_count = migrate_media_index()

    print(f"\n📊 Total migrado: {dict_count} palabras + {media_count} medios")

    verify_migration()

    print("\n═══ Migración completada ═══")
