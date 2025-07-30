#!/usr/bin/env python3
"""
Script para generar embeddings de datos MIA UC para Django existente
Coloca este archivo en la raíz de tu proyecto Django y ejecuta
"""

import os
import json
import pandas as pd
import openai
from pathlib import Path

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")
except ImportError:
    print("⚠️ python-dotenv no instalado, usando variables del sistema")

# Configurar OpenAI (usando tu estilo original)
openai.organization = os.getenv('OPENAI_ORG')
openai.api_key = os.getenv('OPENAI_API_KEY')

EMBEDDING_MODEL = "text-embedding-ada-002"


def load_mia_data():
    """Carga datos JSON de MIA"""
    data_dir = Path("plataforma/mia_data")

    # Buscar archivo de cursos
    json_files = list(data_dir.glob("cursos_completo_*.json"))
    if not json_files:
        raise FileNotFoundError("No se encontró archivo cursos_completo_*.json en plataforma/mia_data/")

    latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"📄 Cargando: {latest_json.name}")

    with open(latest_json, 'r', encoding='utf-8') as f:
        courses_data = json.load(f)

    return courses_data


def process_course_to_text(course_code, course_info):
    """Convierte un curso a texto para embedding (mismo formato que tu sistema)"""
    parts = []

    metadata = course_info.get('metadata', {})

    # Información básica
    if metadata.get('nombre'):
        parts.append(f"Curso: {metadata['nombre']}")
    if metadata.get('codigo'):
        parts.append(f"Código: {metadata['codigo']}")
    if metadata.get('disciplina'):
        parts.append(f"Disciplina: {metadata['disciplina']}")
    if metadata.get('creditos'):
        parts.append(f"Créditos: {metadata['creditos']}")

    # Descripción
    if course_info.get('descripcion'):
        parts.append(f"Descripción: {course_info['descripcion']}")

    # Resultados de aprendizaje
    if course_info.get('resultados_aprendizaje'):
        resultados = ' '.join(course_info['resultados_aprendizaje'])
        parts.append(f"Resultados de aprendizaje: {resultados}")

    # Contenidos - CORREGIDO para manejar la nueva estructura
    if course_info.get('contenidos'):
        contenidos_text = []
        contenidos = course_info['contenidos']

        # Si contenidos es un diccionario con estructura jerárquica
        if isinstance(contenidos, dict):
            for key, value in contenidos.items():
                if isinstance(value, dict) and 'titulo' in value:
                    # Nueva estructura jerárquica
                    contenidos_text.append(value['titulo'])
                    # Agregar subsecciones si existen
                    if 'subsecciones' in value and isinstance(value['subsecciones'], dict):
                        for sub_key, sub_value in value['subsecciones'].items():
                            if isinstance(sub_value, dict) and 'titulo' in sub_value:
                                contenidos_text.append(sub_value['titulo'])
                elif isinstance(value, str):
                    # Estructura simple
                    contenidos_text.append(value)

        if contenidos_text:
            parts.append(f"Contenidos: {' '.join(contenidos_text)}")

    # Metodologías
    if course_info.get('metodologias') and isinstance(course_info['metodologias'], list):
        metodologias = ' '.join(course_info['metodologias'])
        parts.append(f"Metodologías: {metodologias}")

    # Evaluación - CORREGIDO para manejar la nueva estructura
    if course_info.get('evaluacion'):
        evaluacion = course_info['evaluacion']
        if isinstance(evaluacion, dict) and 'items' in evaluacion:
            # Nueva estructura
            eval_items = []
            for item, porcentaje in evaluacion['items'].items():
                eval_items.append(f"{item} {porcentaje}%")
            if eval_items:
                parts.append(f"Evaluación: {' '.join(eval_items)}")
        elif isinstance(evaluacion, dict):
            # Estructura simple (diccionario directo)
            eval_items = []
            for item, porcentaje in evaluacion.items():
                eval_items.append(f"{item} {porcentaje}")
            if eval_items:
                parts.append(f"Evaluación: {' '.join(eval_items)}")

    # Bibliografía
    bibliography = course_info.get('bibliography') or course_info.get('bibliografia', {})
    bib_texts = []

    for entry in bibliography.get('minima', []):
        if isinstance(entry, dict) and entry.get('raw_text'):
            bib_texts.append(entry['raw_text'])
    for entry in bibliography.get('complementaria', []):
        if isinstance(entry, dict) and entry.get('raw_text'):
            bib_texts.append(entry['raw_text'])

    if bib_texts:
        parts.append(f"Bibliografía: {' '.join(bib_texts[:5])}")  # Primeras 5 entradas

    return ' '.join(parts)


def create_embeddings_csv():
    """Crea CSV de embeddings compatible con tu sistema existente"""
    print("🔄 Cargando datos MIA...")
    courses_data = load_mia_data()

    # Procesar cursos
    texts = []
    course_codes = []

    for course_code, course_info in courses_data.items():
        text = process_course_to_text(course_code, course_info)
        if len(text.strip()) > 50:  # Solo textos con contenido
            texts.append(text)
            course_codes.append(course_code)

    print(f"📚 Procesados {len(texts)} cursos")

    # Crear embeddings
    print("🧠 Creando embeddings...")
    embeddings = []

    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"   Procesando batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")

        try:
            response = openai.Embedding.create(
                model=EMBEDDING_MODEL,
                input=batch
            )

            batch_embeddings = [item['embedding'] for item in response['data']]
            embeddings.extend(batch_embeddings)

        except Exception as e:
            print(f"❌ Error en batch: {e}")
            # Embeddings vacíos para este batch
            embeddings.extend([[0.0] * 1536] * len(batch))

    # Crear DataFrame compatible con tu formato original
    df = pd.DataFrame({
        'text': texts,
        'embedding': embeddings,
        'course_code': course_codes
    })

    # Guardar en formato compatible
    output_path = Path("plataforma/mia_data/mia_embeddings.csv")
    df.to_csv(output_path, index=False)

    print(f"✅ Embeddings guardados en: {output_path}")
    print(f"📊 Total: {len(df)} cursos")

    return output_path


if __name__ == "__main__":
    print("=== Generador de Embeddings MIA UC ===")

    # Debug de variables de entorno
    print(f"🔍 OPENAI_API_KEY configurada: {'✅ Sí' if os.getenv('OPENAI_API_KEY') else '❌ No'}")
    print(f"🔍 OPENAI_ORG configurada: {'✅ Sí' if os.getenv('OPENAI_ORG') else '❌ No'}")

    # Verificar que existe el directorio
    data_dir = Path("plataforma/mia_data")
    if not data_dir.exists():
        print("❌ Directorio plataforma/mia_data no existe")
        print("💡 Créalo y copia los archivos JSON ahí")
        exit(1)

    # Verificar OpenAI
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY no configurada")
        print("💡 Opciones:")
        print("   1. Instala python-dotenv: pip install python-dotenv")
        print("   2. O configura la variable manualmente:")
        print("      set OPENAI_API_KEY=tu_api_key  # Windows")
        print("      export OPENAI_API_KEY=tu_api_key  # Linux/Mac")
        exit(1)

    try:
        create_embeddings_csv()
        print("\n🎉 ¡Listo! Ahora puedes usar el chat MIA UC")

    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)